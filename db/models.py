from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Boolean, JSON,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Athlete(Base):
    __tablename__ = "athletes"

    id = Column(Integer, primary_key=True)
    garmin_user_id = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=True)
    ftp_watts = Column(Integer, nullable=True)       # cycling threshold power
    threshold_pace_per_km = Column(Float, nullable=True)  # running threshold pace
    threshold_css_per_100m = Column(Float, nullable=True) # swim critical swim speed
    gym_split = Column(String, nullable=True)        # "upper_lower" | "ppl" | "arnold"

    # Auth. password_hash is bcrypt; there is no plaintext anywhere.
    password_hash = Column(String, nullable=True)

    # Garmin credentials, encrypted at rest with Fernet keyed by GARMIN_ENC_KEY.
    # Each athlete connects their own account, so these are per-row, never env vars.
    garmin_token_encrypted = Column(String, nullable=True)
    garmin_connected_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    activities = relationship("Activity", back_populates="athlete", cascade="all, delete-orphan")
    daily_metrics = relationship("DailyMetrics", back_populates="athlete", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="athlete", cascade="all, delete-orphan")
    gym_workouts = relationship("GymWorkout", back_populates="athlete", cascade="all, delete-orphan")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    garmin_activity_id = Column(String, unique=True, nullable=False)
    discipline = Column(String, nullable=False)  # "swimming" | "cycling" | "running" | "other"
    start_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)
    distance_meters = Column(Float, nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    max_heart_rate = Column(Integer, nullable=True)
    avg_power = Column(Integer, nullable=True)       # watts, cycling only
    avg_pace_per_km = Column(Float, nullable=True)   # running
    avg_speed_kph = Column(Float, nullable=True)
    calories = Column(Integer, nullable=True)
    tss = Column(Float, nullable=True)               # computed after ingestion
    normalized_power = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    athlete = relationship("Athlete", back_populates="activities")
    streams = relationship("ActivityStream", back_populates="activity", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_activities_athlete_time", "athlete_id", "start_time"),
    )


class ActivityStream(Base):
    """Second-by-second sensor data — ~3,600 rows per hour of training."""

    __tablename__ = "activity_streams"

    id = Column(Integer, primary_key=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    heart_rate = Column(Integer, nullable=True)
    power = Column(Integer, nullable=True)           # watts
    speed_mps = Column(Float, nullable=True)         # meters per second
    cadence = Column(Integer, nullable=True)         # rpm or spm
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude_meters = Column(Float, nullable=True)

    activity = relationship("Activity", back_populates="streams")

    __table_args__ = (
        Index("idx_streams_activity_time", "activity_id", "timestamp"),
    )


class DailyMetrics(Base):
    """
    Pre-computed training load numbers per day.
    These are expensive to calculate so we store them rather than recomputing on every request.
    """

    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    date = Column(Date, nullable=False)
    ctl = Column(Float, nullable=True)   # Chronic Training Load — 42-day fitness
    atl = Column(Float, nullable=True)   # Acute Training Load  — 7-day fatigue
    tsb = Column(Float, nullable=True)   # Form = CTL - ATL (positive = fresh, negative = fatigued)
    daily_tss = Column(Float, default=0) # TSS earned that day
    swim_volume_meters = Column(Float, default=0)
    bike_volume_meters = Column(Float, default=0)
    run_volume_meters = Column(Float, default=0)

    athlete = relationship("Athlete", back_populates="daily_metrics")

    __table_args__ = (
        UniqueConstraint("athlete_id", "date", name="uq_daily_metrics_athlete_date"),
        Index("idx_daily_metrics_athlete_date", "athlete_id", "date"),
    )


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    swim_time_seconds = Column(Integer, nullable=True)
    bike_time_seconds = Column(Integer, nullable=True)
    run_time_seconds = Column(Integer, nullable=True)
    total_time_seconds = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0.0–1.0
    model_version = Column(String, nullable=True)

    athlete = relationship("Athlete", back_populates="predictions")


class GymWorkout(Base):
    """
    A single gym session. exercises is a JSON array so you can log any number
    of movements without needing a separate table per exercise.

    Example exercises value:
    [{"name": "Squat", "sets": [{"reps": 5, "weight_kg": 100}, ...]}, ...]
    """

    __tablename__ = "gym_workouts"

    id = Column(Integer, primary_key=True)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=False)
    hevy_workout_id = Column(String, unique=True, nullable=True)  # set when imported from Hevy
    date = Column(Date, nullable=False)
    notes = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    exercises = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    athlete = relationship("Athlete", back_populates="gym_workouts")

    __table_args__ = (
        Index("idx_gym_workouts_athlete_date", "athlete_id", "date"),
    )
