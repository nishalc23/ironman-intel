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
from services.ingestion.garmin_client import GarminClient

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


def ingest_activities(athlete: Athlete, db, garmin: GarminClient) -> int:
    raw_activities = garmin.get_activities(limit=100)
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
        logger.info(f"Sync complete — {new_count} new activities ingested")


if __name__ == "__main__":
    main()
