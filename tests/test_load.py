"""
CTL / ATL / TSB tests.

CTL and ATL are exponential moving averages over daily TSS with 42 and 7 day
time constants. The properties below are what make the numbers trustworthy:
they converge to sustained load, they decay when training stops, and
recomputing over a range must not change an already correct answer.
"""
import math
from datetime import date, datetime, timedelta

import pytest

from compute.load import (
    recompute_load,
    get_daily_tss,
    CTL_DECAY,
    ATL_DECAY,
    CTL_DAYS,
    ATL_DAYS,
)
from db.models import DailyMetrics, GymWorkout

START = date(2026, 1, 1)


def metrics(db, athlete, on_date):
    return db.query(DailyMetrics).filter_by(athlete_id=athlete.id, date=on_date).one()


def all_metrics(db, athlete):
    return db.query(DailyMetrics).filter_by(athlete_id=athlete.id).order_by(DailyMetrics.date).all()


class TestDecayConstants:
    def test_constants_match_the_coggan_time_constants(self):
        assert CTL_DECAY == pytest.approx(math.exp(-1 / CTL_DAYS))
        assert ATL_DECAY == pytest.approx(math.exp(-1 / ATL_DAYS))

    def test_atl_reacts_faster_than_ctl(self):
        assert ATL_DECAY < CTL_DECAY


class TestDailyTSS:
    def test_sums_activities_on_the_day(self, db, athlete, add_activity):
        add_activity(START, tss=50)
        add_activity(START, tss=30)
        assert get_daily_tss(db, athlete.id, START) == pytest.approx(80)

    def test_ignores_other_days(self, db, athlete, add_activity):
        add_activity(START, tss=50)
        add_activity(START + timedelta(days=1), tss=30)
        assert get_daily_tss(db, athlete.id, START) == pytest.approx(50)

    def test_includes_gym_sessions(self, db, athlete, add_activity):
        add_activity(START, tss=50)
        db.add(GymWorkout(athlete_id=athlete.id, date=START, duration_minutes=45, exercises=[]))
        db.commit()
        assert get_daily_tss(db, athlete.id, START) == pytest.approx(100)

    def test_late_night_activity_counts_on_its_own_day(self, db, athlete):
        """An 11pm run belongs to that day, not the next one."""
        from db.models import Activity
        db.add(Activity(
            athlete_id=athlete.id, garmin_activity_id="late", discipline="running",
            start_time=datetime.combine(START, datetime.min.time()) + timedelta(hours=23, minutes=30),
            duration_seconds=3600, tss=42,
        ))
        db.commit()
        assert get_daily_tss(db, athlete.id, START) == pytest.approx(42)
        assert get_daily_tss(db, athlete.id, START + timedelta(days=1)) == pytest.approx(0)


class TestRecomputeLoad:
    def test_single_day_applies_one_ema_step(self, db, athlete, add_activity):
        add_activity(START, tss=100)
        recompute_load(db, athlete, START, START)
        db.commit()
        m = metrics(db, athlete, START)
        assert m.ctl == pytest.approx(100 * (1 - CTL_DECAY), abs=0.01)
        assert m.atl == pytest.approx(100 * (1 - ATL_DECAY), abs=0.01)

    def test_tsb_is_ctl_minus_atl(self, db, athlete, add_activity):
        for i in range(20):
            add_activity(START + timedelta(days=i), tss=80)
        recompute_load(db, athlete, START, START + timedelta(days=19))
        db.commit()
        for m in all_metrics(db, athlete):
            assert m.tsb == pytest.approx(m.ctl - m.atl, abs=0.01)

    def test_sustained_load_converges_ctl_toward_that_load(self, db, athlete, add_activity):
        """Train at 100 TSS every day for a year and CTL should approach 100."""
        for i in range(365):
            add_activity(START + timedelta(days=i), tss=100)
        recompute_load(db, athlete, START, START + timedelta(days=364))
        db.commit()
        final = metrics(db, athlete, START + timedelta(days=364))
        assert final.ctl == pytest.approx(100, abs=1.0)
        assert final.atl == pytest.approx(100, abs=1.0)

    def test_atl_climbs_faster_than_ctl_early_on(self, db, athlete, add_activity):
        for i in range(7):
            add_activity(START + timedelta(days=i), tss=100)
        recompute_load(db, athlete, START, START + timedelta(days=6))
        db.commit()
        m = metrics(db, athlete, START + timedelta(days=6))
        assert m.atl > m.ctl
        assert m.tsb < 0  # fatigued, which is correct after a hard week

    def test_rest_decays_both_and_turns_form_positive(self, db, athlete, add_activity):
        for i in range(30):
            add_activity(START + timedelta(days=i), tss=100)
        recompute_load(db, athlete, START, START + timedelta(days=29))
        db.commit()
        loaded = metrics(db, athlete, START + timedelta(days=29))

        recompute_load(db, athlete, START + timedelta(days=30), START + timedelta(days=43))
        db.commit()
        rested = metrics(db, athlete, START + timedelta(days=43))

        assert rested.ctl < loaded.ctl
        assert rested.atl < loaded.atl
        assert rested.tsb > 0  # two weeks off leaves you fresh

    def test_volume_is_split_by_discipline(self, db, athlete, add_activity):
        add_activity(START, tss=30, discipline="swimming", distance=2000)
        add_activity(START, tss=60, discipline="cycling", distance=40000)
        add_activity(START, tss=50, discipline="running", distance=10000)
        recompute_load(db, athlete, START, START)
        db.commit()
        m = metrics(db, athlete, START)
        assert m.swim_volume_meters == pytest.approx(2000)
        assert m.bike_volume_meters == pytest.approx(40000)
        assert m.run_volume_meters == pytest.approx(10000)

    def test_recompute_is_idempotent(self, db, athlete, add_activity):
        """Running the same window twice must not change the answer."""
        for i in range(30):
            add_activity(START + timedelta(days=i), tss=75)
        end = START + timedelta(days=29)

        recompute_load(db, athlete, START, end)
        db.commit()
        first = [(m.date, m.ctl, m.atl, m.tsb) for m in all_metrics(db, athlete)]

        recompute_load(db, athlete, START, end)
        db.commit()
        second = [(m.date, m.ctl, m.atl, m.tsb) for m in all_metrics(db, athlete)]

        assert first == second

    def test_partial_recompute_resumes_from_the_prior_day(self, db, athlete, add_activity):
        """Computing days 0-29 then 30-59 must equal computing 0-59 in one pass."""
        for i in range(60):
            add_activity(START + timedelta(days=i), tss=90)

        recompute_load(db, athlete, START, START + timedelta(days=29))
        db.commit()
        recompute_load(db, athlete, START + timedelta(days=30), START + timedelta(days=59))
        db.commit()
        split = [(m.date, m.ctl, m.atl) for m in all_metrics(db, athlete)]

        for m in all_metrics(db, athlete):
            db.delete(m)
        db.commit()
        recompute_load(db, athlete, START, START + timedelta(days=59))
        db.commit()
        one_pass = [(m.date, m.ctl, m.atl) for m in all_metrics(db, athlete)]

        assert split == one_pass


class TestLateArrivingActivity:
    """
    Garmin uploads are not ordered by when the workout happened. A ride that
    syncs three days late invalidates every CTL value from its own date onward.
    """

    def test_backdated_activity_changes_all_downstream_days(self, db, athlete, add_activity):
        for i in range(30):
            add_activity(START + timedelta(days=i), tss=60)
        end = START + timedelta(days=29)
        recompute_load(db, athlete, START, end)
        db.commit()
        before = metrics(db, athlete, end).ctl

        # A hard ride from day 10 finally uploads.
        add_activity(START + timedelta(days=10), tss=200)
        recompute_load(db, athlete, START + timedelta(days=10), end)
        db.commit()
        after = metrics(db, athlete, end).ctl

        assert after > before, "backdated work must raise fitness on every later day"

    def test_recomputing_only_today_leaves_history_stale(self, db, athlete, add_activity):
        """
        This is the bug the ingestion path has to avoid. If a late activity lands
        and we only recompute the current day, every day in between stays wrong.
        """
        for i in range(30):
            add_activity(START + timedelta(days=i), tss=60)
        end = START + timedelta(days=29)
        recompute_load(db, athlete, START, end)
        db.commit()

        add_activity(START + timedelta(days=10), tss=200)
        recompute_load(db, athlete, end, end)  # naive: only recompute today
        db.commit()
        naive = metrics(db, athlete, end).ctl

        recompute_load(db, athlete, START + timedelta(days=10), end)  # correct: cascade
        db.commit()
        correct = metrics(db, athlete, end).ctl

        assert naive != pytest.approx(correct), "naive recompute should be detectably wrong"
