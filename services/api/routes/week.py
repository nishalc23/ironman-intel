"""
The weekly requirement checklist and its completions.

Scoped to the authenticated athlete, stored server side so a checkmark
survives a different browser or device.
"""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from compute.weekly_template import (
    ALL_KEYS,
    DISCIPLINE_ORDER,
    TRAINING_KEYS,
    by_discipline,
    targets,
    week_end,
    week_start,
)
from db.database import get_db
from db.session_completion_model import SessionCompletion
from services.api.auth import current_athlete_id, load_athlete

router = APIRouter()


class RequirementOut(BaseModel):
    key: str
    discipline: str
    intensity: str
    label: str
    completed: bool
    completed_at: datetime | None


class GroupOut(BaseModel):
    discipline: str
    done: int
    target: int
    requirements: list[RequirementOut]


class ProgressOut(BaseModel):
    completed: int
    total: int
    # Training only. Rest is a box you tick, not work you did, so counting it
    # would make a week where you only rested look partly trained.
    training_completed: int
    training_total: int
    by_discipline: dict[str, int]
    targets: dict[str, int]


class WeekOut(BaseModel):
    week_start: date
    week_end: date
    groups: list[GroupOut]
    progress: ProgressOut


def _completions(db, athlete_id: int, start: date) -> dict[str, datetime]:
    rows = (
        db.query(SessionCompletion)
        .filter(
            SessionCompletion.athlete_id == athlete_id,
            SessionCompletion.week_start == start,
        )
        .all()
    )
    return {r.session_key: r.completed_at for r in rows}


def _build(db, athlete_id: int, start: date) -> WeekOut:
    done = _completions(db, athlete_id, start)
    grouped = by_discipline()
    target_counts = targets()

    groups, completed, training_completed = [], 0, 0
    per_discipline: dict[str, int] = {}

    for discipline in DISCIPLINE_ORDER:
        group_done = 0
        items = []
        for r in grouped.get(discipline, []):
            is_done = r.key in done
            if is_done:
                completed += 1
                group_done += 1
                if r.key in TRAINING_KEYS:
                    training_completed += 1
            items.append(RequirementOut(
                key=r.key, discipline=r.discipline, intensity=r.intensity,
                label=r.label, completed=is_done, completed_at=done.get(r.key),
            ))
        per_discipline[discipline] = group_done
        groups.append(GroupOut(
            discipline=discipline, done=group_done,
            target=target_counts.get(discipline, 0), requirements=items,
        ))

    return WeekOut(
        week_start=start,
        week_end=week_end(start),
        groups=groups,
        progress=ProgressOut(
            completed=completed,
            total=len(ALL_KEYS),
            training_completed=training_completed,
            training_total=len(TRAINING_KEYS),
            by_discipline=per_discipline,
            targets=target_counts,
        ),
    )


@router.get("/", response_model=WeekOut)
def get_week(week_of: date | None = None, athlete_id: int = Depends(current_athlete_id)):
    start = week_start(week_of or date.today())
    with get_db() as db:
        load_athlete(db, athlete_id)
        return _build(db, athlete_id, start)


@router.post("/complete/{session_key}", response_model=WeekOut)
def complete(session_key: str, week_of: date | None = None,
             athlete_id: int = Depends(current_athlete_id)):
    """
    Tick a requirement off. Idempotent, because a double tap on a phone should
    not produce a duplicate row or an error.
    """
    if session_key not in ALL_KEYS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown session '{session_key}'")

    start = week_start(week_of or date.today())
    with get_db() as db:
        load_athlete(db, athlete_id)
        exists = (
            db.query(SessionCompletion)
            .filter(
                SessionCompletion.athlete_id == athlete_id,
                SessionCompletion.week_start == start,
                SessionCompletion.session_key == session_key,
            )
            .first()
        )
        if exists is None:
            db.add(SessionCompletion(
                athlete_id=athlete_id, week_start=start, session_key=session_key,
            ))
            db.flush()
        return _build(db, athlete_id, start)


@router.delete("/complete/{session_key}", response_model=WeekOut)
def uncomplete(session_key: str, week_of: date | None = None,
               athlete_id: int = Depends(current_athlete_id)):
    """Untick a requirement. Also idempotent."""
    if session_key not in ALL_KEYS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown session '{session_key}'")

    start = week_start(week_of or date.today())
    with get_db() as db:
        load_athlete(db, athlete_id)
        db.query(SessionCompletion).filter(
            SessionCompletion.athlete_id == athlete_id,
            SessionCompletion.week_start == start,
            SessionCompletion.session_key == session_key,
        ).delete()
        db.flush()
        return _build(db, athlete_id, start)
