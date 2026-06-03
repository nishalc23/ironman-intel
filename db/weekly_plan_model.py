from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, JSON, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from db.models import Base


class WeeklyAdaptivePlan(Base):
    """
    Stores the Claude-generated adaptive plan for a specific week.
    Generated every Sunday night based on actual training data.
    Falls back to static plan if not yet generated.
    """
    __tablename__ = "weekly_adaptive_plans"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    week_start = Column(Date, nullable=False)       # always a Monday
    week_number = Column(Integer, nullable=False)   # 1–26
    phase = Column(String, nullable=False)          # foundation | build | peak | taper | race_week
    generated_at = Column(DateTime, default=datetime.utcnow)

    # The full structured plan as JSON — matches frontend DayPlan[] shape
    plan_json = Column(JSON, nullable=False, default=list)

    # Adaptation metadata — what Claude saw and decided
    adaptation_notes = Column(String, nullable=True)   # Claude's reasoning summary
    volume_adjustment = Column(String, nullable=True)  # "normal" | "reduced_10" | "reduced_25" | "increased_5"
    missed_sessions = Column(JSON, nullable=True)      # list of missed sports from prior week
    prior_ctl = Column(String, nullable=True)
    prior_atl = Column(String, nullable=True)
    prior_tsb = Column(String, nullable=True)

    __table_args__ = (
        UniqueConstraint("athlete_id", "week_start", name="uq_weekly_plan_athlete_week"),
        Index("idx_weekly_plan_athlete_week", "athlete_id", "week_start"),
    )
