from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from db.models import Athlete, Activity

router = APIRouter()


class ActivityOut(BaseModel):
    id: int
    garmin_activity_id: str
    discipline: str
    start_time: datetime
    duration_seconds: float
    distance_meters: float | None
    avg_heart_rate: int | None
    avg_power: int | None
    calories: int | None
    tss: float | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[ActivityOut])
def list_activities(limit: int = 50, offset: int = 0):
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run the sync first")

        rows = (
            db.query(Activity)
            .filter_by(athlete_id=athlete.id)
            .order_by(Activity.start_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return rows
