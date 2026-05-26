from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from db.models import Athlete, GymWorkout
from services.api.claude_planner import generate_plan, _next_split_day

router = APIRouter()

# Which cardio disciplines are allowed per split day
ALLOWED_BY_SPLIT = {
    "upper": ["bike", "run"],   # upper body worked → no swim
    "lower": ["swim", "bike"],  # legs worked → no run
}


class PlanOut(BaseModel):
    plan: str


class SplitOut(BaseModel):
    split_day: str          # "upper" | "lower" | "unknown"
    allowed: list[str]      # e.g. ["bike", "run"]


@router.get("/split", response_model=SplitOut)
def get_split():
    """Return today's gym split day and which tri disciplines are allowed."""
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            return SplitOut(split_day="unknown", allowed=["swim", "bike", "run"])

        from datetime import date, timedelta
        recent_gym = (
            db.query(GymWorkout)
            .filter(
                GymWorkout.athlete_id == athlete.id,
                GymWorkout.date >= date.today() - timedelta(days=14),
            )
            .order_by(GymWorkout.date.desc())
            .all()
        )
        split = athlete.gym_split or "upper_lower"
        split_day = _next_split_day(recent_gym, split)
        allowed = ALLOWED_BY_SPLIT.get(split_day, ["swim", "bike", "run"])
        return SplitOut(split_day=split_day, allowed=allowed)


@router.get("/today", response_model=PlanOut)
def get_today_plan(gym: bool = True, discipline: str | None = None, split: str | None = None):
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run the sync first")

        plan_text = generate_plan(db, athlete, gym=gym, discipline=discipline, split_override=split)
        return PlanOut(plan=plan_text)
