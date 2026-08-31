from datetime import datetime
from sqlalchemy import Column, Integer, Float, Date, DateTime, String, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from db.models import Base


class SleepLog(Base):
    """
    Nightly sleep data pulled from Garmin Connect.
    Synced every morning as part of the main sync job.
    """
    __tablename__ = "sleep_logs"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date = Column(Date, nullable=False)                    # the night's date (morning after)

    # Garmin sleep score (0–100)
    sleep_score = Column(Integer, nullable=True)           # overall score
    sleep_score_qualifier = Column(String, nullable=True)  # "EXCELLENT" | "GOOD" | "FAIR" | "POOR"

    # Duration
    duration_seconds = Column(Integer, nullable=True)      # total sleep time
    deep_sleep_seconds = Column(Integer, nullable=True)
    light_sleep_seconds = Column(Integer, nullable=True)
    rem_sleep_seconds = Column(Integer, nullable=True)
    awake_seconds = Column(Integer, nullable=True)

    # Recovery signals
    hrv_nightly_avg = Column(Float, nullable=True)         # ms — key training readiness signal
    hrv_5min_high = Column(Float, nullable=True)           # best HRV block of the night
    resting_hr = Column(Integer, nullable=True)            # bpm
    body_battery_charged = Column(Integer, nullable=True)  # 0–100 Garmin body battery

    # Computed readiness (0–100, derived from score + HRV trend)
    readiness_score = Column(Integer, nullable=True)
    readiness_signal = Column(String, nullable=True)       # "green" | "yellow" | "red"
    readiness_headline = Column(String, nullable=True)     # what to actually do today
    readiness_limiter = Column(String, nullable=True)      # weakest signal, or NULL if none

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uq_sleep_athlete_date"),
        Index("idx_sleep_athlete_date", "athlete_id", "date"),
    )
