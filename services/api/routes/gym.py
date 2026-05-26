from datetime import date
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from db.models import Athlete, GymWorkout

router = APIRouter()


class SetIn(BaseModel):
    reps: int
    weight_kg: float | None = None


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


@router.post("/", response_model=GymWorkoutOut)
def log_gym_workout(payload: GymWorkoutIn):
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run the sync first")

        workout = GymWorkout(
            athlete_id=athlete.id,
            date=payload.date,
            duration_minutes=payload.duration_minutes,
            notes=payload.notes,
            exercises=[e.model_dump() for e in payload.exercises],
        )
        db.add(workout)
        db.flush()
        return workout


@router.get("/", response_model=list[GymWorkoutOut])
def list_gym_workouts(limit: int = 30):
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run the sync first")

        return (
            db.query(GymWorkout)
            .filter_by(athlete_id=athlete.id)
            .order_by(GymWorkout.date.desc())
            .limit(limit)
            .all()
        )
