from datetime import date
from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from services.api.auth import current_athlete_id, load_athlete
from db.models import Athlete, GymWorkout

router = APIRouter()


class SetIn(BaseModel):
    reps: int
    weight_lbs: float | None = None


class ExerciseIn(BaseModel):
    name: str
    sets: list[SetIn]


class GymWorkoutIn(BaseModel):
    date: date
    duration_minutes: int | None = None
    notes: str | None = None
    exercises: list[ExerciseIn]


class GymWorkoutOut(BaseModel):
    id: int
    date: date
    duration_minutes: int | None
    notes: str | None
    exercises: list

    model_config = {"from_attributes": True}


def _serialize(w: GymWorkout) -> GymWorkoutOut:
    return GymWorkoutOut(
        id=w.id,
        date=w.date,
        duration_minutes=w.duration_minutes,
        notes=w.notes,
        exercises=w.exercises or [],
    )


@router.post("/", response_model=GymWorkoutOut)
def log_gym_workout(payload: GymWorkoutIn, athlete_id: int = Depends(current_athlete_id)):
    with get_db() as db:
        athlete = load_athlete(db, athlete_id)

        workout = GymWorkout(
            athlete_id=athlete.id,
            date=payload.date,
            duration_minutes=payload.duration_minutes,
            notes=payload.notes,
            exercises=[e.model_dump() for e in payload.exercises],
        )
        db.add(workout)
        db.flush()
        return _serialize(workout)


@router.get("/exercises", response_model=list[str])
def list_exercises(athlete_id: int = Depends(current_athlete_id)):
    """Return all unique exercise names from history, sorted alphabetically."""
    CARDIO = {"treadmill", "swimming", "stair machine", "bike", "elliptical", "rower"}
    with get_db() as db:
        athlete = load_athlete(db, athlete_id)
        workouts = db.query(GymWorkout).filter_by(athlete_id=athlete.id).all()
        names: set[str] = set()
        for w in workouts:
            for ex in (w.exercises or []):
                name = ex.get("name", "").strip()
                if name and not any(c in name.lower() for c in CARDIO):
                    names.add(name)
        return sorted(names)


@router.get("/", response_model=list[GymWorkoutOut])
def list_gym_workouts(limit: int = 30, athlete_id: int = Depends(current_athlete_id)):
    with get_db() as db:
        athlete = load_athlete(db, athlete_id)

        rows = (
            db.query(GymWorkout)
            .filter_by(athlete_id=athlete.id)
            .order_by(GymWorkout.date.desc())
            .limit(limit)
            .all()
        )
        # Serialize inside the session before it closes
        return [_serialize(w) for w in rows]
