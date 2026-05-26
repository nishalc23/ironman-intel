"""
CTL / ATL / TSB computation from daily TSS values.

Both CTL and ATL are exponential moving averages — they weight recent days
more heavily than older ones. The time constants (42 days for CTL, 7 for ATL)
are from Coggan's Performance Manager model, standard across all serious
triathlon/cycling software.
"""
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


def recompute_load(db: Session, athlete: Athlete, from_date: date, to_date: date):
    """
    Rebuild DailyMetrics rows from from_date to to_date.

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

    current = from_date
    while current <= to_date:
        daily_tss = get_daily_tss(db, athlete.id, current)

        # EMA update: new_value = old_value × decay + today_tss × (1 − decay)
        ctl = ctl * CTL_DECAY + daily_tss * (1 - CTL_DECAY)
        atl = atl * ATL_DECAY + daily_tss * (1 - ATL_DECAY)
        tsb = ctl - atl

        # Get volume by discipline for this day
        acts = (
            db.query(Activity)
            .filter(
                Activity.athlete_id == athlete.id,
                Activity.start_time >= current,
                Activity.start_time < current + timedelta(days=1),
            )
            .all()
        )

        swim_m = sum(a.distance_meters or 0 for a in acts if a.discipline == "swimming")
        bike_m = sum(a.distance_meters or 0 for a in acts if a.discipline == "cycling")
        run_m  = sum(a.distance_meters or 0 for a in acts if a.discipline == "running")

        existing = (
            db.query(DailyMetrics)
            .filter_by(athlete_id=athlete.id, date=current)
            .first()
        )

        if existing:
            existing.ctl = round(ctl, 2)
            existing.atl = round(atl, 2)
            existing.tsb = round(tsb, 2)
            existing.daily_tss = round(daily_tss, 1)
            existing.swim_volume_meters = swim_m
            existing.bike_volume_meters = bike_m
            existing.run_volume_meters = run_m
        else:
            db.add(DailyMetrics(
                athlete_id=athlete.id,
                date=current,
                ctl=round(ctl, 2),
                atl=round(atl, 2),
                tsb=round(tsb, 2),
                daily_tss=round(daily_tss, 1),
                swim_volume_meters=swim_m,
                bike_volume_meters=bike_m,
                run_volume_meters=run_m,
            ))

        current += timedelta(days=1)
