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


class TestCascadeFromChange:
    """
    recompute_from is what makes late arrivals correct. The old sync path
    recomputed a fixed 90 day window from today, which both did unnecessary
    work and silently missed any upload older than 90 days.
    """

    def test_cascade_covers_every_day_from_the_change_forward(self, db, athlete, add_activity):
        from compute.load import recompute_from
        for i in range(30):
            add_activity(START + timedelta(days=i), tss=60)
        end = START + timedelta(days=29)
        recompute_load(db, athlete, START, end)
        db.commit()
        before = [m.ctl for m in all_metrics(db, athlete)]

        add_activity(START + timedelta(days=10), tss=200)
        days = recompute_from(db, athlete, START + timedelta(days=10), through=end)
        db.commit()
        after = [m.ctl for m in all_metrics(db, athlete)]

        assert days == 20
        assert before[:10] == after[:10], "days before the change must not move"
        assert all(b < a for b, a in zip(before[10:], after[10:])), \
            "every day from the change onward must rise"

    def test_cascade_matches_a_full_recompute(self, db, athlete, add_activity):
        """The cheap targeted recompute must produce identical numbers to redoing everything."""
        from compute.load import recompute_from
        for i in range(40):
            add_activity(START + timedelta(days=i), tss=70)
        end = START + timedelta(days=39)
        recompute_load(db, athlete, START, end)
        db.commit()

        add_activity(START + timedelta(days=15), tss=180)
        recompute_from(db, athlete, START + timedelta(days=15), through=end)
        db.commit()
        cascaded = [(m.date, m.ctl, m.atl) for m in all_metrics(db, athlete)]

        for m in all_metrics(db, athlete):
            db.delete(m)
        db.commit()
        recompute_load(db, athlete, START, end)
        db.commit()
        full = [(m.date, m.ctl, m.atl) for m in all_metrics(db, athlete)]

        assert cascaded == full

    def test_fixed_90_day_window_misses_older_uploads(self, db, athlete, add_activity):
        """
        The regression this replaced. An activity 120 days old falls outside a
        90 day window, so the old code left its effect out of history entirely.
        """
        from compute.load import recompute_from
        old_day = START
        end = START + timedelta(days=150)
        for i in range(0, 151, 5):
            add_activity(START + timedelta(days=i), tss=60)
        recompute_load(db, athlete, START, end)
        db.commit()
        baseline = metrics(db, athlete, end).ctl

        add_activity(old_day, tss=300)

        # A 90 day window starting from the end never reaches old_day.
        recompute_from(db, athlete, end - timedelta(days=90), through=end)
        db.commit()
        windowed = metrics(db, athlete, end).ctl
        assert windowed == pytest.approx(baseline), "the old approach cannot see the change"

        recompute_from(db, athlete, old_day, through=end)
        db.commit()
        cascaded = metrics(db, athlete, end).ctl
        assert cascaded > baseline, "cascading from the event date does see it"

    def test_returns_zero_when_nothing_to_do(self, db, athlete):
        from compute.load import recompute_from
        assert recompute_from(db, athlete, START + timedelta(days=5), through=START) == 0


class TestEarliestUncountedActivity:
    def test_finds_the_oldest_day_with_no_metrics_row(self, db, athlete, add_activity):
        from compute.load import earliest_uncounted_activity
        for i in range(10):
            add_activity(START + timedelta(days=i), tss=50)
        recompute_load(db, athlete, START, START + timedelta(days=9))
        db.commit()
        assert earliest_uncounted_activity(db, athlete.id) is None

        backdated = START - timedelta(days=45)
        add_activity(backdated, tss=90)
        assert earliest_uncounted_activity(db, athlete.id) == backdated

    def test_returns_none_when_there_are_no_activities(self, db, athlete):
        from compute.load import earliest_uncounted_activity
        assert earliest_uncounted_activity(db, athlete.id) is None


class TestAutoflushRegression:
    """
    The session runs with autoflush disabled. That makes freshly added rows
    invisible to later queries in the same session until something flushes,
    which silently produced a flat fitness chart: fifty ingested activities
    were never scored, committed with a NULL TSS, and the EMA summed zeros.
    """

    def test_added_activities_are_invisible_until_flush(self, db, athlete):
        from datetime import datetime
        from db.models import Activity

        db.add(Activity(
            athlete_id=athlete.id, garmin_activity_id="pending", discipline="running",
            start_time=datetime.combine(START, datetime.min.time()),
            duration_seconds=3600, avg_heart_rate=150, tss=None,
        ))
        # No flush yet, so a query cannot see it. This is the trap.
        assert db.query(Activity).filter(Activity.tss.is_(None)).count() == 0

        db.flush()
        assert db.query(Activity).filter(Activity.tss.is_(None)).count() == 1

    def test_unscored_activities_produce_no_training_load(self, db, athlete):
        """A NULL TSS contributes nothing, which is why the bug was invisible."""
        from datetime import datetime
        from db.models import Activity

        db.add(Activity(
            athlete_id=athlete.id, garmin_activity_id="unscored", discipline="running",
            start_time=datetime.combine(START, datetime.min.time()),
            duration_seconds=3600, avg_heart_rate=155, tss=None,
        ))
        db.commit()

        recompute_load(db, athlete, START, START)
        db.commit()
        assert metrics(db, athlete, START).ctl == 0.0

    def test_scoring_before_recompute_produces_real_load(self, db, athlete):
        """The fix: score the activities, flush, then recompute."""
        from datetime import datetime
        from db.models import Activity
        from compute.tss import estimate_activity_tss

        act = Activity(
            athlete_id=athlete.id, garmin_activity_id="scored", discipline="running",
            start_time=datetime.combine(START, datetime.min.time()),
            duration_seconds=3600, avg_heart_rate=175, tss=None,
        )
        db.add(act)
        db.flush()

        for a in db.query(Activity).filter(Activity.tss.is_(None)).all():
            a.tss = estimate_activity_tss(
                discipline=a.discipline, duration_seconds=a.duration_seconds,
                avg_hr=a.avg_heart_rate, avg_power=a.avg_power,
                ftp_watts=athlete.ftp_watts, threshold_hr=None,
            )
        db.flush()

        recompute_load(db, athlete, START, START)
        db.commit()
        assert metrics(db, athlete, START).ctl > 0
        assert metrics(db, athlete, START).daily_tss == pytest.approx(100, abs=1)
