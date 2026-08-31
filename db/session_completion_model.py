from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Date, DateTime, ForeignKey, UniqueConstraint, Index,
)

from db.models import Base


class SessionCompletion(Base):
    """
    A checked-off session from the fixed weekly template.

    Completions used to live in the browser's localStorage, so they vanished on
    another device and could not be read back by the planner. Keyed by athlete,
    week, and session key, with a unique constraint so double-tapping the same
    checkbox cannot create two rows.
    """

    __tablename__ = "session_completions"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    week_start = Column(Date, nullable=False)      # always a Monday
    session_key = Column(String, nullable=False)   # from compute.weekly_template
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("athlete_id", "week_start", "session_key",
                         name="uq_session_completion"),
        Index("idx_session_completion_athlete_week", "athlete_id", "week_start"),
    )
