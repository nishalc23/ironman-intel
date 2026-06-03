from datetime import date, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from db.database import get_db
from db.models import Athlete, GymWorkout
from db.weekly_plan_model import WeeklyAdaptivePlan
from services.api.claude_planner import generate_plan, generate_weekly_plan, _next_split_day
from services.api.adaptive_planner import generate_adaptive_weekly_plan, get_week_number, get_week_start

router = APIRouter()

# Which cardio disciplines are allowed per split day
ALLOWED_BY_SPLIT = {
    "upper": ["bike", "run"],   # upper body worked → no swim
    "lower": ["swim", "bike"],  # legs worked → no run
}


class PlanOut(BaseModel):
    plan: str


class AdaptivePlanOut(BaseModel):
    week_number: int
    week_start: str
    phase: str
    adaptation_notes: str | None
    volume_adjustment: str | None
    missed_sessions: list[str] | None
    prior_ctl: str | None
    prior_atl: str | None
    prior_tsb: str | None
    days: list[Any]
    generated_at: str


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


@router.get("/weekly", response_model=PlanOut)
def get_weekly_plan():
    """Return a 7-day structured training schedule targeting sub-5:00 70.3."""
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run the sync first")

        plan_text = generate_weekly_plan(db, athlete)
        return PlanOut(plan=plan_text)


@router.get("/adaptive/{week_number}", response_model=AdaptivePlanOut)
def get_adaptive_plan(week_number: int):
    """
    Return the stored adaptive plan for a given week number.
    Returns 404 if not yet generated (frontend falls back to static plan).
    """
    with get_db() as db:
        week_start = get_week_start(week_number)
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found")

        plan = (
            db.query(WeeklyAdaptivePlan)
            .filter_by(athlete_id=athlete.id, week_start=week_start)
            .first()
        )
        if not plan:
            raise HTTPException(404, f"No adaptive plan for week {week_number} yet")

        return AdaptivePlanOut(
            week_number=plan.week_number,
            week_start=str(plan.week_start),
            phase=plan.phase,
            adaptation_notes=plan.adaptation_notes,
            volume_adjustment=plan.volume_adjustment,
            missed_sessions=plan.missed_sessions or [],
            prior_ctl=plan.prior_ctl,
            prior_atl=plan.prior_atl,
            prior_tsb=plan.prior_tsb,
            days=plan.plan_json,
            generated_at=str(plan.generated_at),
        )


@router.post("/adaptive/generate")
async def trigger_adaptive_generation(week_number: int | None = None, background_tasks: __import__("fastapi").BackgroundTasks = None):
    """
    Fire-and-forget: kicks off Claude generation in the background and returns immediately.
    Frontend polls GET /adaptive/{week} until the plan appears.
    """
    from fastapi import BackgroundTasks as BT
    import asyncio

    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run sync first")
        athlete_id = athlete.id

    target_wk = week_number

    def _run():
        from services.api.adaptive_planner import generate_adaptive_weekly_plan
        from db.models import Athlete as A
        with get_db() as db2:
            ath = db2.query(A).filter_by(id=athlete_id).first()
            if ath:
                generate_adaptive_weekly_plan(db2, ath, target_week_num=target_wk)

    import threading
    t = threading.Thread(target=_run, daemon=True)
    t.start()

    wk = week_number or 1
    return {"status": "generating", "week_number": wk, "message": "Plan generation started — poll GET /adaptive/{week} until ready"}
