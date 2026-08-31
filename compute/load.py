"""
CTL / ATL / TSB computation from daily TSS values.

Both CTL and ATL are exponential moving averages — they weight recent days
more heavily than older ones. The time constants (42 days for CTL, 7 for ATL)
are from Coggan's Performance Manager model, standard across all serious
triathlon/cycling software.
"""
from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import Session

from db.models import Activity, DailyMetrics, Athlete, GymWorkout
from compute.tss import estimate_activity_tss, gym_tss

CTL_DAYS = 42
ATL_DAYS = 7


def _ema_factor(time_constant: int) -> float:
    """e^(-1/tc) — the decay factor for one day with no training."""
    import math
    return math.exp(-1 / time_constant)


CTL_DECAY = _ema_factor(CTL_DAYS)   # ≈ 0.9764
ATL_DECAY = _ema_factor(ATL_DAYS)   # ≈ 0.8669


def get_daily_tss(db: Session, athlete_id: int, on_date: date) -> float:
    """Sum TSS from all activities (including gym) on a given date."""
    activities = (
        db.query(Activity)
        .filter(
            Activity.athlete_id == athlete_id,
            Activity.start_time >= on_date,
            Activity.start_time < on_date + timedelta(days=1),
        )
        .all()
    )

    gym_sessions = (
        db.query(GymWorkout)
        .filter(
            GymWorkout.athlete_id == athlete_id,
            GymWorkout.date == on_date,
        )
        .all()
    )

    total = sum(a.tss or 0 for a in activities)
    total += sum(gym_tss(g.duration_minutes or 45) for g in gym_sessions)
    return total


def _load_window(db: Session, athlete_id: int, from_date: date, to_date: date):
    """
    Pull the whole window in two queries and bucket it by day in memory.

    Returns (tss_by_day, volume_by_day). Days with no training are absent from
    both, which callers treat as zero, because that is what a rest day is.
    """
    activities = (
        db.query(Activity)
        .filter(
            Activity.athlete_id == athlete_id,
            Activity.start_time >= from_date,
            Activity.start_time < to_date + timedelta(days=1),
        )
        .all()
    )

    gym_sessions = (
        db.query(GymWorkout)
        .filter(
            GymWorkout.athlete_id == athlete_id,
            GymWorkout.date >= from_date,
            GymWorkout.date <= to_date,
        )
        .all()
    )

    tss_by_day = defaultdict(float)
    volume_by_day = defaultdict(lambda: {"swimming": 0.0, "cycling": 0.0, "running": 0.0})

    for a in activities:
        day = a.start_time.date()
        tss_by_day[day] += a.tss or 0
        if a.discipline in volume_by_day[day]:
            volume_by_day[day][a.discipline] += a.distance_meters or 0

    for g in gym_sessions:
        tss_by_day[g.date] += gym_tss(g.duration_minutes or 45)

    return tss_by_day, volume_by_day


def recompute_load(db: Session, athlete: Athlete, from_date: date, to_date: date):
    """
    Rebuild DailyMetrics rows from from_date to to_date.

    The EMA is inherently sequential, so the day loop stays. What does not need
    to be sequential is the data access: this pulls the whole window up front in
    a fixed number of queries and writes back in two batched statements, rather
    than issuing five queries per day inside the loop.

    We need the CTL/ATL values from the day before from_date as the starting
    point. If there's no prior row we start from zero (athlete just began training).
    """
    prior = (
        db.query(DailyMetrics)
        .filter(
            DailyMetrics.athlete_id == athlete.id,
            DailyMetrics.date < from_date,
        )
        .order_by(DailyMetrics.date.desc())
        .first()
    )

    ctl = prior.ctl if prior else 0.0
    atl = prior.atl if prior else 0.0

    tss_by_day, volume_by_day = _load_window(db, athlete.id, from_date, to_date)

    existing_by_day = {
        m.date: m
        for m in db.query(DailyMetrics).filter(
            DailyMetrics.athlete_id == athlete.id,
            DailyMetrics.date >= from_date,
            DailyMetrics.date <= to_date,
        )
    }

    updates, inserts = [], []

    current = from_date
    while current <= to_date:
        daily_tss = tss_by_day.get(current, 0.0)

        # EMA update: new_value = old_value x decay + today_tss x (1 - decay)
        ctl = ctl * CTL_DECAY + daily_tss * (1 - CTL_DECAY)
        atl = atl * ATL_DECAY + daily_tss * (1 - ATL_DECAY)
        tsb = ctl - atl

        vol = volume_by_day.get(current)

        # Store full precision. Rounding here used to cause two bugs: the stored
        # TSB stopped equalling stored CTL minus stored ATL, and an incremental
        # recompute resumed from a rounded prior day and drifted away from a
        # full recompute. Presentation rounds instead - see routes/metrics.py.
        row = {
            "ctl": ctl,
            "atl": atl,
            "tsb": tsb,
            "daily_tss": daily_tss,
            "swim_volume_meters": vol["swimming"] if vol else 0.0,
            "bike_volume_meters": vol["cycling"] if vol else 0.0,
            "run_volume_meters": vol["running"] if vol else 0.0,
        }

        existing = existing_by_day.get(current)
        if existing:
            updates.append({"id": existing.id, **row})
        else:
            inserts.append({"athlete_id": athlete.id, "date": current, **row})

        current += timedelta(days=1)

    # Two batched statements instead of one round trip per day.
    if updates:
        db.bulk_update_mappings(DailyMetrics, updates)
    if inserts:
        db.bulk_insert_mappings(DailyMetrics, inserts)


def recompute_from(db: Session, athlete: Athlete, earliest_affected: date,
                   through: date | None = None) -> int:
    """
    Cascade recomputation forward from the earliest event date that changed.

    Garmin uploads are ordered by when they sync, not by when the workout
    happened. A ride that lands three days late invalidates CTL and ATL for its
    own date and every day after it, because the EMA at day N depends on day
    N-1. Recomputing only recent days leaves that gap silently wrong, and
    recomputing a fixed 90 day window misses anything older than 90 days.

    Returns the number of days recomputed.
    """
    through = through or date.today()
    if earliest_affected > through:
        return 0
    recompute_load(db, athlete, earliest_affected, through)
    return (through - earliest_affected).days + 1


def earliest_uncounted_activity(db: Session, athlete_id: int) -> date | None:
    """
    The event date of the oldest activity whose day has no DailyMetrics row.

    Used after ingestion to find where history diverged, so a backdated upload
    is caught even when the caller does not know which dates it touched.
    """
    counted = {
        d for (d,) in db.query(DailyMetrics.date)
        .filter(DailyMetrics.athlete_id == athlete_id)
    }
    dates = sorted({
        start.date() for (start,) in db.query(Activity.start_time)
        .filter(Activity.athlete_id == athlete_id)
    })
    for d in dates:
        if d not in counted:
            return d
    return None
