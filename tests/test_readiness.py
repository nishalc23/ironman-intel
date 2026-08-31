"""
Readiness tests.

These exist because the old model called a 5.3 hour night with a Garmin sleep
score of 68 "green, ready to train hard". It averaged sleep score, HRV and
resting HR equally against absolute thresholds, so a good HRV reading simply
outvoted a bad night. The cases below pin the behaviour that replaced it.
"""
import pytest

from compute.readiness import (
    compute_readiness,
    rolling_baseline,
    SHORT_SLEEP_HOURS,
    MIN_NIGHTS_FOR_BASELINE,
)


class TestTheOriginalBug:
    def test_short_night_with_good_hrv_is_not_green(self):
        """The exact reading that was wrong: 68 score, 5.3h, HRV 87 on an 88 baseline."""
        r = compute_readiness(
            sleep_score=68, duration_hours=5.3, hrv=87.0, resting_hr=51,
            hrv_baseline=88.0, rhr_baseline=52.0,
        )
        assert r.signal != "green"
        assert r.score <= 55
        assert "duration" in (r.limiter or "")

    def test_good_hrv_cannot_rescue_a_short_night(self):
        """Even an exceptional HRV leaves a five hour night out of the green."""
        r = compute_readiness(
            sleep_score=70, duration_hours=5.0, hrv=120.0, resting_hr=44,
            hrv_baseline=80.0, rhr_baseline=52.0,
        )
        assert r.signal != "green"


class TestDuration:
    def test_full_night_with_normal_signals_is_green(self):
        r = compute_readiness(
            sleep_score=88, duration_hours=8.2, hrv=90.0, resting_hr=50,
            hrv_baseline=87.0, rhr_baseline=52.0,
        )
        assert r.signal == "green"
        assert r.limiter is None

    def test_more_sleep_never_scores_worse(self):
        def at(hours):
            return compute_readiness(80, hours, 88.0, 51, 88.0, 51.0).score
        scores = [at(h) for h in (4.0, 5.0, 6.0, 7.0, 8.0, 9.0)]
        assert all(b >= a for a, b in zip(scores, scores[1:]))

    def test_below_the_floor_is_capped_regardless_of_everything_else(self):
        r = compute_readiness(
            sleep_score=100, duration_hours=SHORT_SLEEP_HOURS - 0.1,
            hrv=200.0, resting_hr=40, hrv_baseline=80.0, rhr_baseline=55.0,
        )
        assert r.score <= 55

    def test_missing_duration_still_produces_a_result(self):
        r = compute_readiness(75, None, 88.0, 51, 88.0, 51.0)
        assert 0 <= r.score <= 100
        assert r.signal in ("green", "yellow", "red")


class TestBaselineRelative:
    def test_hrv_is_judged_against_the_athletes_own_normal(self):
        """The same 60ms reading is good for one athlete and bad for another."""
        low_baseline = compute_readiness(85, 8.0, 60.0, 50, hrv_baseline=50.0, rhr_baseline=50.0)
        high_baseline = compute_readiness(85, 8.0, 60.0, 50, hrv_baseline=85.0, rhr_baseline=50.0)
        assert low_baseline.score > high_baseline.score

    def test_suppressed_hrv_pulls_readiness_down(self):
        normal = compute_readiness(85, 8.0, 88.0, 51, 88.0, 51.0)
        suppressed = compute_readiness(85, 8.0, 62.0, 51, 88.0, 51.0)
        assert suppressed.score < normal.score
        assert suppressed.limiter == "HRV"

    def test_elevated_resting_hr_pulls_readiness_down(self):
        normal = compute_readiness(85, 8.0, 88.0, 51, 88.0, 51.0)
        elevated = compute_readiness(85, 8.0, 88.0, 62, 88.0, 51.0)
        assert elevated.score < normal.score

    def test_without_a_baseline_the_signal_is_skipped_not_guessed(self):
        """No baseline means no opinion, rather than an absolute threshold."""
        r = compute_readiness(85, 8.0, 40.0, 51, hrv_baseline=None, rhr_baseline=None)
        assert r.limiter != "HRV"
        assert r.signal == "green"


class TestWeakestLinkCaps:
    def test_one_bad_signal_cannot_be_averaged_away(self):
        r = compute_readiness(
            sleep_score=25, duration_hours=8.5, hrv=95.0, resting_hr=48,
            hrv_baseline=88.0, rhr_baseline=52.0,
        )
        # A flat mean would land near 75. The cap keeps it honest.
        assert r.score <= 45
        assert r.limiter == "sleep quality"

    def test_headline_names_the_limiter(self):
        r = compute_readiness(30, 8.0, 88.0, 51, 88.0, 51.0)
        assert "sleep quality" in r.headline

    def test_no_data_is_yellow_not_green(self):
        r = compute_readiness(None, None, None, None)
        assert r.signal == "yellow"
        assert r.limiter is None


class TestRollingBaseline:
    def test_needs_a_few_nights_before_it_means_anything(self):
        assert rolling_baseline([80.0] * (MIN_NIGHTS_FOR_BASELINE - 1) + [80.0]) is None
        assert rolling_baseline([80.0] * (MIN_NIGHTS_FOR_BASELINE + 1)) == pytest.approx(80.0)

    def test_excludes_the_most_recent_night(self):
        """Tonight must not drag its own baseline toward itself."""
        assert rolling_baseline([80.0, 80.0, 80.0, 20.0]) == pytest.approx(80.0)

    def test_ignores_gaps(self):
        assert rolling_baseline([80.0, None, 90.0, 100.0, None]) == pytest.approx(90.0)

    def test_returns_none_when_empty(self):
        assert rolling_baseline([]) is None
        assert rolling_baseline([None, None]) is None
