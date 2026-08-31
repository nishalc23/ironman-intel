"""
TSS formula tests.

The anchor for every discipline is the same: one hour at threshold equals
TSS 100. If a formula drifts off that scale, CTL and ATL become meaningless
because they are just weighted sums of these numbers.
"""
import math

import pytest

from compute.tss import (
    cycling_tss,
    hr_based_tss,
    gym_tss,
    estimate_activity_tss,
    DEFAULT_THRESHOLD_HR,
    DEFAULT_RESTING_HR,
)

HOUR = 3600.0


class TestCyclingTSS:
    def test_one_hour_at_ftp_is_100(self):
        assert cycling_tss(HOUR, avg_power=250, ftp_watts=250) == pytest.approx(100.0)

    def test_scales_linearly_with_duration(self):
        one = cycling_tss(HOUR, 250, 250)
        two = cycling_tss(2 * HOUR, 250, 250)
        assert two == pytest.approx(2 * one)

    def test_scales_quadratically_with_intensity(self):
        """TSS uses power squared over FTP squared, so half power is a quarter TSS."""
        full = cycling_tss(HOUR, 250, 250)
        half = cycling_tss(HOUR, 125, 250)
        assert half == pytest.approx(full / 4)

    def test_above_threshold_exceeds_100(self):
        assert cycling_tss(HOUR, 300, 250) > 100

    @pytest.mark.parametrize("power,ftp", [(0, 250), (None, 250), (250, 0), (250, None)])
    def test_missing_inputs_return_zero(self, power, ftp):
        assert cycling_tss(HOUR, power, ftp) == 0.0


class TestHeartRateTSS:
    def test_one_hour_at_threshold_hr_is_100(self):
        assert hr_based_tss(HOUR, avg_hr=DEFAULT_THRESHOLD_HR) == pytest.approx(100.0)

    def test_scales_linearly_with_duration(self):
        one = hr_based_tss(HOUR, 175)
        two = hr_based_tss(2 * HOUR, 175)
        assert two == pytest.approx(2 * one)

    def test_easy_effort_is_far_below_100(self):
        """An hour at 120 bpm is genuine aerobic work but nowhere near threshold."""
        easy = hr_based_tss(HOUR, avg_hr=120)
        assert 0 < easy < 40

    def test_monotonic_in_heart_rate(self):
        values = [hr_based_tss(HOUR, hr) for hr in range(100, 180, 5)]
        assert all(b > a for a, b in zip(values, values[1:]))

    def test_hr_at_or_below_resting_returns_zero(self):
        assert hr_based_tss(HOUR, avg_hr=DEFAULT_RESTING_HR) == 0.0
        assert hr_based_tss(HOUR, avg_hr=40) == 0.0

    def test_missing_hr_returns_zero(self):
        assert hr_based_tss(HOUR, avg_hr=None) == 0.0

    def test_ratio_is_capped_so_a_bad_reading_cannot_explode(self):
        """Garmin sometimes reports 220 bpm from a dropout. Cap keeps TSS sane."""
        capped = hr_based_tss(HOUR, avg_hr=1000)
        assert capped == pytest.approx(hr_based_tss(HOUR, avg_hr=int(
            DEFAULT_RESTING_HR + 1.5 * (DEFAULT_THRESHOLD_HR - DEFAULT_RESTING_HR))))


class TestGymTSS:
    def test_45_minutes_is_50(self):
        assert gym_tss(45) == pytest.approx(50.0)

    def test_scales_linearly(self):
        assert gym_tss(90) == pytest.approx(100.0)


class TestEstimateActivityTSS:
    def test_cycling_prefers_power_over_heart_rate(self):
        with_power = estimate_activity_tss("cycling", HOUR, avg_hr=150, avg_power=250,
                                           ftp_watts=250, threshold_hr=175)
        assert with_power == pytest.approx(100.0, abs=0.05)

    def test_cycling_without_power_falls_back_to_heart_rate(self):
        result = estimate_activity_tss("cycling", HOUR, avg_hr=175, avg_power=None,
                                       ftp_watts=250, threshold_hr=175)
        assert result == pytest.approx(100.0, abs=0.05)

    def test_running_uses_heart_rate(self):
        result = estimate_activity_tss("running", HOUR, avg_hr=175, avg_power=None,
                                       ftp_watts=None, threshold_hr=175)
        assert result == pytest.approx(100.0, abs=0.05)

    def test_no_sensor_data_falls_back_to_duration(self):
        """A pool swim with no HR strap still has to produce a plausible number."""
        result = estimate_activity_tss("swimming", HOUR, avg_hr=None, avg_power=None,
                                       ftp_watts=None, threshold_hr=None)
        assert result == pytest.approx(50.0)

    def test_uses_athlete_thresholds_not_defaults(self):
        """A fitter athlete with a higher FTP earns less TSS for the same watts."""
        fit = estimate_activity_tss("cycling", HOUR, None, 250, ftp_watts=300, threshold_hr=175)
        unfit = estimate_activity_tss("cycling", HOUR, None, 250, ftp_watts=200, threshold_hr=175)
        assert fit < 100 < unfit
