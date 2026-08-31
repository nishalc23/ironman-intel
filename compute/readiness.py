"""
Training readiness from sleep and recovery signals.

The previous version averaged sleep score, HRV and resting HR with equal
weight and absolute thresholds. That produced a green "ready to train hard" on
a night of 5.3 hours and a Garmin sleep score of 68, because an HRV of 87ms
scored a capped 100 and outvoted the bad night. Three things were wrong:

1. Sleep duration was not an input at all. Five hours and nine hours scored
   identically as long as the quality score matched.
2. A flat mean lets a strong signal hide a weak one. Recovery does not work
   that way. Too little sleep is not offset by good heart rate variability.
3. HRV and resting HR were judged against fixed cutoffs. Both are highly
   individual, so a number is only meaningful next to that athlete's own
   normal. 87ms means nothing until you know their baseline is 88.

This version scores duration explicitly, compares HRV and resting HR to the
athlete's rolling baseline, and lets the weakest signal cap the result.
"""
from dataclasses import dataclass

# Sleep need for an endurance athlete in a build block. Below the floor no
# other signal can produce a green, however good it looks.
IDEAL_SLEEP_HOURS = 8.0
ADEQUATE_SLEEP_HOURS = 7.0
SHORT_SLEEP_HOURS = 6.0

# A baseline needs a few nights before it means anything.
MIN_NIGHTS_FOR_BASELINE = 3


@dataclass(frozen=True)
class Readiness:
    score: int              # 0-100
    signal: str             # green | yellow | red
    headline: str           # what to actually do today
    limiter: str | None     # the weakest signal, or None when nothing is limiting


def _duration_points(hours: float | None) -> int | None:
    """
    Piecewise, because sleep need is not linear. Going from 5 to 6 hours
    matters far more than going from 8 to 9.
    """
    if hours is None:
        return None
    if hours >= IDEAL_SLEEP_HOURS:
        return 100
    if hours >= ADEQUATE_SLEEP_HOURS:
        # 7.0 -> 80, 8.0 -> 100
        return int(80 + (hours - ADEQUATE_SLEEP_HOURS) * 20)
    if hours >= SHORT_SLEEP_HOURS:
        # 6.0 -> 55, 7.0 -> 80
        return int(55 + (hours - SHORT_SLEEP_HOURS) * 25)
    if hours >= 5.0:
        # 5.0 -> 25, 6.0 -> 55
        return int(25 + (hours - 5.0) * 30)
    return max(0, int(hours * 5))


def _relative_points(value: float | None, baseline: float | None,
                     higher_is_better: bool) -> int | None:
    """
    Score a value against the athlete's own baseline as a percentage deviation.

    Without a baseline there is nothing meaningful to say, so this returns None
    and the caller drops the signal rather than inventing a number from an
    absolute threshold.
    """
    if value is None or baseline is None or baseline <= 0:
        return None

    deviation = (value - baseline) / baseline
    if not higher_is_better:
        deviation = -deviation

    # +10% off baseline is excellent, -15% is a genuine warning.
    if deviation >= 0.10:
        return 100
    if deviation >= 0.0:
        return int(80 + deviation * 200)      # 0% -> 80, +10% -> 100
    if deviation >= -0.05:
        return int(80 + deviation * 400)      # -5% -> 60
    if deviation >= -0.15:
        return int(60 + (deviation + 0.05) * 400)  # -15% -> 20
    return max(0, int(20 + (deviation + 0.15) * 100))


def compute_readiness(
    sleep_score: int | None,
    duration_hours: float | None,
    hrv: float | None,
    resting_hr: int | None,
    hrv_baseline: float | None = None,
    rhr_baseline: float | None = None,
) -> Readiness:
    """
    Combine the signals, weighted, then let the weakest one cap the result.

    Baselines are the athlete's recent rolling averages. Pass None for either
    and that signal is skipped rather than guessed at.
    """
    components: dict[str, tuple[int, float]] = {}  # name -> (points, weight)

    duration = _duration_points(duration_hours)
    if duration is not None:
        components["sleep duration"] = (duration, 0.35)

    if sleep_score is not None:
        components["sleep quality"] = (sleep_score, 0.35)

    hrv_points = _relative_points(hrv, hrv_baseline, higher_is_better=True)
    if hrv_points is not None:
        components["HRV"] = (hrv_points, 0.20)

    rhr_points = _relative_points(
        float(resting_hr) if resting_hr is not None else None,
        rhr_baseline, higher_is_better=False,
    )
    if rhr_points is not None:
        components["resting HR"] = (rhr_points, 0.10)

    if not components:
        return Readiness(50, "yellow", "No recovery data yet.", None)

    total_weight = sum(w for _, w in components.values())
    weighted = sum(p * w for p, w in components.values()) / total_weight

    # The weakest signal caps the score. A weighted mean alone would let good
    # HRV carry a five hour night into the green, which is the bug this fixes.
    worst_name, (worst_points, _) = min(components.items(), key=lambda kv: kv[1][0])
    score = int(min(weighted, worst_points + 20))

    # A hard floor on duration. No combination of other signals says "train
    # hard" after a genuinely short night.
    if duration_hours is not None and duration_hours < SHORT_SLEEP_HOURS:
        score = min(score, 55)

    limiter = worst_name if worst_points < 60 else None

    if score >= 75:
        signal, headline = "green", "Ready to train hard"
    elif score >= 55:
        signal, headline = "yellow", "Train, but keep it easy"
    else:
        signal, headline = "red", "Recover today"

    if limiter:
        headline = f"{headline} · {limiter} is low"

    return Readiness(score, signal, headline, limiter)


def rolling_baseline(values: list[float | None], exclude_last: bool = True) -> float | None:
    """
    Mean of recent readings, ignoring gaps.

    The most recent night is excluded by default so tonight is compared against
    the nights before it rather than against itself, which would drag the
    baseline toward whatever just happened and mute every signal.
    """
    usable = [v for v in (values[:-1] if exclude_last and values else values) if v is not None]
    if len(usable) < MIN_NIGHTS_FOR_BASELINE:
        return None
    return sum(usable) / len(usable)
