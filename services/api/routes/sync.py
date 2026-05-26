import os
import sys
import logging
from datetime import date, timedelta
from fastapi import APIRouter, BackgroundTasks, HTTPException

sys.path.insert(0, "/app")

from db.database import get_db
from db.models import Athlete, Activity
from services.ingestion.garmin_client import GarminClient
from services.ingestion.main import get_or_create_athlete, ingest_activities
from compute.tss import estimate_activity_tss
from compute.load import recompute_load

router = APIRouter()
logger = logging.getLogger(__name__)


def _run_sync():
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]

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

        # Rebuild CTL/ATL/TSB for the last 90 days
        from_date = date.today() - timedelta(days=90)
        recompute_load(db, athlete_obj, from_date, date.today())

        logger.info(f"Sync complete — {new_count} new activities, CTL/ATL/TSB rebuilt")

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
