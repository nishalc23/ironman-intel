"""
Ingestion service — pulls activity data from Garmin Connect into PostgreSQL.

Run manually:  python -m services.ingestion.main
Run via Docker: docker compose run ingestion
"""
import os
import sys
import logging
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, "/app")

from db.database import create_tables, get_db
from db.models import Athlete, Activity
from db.sleep_model import SleepLog
from services.ingestion.garmin_client import GarminClient
from compute.tss import estimate_activity_tss
from compute.load import recompute_from, earliest_uncounted_activity
from compute.readiness import compute_readiness, rolling_baseline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def get_or_create_athlete(db, email: str) -> Athlete:
    athlete = db.query(Athlete).filter_by(email=email).first()
    if not athlete:
        athlete = Athlete(email=email)
        db.add(athlete)
        db.flush()  # assigns the id without committing
        logger.info(f"Created new athlete record for {email}")
    return athlete


def parse_start_time(raw: dict) -> datetime | None:
    for key in ("startTimeLocal", "startTimeGMT"):
        val = raw.get(key)
        if val:
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except ValueError:
                pass
    return None


def _ingest_raw_activities(athlete: Athlete, db, raw_activities: list):
    """
    Ingest a pre-fetched list of raw Garmin activity dicts.

    Returns (new_count, earliest_event_date). The second value is what makes
    late arrivals correct: it is the oldest workout date this sync touched,
    which is where recomputation has to restart from.
    """
    new_count = 0
    earliest = None
    for raw in raw_activities:
        garmin_id = str(raw.get("activityId", ""))
        if not garmin_id:
            continue

        if db.query(Activity).filter_by(garmin_activity_id=garmin_id).first():
            continue  # already ingested

        type_key = raw.get("activityType", {}).get("typeKey", "")
        discipline = GarminClient.map_discipline(type_key)

        start_time = parse_start_time(raw)
        if not start_time:
            logger.warning(f"Skipping activity {garmin_id} — no start time")
            continue

        activity = Activity(
            athlete_id=athlete.id,
            garmin_activity_id=garmin_id,
            discipline=discipline,
            start_time=start_time,
            duration_seconds=raw.get("duration", 0),
            distance_meters=raw.get("distance"),
            avg_heart_rate=raw.get("averageHR"),
            max_heart_rate=raw.get("maxHR"),
            avg_power=raw.get("avgPower"),
            avg_speed_kph=raw.get("averageSpeed"),
            calories=raw.get("calories"),
        )
        db.add(activity)
        new_count += 1
        event_date = start_time.date()
        if earliest is None or event_date < earliest:
            earliest = event_date
        logger.info(f"Ingested {discipline} activity {garmin_id} on {event_date}")

    return new_count, earliest


def ingest_activities(athlete: Athlete, db, garmin: GarminClient):
    """Fetch and ingest activities from Garmin. Returns (new_count, earliest_date)."""
    raw_activities = garmin.get_activities(limit=50)
    return _ingest_raw_activities(athlete, db, raw_activities)


def recompute_readiness(db, athlete_id: int, window: int = 14) -> int:
    """
    Rescore readiness for recent nights against a rolling baseline.

    HRV and resting HR only mean something relative to an athlete's own normal,
    so each night is compared with the nights before it. Runs after ingestion
    because a night cannot be scored until its neighbours exist.
    """
    rows = (
        db.query(SleepLog)
        .filter(SleepLog.athlete_id == athlete_id)
        .order_by(SleepLog.date)
        .all()
    )

    for i, row in enumerate(rows):
        prior = rows[max(0, i - window):i + 1]
        hrv_base = rolling_baseline([r.hrv_nightly_avg for r in prior])
        rhr_base = rolling_baseline([float(r.resting_hr) if r.resting_hr else None for r in prior])

        result = compute_readiness(
            sleep_score=row.sleep_score,
            duration_hours=(row.duration_seconds / 3600) if row.duration_seconds else None,
            hrv=row.hrv_nightly_avg,
            resting_hr=row.resting_hr,
            hrv_baseline=hrv_base,
            rhr_baseline=rhr_base,
        )
        row.readiness_score = result.score
        row.readiness_signal = result.signal
        row.readiness_headline = result.headline
        row.readiness_limiter = result.limiter

    return len(rows)


def ingest_sleep(athlete: Athlete, db, garmin: GarminClient, days: int = 7) -> int:
    """Pull last N days of sleep data from Garmin and store in sleep_logs."""
    from datetime import date, timedelta
    from concurrent.futures import ThreadPoolExecutor, as_completed
    new_count = 0

    today = date.today()
    dates_to_fetch = []
    for i in range(days):
        day = today - timedelta(days=i)
        existing = db.query(SleepLog).filter_by(athlete_id=athlete.id, date=day).first()
        if existing and i > 1:  # always re-fetch yesterday and today
            continue
        dates_to_fetch.append((i, day))

    # Fetch all days in parallel (3 threads — Garmin rate limit safe)
    def fetch_day(args):
        i, day = args
        return i, day, garmin.get_sleep_data(day.isoformat())

    results = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i, day, raw in pool.map(fetch_day, dates_to_fetch):
            results[day] = (i, raw)

    for day, (i, raw) in results.items():
        if not raw:
            continue

        # Parse Garmin sleep response — field names confirmed from real API
        daily = raw.get("dailySleepDTO", {})
        score_obj = daily.get("sleepScores", {})
        sleep_score = score_obj.get("overall", {}).get("value") if isinstance(score_obj, dict) else None
        qualifier = score_obj.get("overall", {}).get("qualifierKey") if isinstance(score_obj, dict) else None

        duration = daily.get("sleepTimeSeconds")
        deep = daily.get("deepSleepSeconds")
        light = daily.get("lightSleepSeconds")
        rem = daily.get("remSleepSeconds")
        awake = daily.get("awakeSleepSeconds")

        # Resting HR is avgHeartRate in the sleep DTO
        resting_hr = int(daily.get("avgHeartRate") or 0) or None

        # HRV — Garmin puts this in a separate key at the top level
        hrv_val = (
            raw.get("avgOvernightHrv")
            or daily.get("avgOvernightHrv")
            or raw.get("hrvValue")
            or daily.get("hrvValue")
        )

        existing_record = db.query(SleepLog).filter_by(athlete_id=athlete.id, date=day).first()
        if existing_record:
            existing_record.sleep_score = sleep_score
            existing_record.sleep_score_qualifier = qualifier
            existing_record.duration_seconds = duration
            existing_record.deep_sleep_seconds = deep
            existing_record.light_sleep_seconds = light
            existing_record.rem_sleep_seconds = rem
            existing_record.awake_seconds = awake
            existing_record.hrv_nightly_avg = hrv_val
            existing_record.resting_hr = resting_hr
            # readiness is recomputed below, once every night is in place
        else:
            log = SleepLog(
                athlete_id=athlete.id,
                date=day,
                sleep_score=sleep_score,
                sleep_score_qualifier=qualifier,
                duration_seconds=duration,
                deep_sleep_seconds=deep,
                light_sleep_seconds=light,
                rem_sleep_seconds=rem,
                awake_seconds=awake,
                hrv_nightly_avg=hrv_val,
                resting_hr=resting_hr,
            )
            db.add(log)
            new_count += 1

        logger.info(f"Sleep {day}: score={sleep_score}, HRV={hrv_val}, {duration and round(duration/3600,1)}h")

    # Readiness compares each night against the athlete's own baseline, so it
    # can only be scored once the surrounding nights are in the database.
    db.flush()
    recompute_readiness(db, athlete.id)

    return new_count


def main():
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]

    logger.info("Initializing database schema...")
    create_tables()

    logger.info("Connecting to Garmin...")
    garmin = GarminClient(email, password)

    with get_db() as db:
        athlete = get_or_create_athlete(db, email)
        new_count, earliest_new = ingest_activities(athlete, db, garmin)

        # Stamp TSS on any activity missing it
        untssed = (
            db.query(Activity)
            .filter(Activity.athlete_id == athlete.id, Activity.tss.is_(None))
            .all()
        )
        for act in untssed:
            act.tss = estimate_activity_tss(
                discipline=act.discipline,
                duration_seconds=act.duration_seconds,
                avg_hr=act.avg_heart_rate,
                avg_power=act.avg_power,
                ftp_watts=athlete.ftp_watts,
                threshold_hr=None,
            )
        if untssed:
            logger.info(f"Computed TSS for {len(untssed)} activities")

        # Rebuild CTL/ATL/TSB from scratch (last 90 days)
        from datetime import date, timedelta
        # Cascade from the oldest workout this sync touched, not a fixed window.
        # A backdated upload invalidates its own day and every day after it,
        # and a fixed 90 day window silently misses anything older.
        candidates = [d for d in (earliest_new, earliest_uncounted_activity(db, athlete.id)) if d]
        cascade_from = min(candidates) if candidates else date.today() - timedelta(days=90)
        days = recompute_from(db, athlete, cascade_from)
        logger.info(f"Recomputed {days} days of training load from {cascade_from}")

        # Pull last 14 days of sleep data
        sleep_count = ingest_sleep(athlete, db, garmin, days=14)
        logger.info(f"Sync complete — {new_count} new activities, {sleep_count} sleep logs, CTL/ATL/TSB rebuilt")


if __name__ == "__main__":
    main()
