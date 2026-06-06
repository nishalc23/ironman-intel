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
from compute.load import recompute_load

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


def _ingest_raw_activities(athlete: Athlete, db, raw_activities: list) -> int:
    """Ingest a pre-fetched list of raw Garmin activity dicts."""
    new_count = 0
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
        logger.info(f"Ingested {discipline} activity {garmin_id} on {start_time.date()}")

    return new_count


def ingest_activities(athlete: Athlete, db, garmin: GarminClient) -> int:
    """Fetch and ingest activities from Garmin."""
    raw_activities = garmin.get_activities(limit=50)
    return _ingest_raw_activities(athlete, db, raw_activities)


def _compute_readiness(score: int | None, hrv: float | None, resting_hr: int | None) -> tuple[int, str]:
    """Compute a 0-100 readiness score and green/yellow/red signal."""
    points = 0
    count = 0

    if score is not None:
        points += score
        count += 1

    if hrv is not None:
        # HRV 60+ = excellent, 40-60 = good, 20-40 = fair, <20 = poor
        hrv_score = min(100, int(hrv * 1.5))
        points += hrv_score
        count += 1

    if resting_hr is not None:
        # Lower resting HR = better recovered (45=100pts, 70=0pts)
        hr_score = max(0, min(100, int((70 - resting_hr) * 4)))
        points += hr_score
        count += 1

    readiness = int(points / count) if count else 50

    if readiness >= 70:
        signal = "green"
    elif readiness >= 45:
        signal = "yellow"
    else:
        signal = "red"

    return readiness, signal


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

        readiness, signal = _compute_readiness(sleep_score, hrv_val, resting_hr)

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
            existing_record.readiness_score = readiness
            existing_record.readiness_signal = signal
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
                readiness_score=readiness,
                readiness_signal=signal,
            )
            db.add(log)
            new_count += 1

        logger.info(f"Sleep {day}: score={sleep_score}, HRV={hrv_val}, readiness={signal}")

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
        new_count = ingest_activities(athlete, db, garmin)

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
        from_date = date.today() - timedelta(days=90)
        recompute_load(db, athlete, from_date, date.today())

        # Pull last 14 days of sleep data
        sleep_count = ingest_sleep(athlete, db, garmin, days=14)
        logger.info(f"Sync complete — {new_count} new activities, {sleep_count} sleep logs, CTL/ATL/TSB rebuilt")


if __name__ == "__main__":
    main()
