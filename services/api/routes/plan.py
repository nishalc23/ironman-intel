from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from db.models import Athlete
from services.api.claude_planner import generate_plan

router = APIRouter()


class PlanOut(BaseModel):
    plan: str


@router.get("/today", response_model=PlanOut)
def get_today_plan():
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run the sync first")

        plan_text = generate_plan(db, athlete)
        return PlanOut(plan=plan_text)
