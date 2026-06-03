from datetime import date, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from db.models import Athlete, DailyMetrics

router = APIRouter()


class DailyMetricsOut(BaseModel):
    date: date
    ctl: float | None
    atl: float | None
    tsb: float | None
    daily_tss: float
    swim_km: float
    bike_km: float
    run_km: float

    model_config = {"from_attributes": True}


class MetricsSummaryOut(BaseModel):
    athlete_name: str | None
    today: DailyMetricsOut | None
    history: list[DailyMetricsOut]
    overtraining_risk: str  # "low" | "moderate" | "high"


def _risk_level(tsb: float | None) -> str:
    if tsb is None:
        return "low"
    if tsb < -30:
        return "high"
    if tsb < -10:
        return "moderate"
    return "low"


@router.get("/", response_model=MetricsSummaryOut)
def get_metrics(days: int = 90):
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found — run the sync first")

        since = date.today() - timedelta(days=days)
        rows = (
            db.query(DailyMetrics)
            .filter(
                DailyMetrics.athlete_id == athlete.id,
                DailyMetrics.date >= since,
            )
            .order_by(DailyMetrics.date)
            .all()
        )

        history = [
            DailyMetricsOut(
                date=r.date,
                ctl=r.ctl,
                atl=r.atl,
                tsb=r.tsb,
                daily_tss=r.daily_tss or 0,
                swim_km=round((r.swim_volume_meters or 0) / 1000, 2),
                bike_km=round((r.bike_volume_meters or 0) / 1000, 2),
                run_km=round((r.run_volume_meters or 0) / 1000, 2),
            )
            for r in rows
        ]

        # Use today's row if it has activity; otherwise fall back to the
        # most recent day with real TSS (handles UTC-vs-Pacific timezone gap).
        today_row = next((h for h in reversed(history) if h.date == date.today() and h.daily_tss > 0), None)
        if today_row is None:
            today_row = next((h for h in reversed(history) if h.daily_tss > 0), None) or (history[-1] if history else None)

        return MetricsSummaryOut(
            athlete_name=athlete.display_name or athlete.email,
            today=today_row,
            history=history,
            overtraining_risk=_risk_level(today_row.tsb if today_row else None),
        )
