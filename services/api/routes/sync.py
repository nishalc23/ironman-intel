import os
import sys
import logging
from datetime import date, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException

sys.path.insert(0, "/app")

from db.database import get_db
from db.models import Athlete, Activity
from services.ingestion.garmin_client import GarminClient
from services.ingestion.main import get_or_create_athlete, ingest_activities, ingest_sleep, _ingest_raw_activities
from compute.tss import estimate_activity_tss
from compute.load import recompute_from, earliest_uncounted_activity

log = logging.getLogger(__name__)

router = APIRouter()
logger = logging.getLogger(__name__)


def _run_sync():
    import concurrent.futures
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]

    garmin = GarminClient(email, password)

    # Fetch activities and sleep raw data in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        activities_future = pool.submit(garmin.get_activities, 50)  # last 50 is plenty
        # Sleep fetching happens inside ingest_sleep with its own parallelism
        raw_activities = activities_future.result()

    with get_db() as db:
        athlete = get_or_create_athlete(db, email)

        # Ingest activities (uses already-fetched list)
        new_count, earliest_new = _ingest_raw_activities(athlete, db, raw_activities)

        # Stamp TSS on any activity missing it
        untssed = (
            db.query(Activity)
            .filter(Activity.athlete_id == athlete.id, Activity.tss.is_(None))
            .all()
        )
        athlete_obj = db.query(Athlete).get(athlete.id)
        for act in untssed:
            act.tss = estimate_activity_tss(
                discipline=act.discipline,
                duration_seconds=act.duration_seconds,
                avg_hr=act.avg_heart_rate,
                avg_power=act.avg_power,
                ftp_watts=athlete_obj.ftp_watts,
                threshold_hr=None,
            )

        # Cascade from the oldest workout this sync touched, not a fixed window.
        # A backdated upload invalidates its own day and every day after it,
        # and a fixed 90 day window silently misses anything older.
        candidates = [d for d in (earliest_new, earliest_uncounted_activity(db, athlete_obj.id)) if d]
        cascade_from = min(candidates) if candidates else date.today() - timedelta(days=90)
        days = recompute_from(db, athlete_obj, cascade_from)
        log.info(f"Recomputed {days} days of training load from {cascade_from}")

        # Pull 7 days of sleep + HRV data (parallelized inside)
        sleep_count = ingest_sleep(athlete_obj, db, garmin, days=7)

        logger.info(f"Sync complete — {new_count} new activities, {sleep_count} sleep logs, CTL/ATL/TSB rebuilt")

        # Bust plan cache so next generation reflects new activity data
        import redis as redis_lib
        try:
            r = redis_lib.Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
            for key in r.scan_iter(f"plan:{athlete.id}:*"):
                r.delete(key)
            logger.info("Plan cache cleared")
        except Exception:
            pass


@router.post("/")
def trigger_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_sync)
    return {"status": "sync started"}
