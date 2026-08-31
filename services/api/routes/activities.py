from datetime import datetime
from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from services.api.auth import current_athlete_id, load_athlete
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
def list_activities(limit: int = 50, offset: int = 0, athlete_id: int = Depends(current_athlete_id)):
    with get_db() as db:
        athlete = load_athlete(db, athlete_id)

        rows = (
            db.query(Activity)
            .filter_by(athlete_id=athlete.id)
            .order_by(Activity.start_time.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        # Serialize inside the session while objects are still attached
        return [ActivityOut.model_validate(r) for r in rows]
