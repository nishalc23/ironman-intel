"""
Baseline measurement for recompute_load over a realistic training history.

Query count is the metric that matters. Wall time here is measured against
in-memory SQLite, which understates production badly: on Render the database
is a network hop away, so every query costs a round trip of roughly 1-3ms
rather than microseconds.
"""
import os
import sys
import time
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import Base, Athlete, Activity, GymWorkout
from compute.load import recompute_load

WEEKS = 26
DAYS = WEEKS * 7


def build(session, athlete_id):
    """A plausible 26 week block: 5 cardio sessions and 2 gym sessions per week."""
    start = date.today() - timedelta(days=DAYS)
    n = 0
    for d in range(DAYS):
        day = start + timedelta(days=d)
        dow = day.weekday()
        if dow in (0, 2, 4, 5, 6):
            n += 1
            session.add(Activity(
                athlete_id=athlete_id,
                garmin_activity_id=f"a{n}",
                discipline=["swimming", "cycling", "running"][d % 3],
                start_time=datetime.combine(day, datetime.min.time()) + timedelta(hours=7),
                duration_seconds=3600 + (d % 5) * 900,
                distance_meters=10000 + (d % 7) * 1000,
                tss=55 + (d % 11) * 6,
            ))
        if dow in (1, 3):
            session.add(GymWorkout(
                athlete_id=athlete_id, date=day, duration_minutes=50, exercises=[]
            ))
    session.commit()
    return n, start


def main():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    athlete = Athlete(email="bench@example.com", display_name="Bench", ftp_watts=250)
    session.add(athlete)
    session.commit()

    n_acts, start = build(session, athlete.id)

    queries = []
    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, params, context, executemany):
        queries.append(statement.split()[0].upper())

    t0 = time.perf_counter()
    recompute_load(session, athlete, start, date.today())
    session.commit()
    elapsed = time.perf_counter() - t0

    selects = sum(1 for q in queries if q == "SELECT")
    writes = sum(1 for q in queries if q in ("INSERT", "UPDATE"))

    print(f"window            {DAYS} days ({WEEKS} weeks)")
    print(f"activities        {n_acts}")
    print(f"total queries     {len(queries)}")
    print(f"  selects         {selects}")
    print(f"  inserts/updates {writes}")
    print(f"queries per day   {len(queries) / DAYS:.1f}")
    print(f"wall time         {elapsed * 1000:.1f} ms  (in-memory sqlite)")
    print()
    for ms in (1, 2, 3):
        print(f"projected @ {ms}ms/round-trip   {len(queries) * ms / 1000:.1f} s")


if __name__ == "__main__":
    main()
