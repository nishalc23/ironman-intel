from datetime import date, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.database import get_db
from db.models import Athlete
from db.sleep_model import SleepLog

router = APIRouter()


class SleepEntry(BaseModel):
    date: str
    sleep_score: int | None
    sleep_score_qualifier: str | None
    duration_hours: float | None
    deep_sleep_hours: float | None
    light_sleep_hours: float | None
    rem_sleep_hours: float | None
    hrv_nightly_avg: float | None
    resting_hr: int | None
    readiness_score: int | None
    readiness_signal: str | None  # "green" | "yellow" | "red"


class SleepSummary(BaseModel):
    today: SleepEntry | None
    last_7_days: list[SleepEntry]
    avg_score_7d: float | None
    avg_hrv_7d: float | None
    trend: str  # "improving" | "stable" | "declining"


def _to_entry(log: SleepLog) -> SleepEntry:
    return SleepEntry(
        date=str(log.date),
        sleep_score=log.sleep_score,
        sleep_score_qualifier=log.sleep_score_qualifier,
        duration_hours=round(log.duration_seconds / 3600, 1) if log.duration_seconds else None,
        deep_sleep_hours=round(log.deep_sleep_seconds / 3600, 1) if log.deep_sleep_seconds else None,
        light_sleep_hours=round(log.light_sleep_seconds / 3600, 1) if log.light_sleep_seconds else None,
        rem_sleep_hours=round(log.rem_sleep_seconds / 3600, 1) if log.rem_sleep_seconds else None,
        hrv_nightly_avg=log.hrv_nightly_avg,
        resting_hr=log.resting_hr,
        readiness_score=log.readiness_score,
        readiness_signal=log.readiness_signal,
    )


@router.get("/", response_model=SleepSummary)
def get_sleep_summary():
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found")

        since = date.today() - timedelta(days=7)
        logs = (
            db.query(SleepLog)
            .filter(SleepLog.athlete_id == athlete.id, SleepLog.date >= since)
            .order_by(SleepLog.date.desc())
            .all()
        )

        today_log = logs[0] if logs and logs[0].date == date.today() else (
            logs[0] if logs else None
        )

        entries = [_to_entry(l) for l in logs]

        scores = [l.sleep_score for l in logs if l.sleep_score is not None]
        hrvs = [l.hrv_nightly_avg for l in logs if l.hrv_nightly_avg is not None]

        avg_score = round(sum(scores) / len(scores), 1) if scores else None
        avg_hrv = round(sum(hrvs) / len(hrvs), 1) if hrvs else None

        # Trend: compare first half vs second half of the week
        trend = "stable"
        if len(scores) >= 4:
            first_half = scores[len(scores)//2:]
            second_half = scores[:len(scores)//2]
            diff = sum(second_half)/len(second_half) - sum(first_half)/len(first_half)
            if diff > 5:
                trend = "improving"
            elif diff < -5:
                trend = "declining"

        return SleepSummary(
            today=_to_entry(today_log) if today_log else None,
            last_7_days=entries,
            avg_score_7d=avg_score,
            avg_hrv_7d=avg_hrv,
            trend=trend,
        )


@router.get("/latest", response_model=SleepEntry)
def get_latest_sleep():
    """Returns most recent sleep log — used by adaptive planner for readiness check."""
    with get_db() as db:
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(404, "No athlete found")

        log = (
            db.query(SleepLog)
            .filter(SleepLog.athlete_id == athlete.id)
            .order_by(SleepLog.date.desc())
            .first()
        )
        if not log:
            raise HTTPException(404, "No sleep data yet — sync first")

        return _to_entry(log)
