"""Shared fixtures. Tests run against in-memory SQLite so they need no Docker."""
import os
import sys
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import Base, Athlete, Activity, GymWorkout  # noqa: E402


@pytest.fixture
def db():
    """
    Mirrors the production session config, autoflush included.

    Testing with autoflush on hid a real bug: the app disables it, so rows
    added but not flushed were invisible to later queries in the same session,
    and fifty ingested activities went unscored. A fixture that does not match
    production cannot catch that.
    """
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    yield session
    session.close()


@pytest.fixture
def athlete(db):
    a = Athlete(email="test@example.com", display_name="Test", ftp_watts=250)
    db.add(a)
    db.commit()
    return a


@pytest.fixture
def add_activity(db, athlete):
    """Insert an activity with a known TSS on a given date."""
    counter = {"n": 0}

    def _add(on_date: date, tss: float, discipline: str = "cycling", distance: float = 10000):
        counter["n"] += 1
        act = Activity(
            athlete_id=athlete.id,
            garmin_activity_id=f"test-{counter['n']}",
            discipline=discipline,
            start_time=datetime.combine(on_date, datetime.min.time()) + timedelta(hours=9),
            duration_seconds=3600,
            distance_meters=distance,
            tss=tss,
        )
        db.add(act)
        db.commit()
        return act

    return _add
