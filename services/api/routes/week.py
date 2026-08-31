"""
The fixed weekly template and its completion checkboxes.

Everything here is scoped to the authenticated athlete, and completions are
stored server side so a checkmark survives a different browser or device.
"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from compute.weekly_template import (
    TEMPLATE,
    DAY_NAMES,
    ALL_KEYS,
    WEEKLY_TARGETS,
    week_start,
)
from db.database import get_db
from db.session_completion_model import SessionCompletion
from services.api.auth import current_athlete_id, load_athlete

router = APIRouter()


class SessionOut(BaseModel):
    key: str
    discipline: str
    intensity: str
    label: str
    completed: bool
    completed_at: datetime | None


class DayOut(BaseModel):
    day_index: int
    day_name: str
    date: date
    is_today: bool
    sessions: list[SessionOut]


class ProgressOut(BaseModel):
    completed: int
    total: int
    by_discipline: dict[str, int]
    targets: dict[str, int]


class WeekOut(BaseModel):
    week_start: date
    days: list[DayOut]
    progress: ProgressOut


def _completions(db, athlete_id: int, monday: date) -> dict[str, datetime]:
    rows = (
        db.query(SessionCompletion)
        .filter(
            SessionCompletion.athlete_id == athlete_id,
            SessionCompletion.week_start == monday,
        )
        .all()
    )
    return {r.session_key: r.completed_at for r in rows}


def _build_week(db, athlete_id: int, monday: date) -> WeekOut:
    done = _completions(db, athlete_id, monday)
    today = date.today()

    days, completed_count = [], 0
    by_discipline: dict[str, int] = {}

    for idx in range(7):
        day_date = monday + timedelta(days=idx)
        sessions = []
        for s in TEMPLATE[idx]:
            is_done = s.key in done
            if is_done:
                completed_count += 1
                by_discipline[s.discipline] = by_discipline.get(s.discipline, 0) + 1
            sessions.append(SessionOut(
                key=s.key, discipline=s.discipline, intensity=s.intensity,
                label=s.label, completed=is_done, completed_at=done.get(s.key),
            ))
        days.append(DayOut(
            day_index=idx, day_name=DAY_NAMES[idx], date=day_date,
            is_today=day_date == today, sessions=sessions,
        ))

    return WeekOut(
        week_start=monday,
        days=days,
        progress=ProgressOut(
            completed=completed_count,
            total=len(ALL_KEYS),
            by_discipline=by_discipline,
            targets=WEEKLY_TARGETS,
        ),
    )


@router.get("/", response_model=WeekOut)
def get_week(week_of: date | None = None, athlete_id: int = Depends(current_athlete_id)):
    """The template for a week, with this athlete's checkmarks applied."""
    monday = week_start(week_of or date.today())
    with get_db() as db:
        load_athlete(db, athlete_id)
        return _build_week(db, athlete_id, monday)


@router.post("/complete/{session_key}", response_model=WeekOut)
def complete_session(session_key: str, week_of: date | None = None,
                     athlete_id: int = Depends(current_athlete_id)):
    """
    Check a session off. Idempotent: checking an already checked session is a
    no-op rather than a duplicate row or an error, because a double tap on a
    phone should not fail.
    """
    if session_key not in ALL_KEYS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown session '{session_key}'")

    monday = week_start(week_of or date.today())
    with get_db() as db:
        load_athlete(db, athlete_id)
        existing = (
            db.query(SessionCompletion)
            .filter(
                SessionCompletion.athlete_id == athlete_id,
                SessionCompletion.week_start == monday,
                SessionCompletion.session_key == session_key,
            )
            .first()
        )
        if existing is None:
            db.add(SessionCompletion(
                athlete_id=athlete_id, week_start=monday, session_key=session_key,
            ))
            db.flush()
        return _build_week(db, athlete_id, monday)


@router.delete("/complete/{session_key}", response_model=WeekOut)
def uncomplete_session(session_key: str, week_of: date | None = None,
                       athlete_id: int = Depends(current_athlete_id)):
    """Uncheck a session. Also idempotent."""
    if session_key not in ALL_KEYS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown session '{session_key}'")

    monday = week_start(week_of or date.today())
    with get_db() as db:
        load_athlete(db, athlete_id)
        db.query(SessionCompletion).filter(
            SessionCompletion.athlete_id == athlete_id,
            SessionCompletion.week_start == monday,
            SessionCompletion.session_key == session_key,
        ).delete()
        db.flush()
        return _build_week(db, athlete_id, monday)
