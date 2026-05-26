"""
TSS (Training Stress Score) computation for each discipline.

All formulas target the same scale: a 1-hour effort at threshold = TSS 100.
"""
import math


DEFAULT_FTP_WATTS = 200
DEFAULT_THRESHOLD_HR = 175      # rough lactate threshold HR for recreational athlete
DEFAULT_RESTING_HR = 55


def cycling_tss(duration_seconds: float, avg_power: int, ftp_watts: int) -> float:
    """
    Power-based TSS. Most accurate when athlete has a power meter.
    TSS = (duration_s × NP × IF) / (FTP × 3600) × 100
    We use avg_power as a proxy for NP here — NP needs second-by-second data.
    """
    if not avg_power or not ftp_watts or ftp_watts == 0:
        return 0.0
    intensity_factor = avg_power / ftp_watts
    return (duration_seconds * avg_power * intensity_factor) / (ftp_watts * 3600) * 100


def hr_based_tss(
    duration_seconds: float,
    avg_hr: int,
    threshold_hr: int = DEFAULT_THRESHOLD_HR,
    resting_hr: int = DEFAULT_RESTING_HR,
) -> float:
    """
    TRIMP-based hrTSS — used for running and swimming where we rarely have power.

    TRIMP formula: duration_min × hr_ratio × 0.64 × e^(1.92 × hr_ratio)
    where hr_ratio = (avg_hr − resting_hr) / (threshold_hr − resting_hr)

    Scaled so that 60 min at threshold HR = TSS 100.
    """
    if not avg_hr or avg_hr <= resting_hr:
        return 0.0

    hr_range = threshold_hr - resting_hr
    if hr_range <= 0:
        return 0.0

    hr_ratio = (avg_hr - resting_hr) / hr_range
    hr_ratio = min(hr_ratio, 1.5)  # cap at 150% to prevent absurd values

    duration_minutes = duration_seconds / 60
    trimp = duration_minutes * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)

    # Normalize: at threshold (hr_ratio=1.0) for 60 min, TRIMP ≈ 48.5
    # Scale so 60 min at threshold = 100 TSS
    normalization_factor = 100 / (60 * 1.0 * 0.64 * math.exp(1.92))
    return trimp * normalization_factor


def gym_tss(duration_minutes: float) -> float:
    """
    Strength sessions don't fit cleanly into aerobic TSS.
    Rule of thumb: 45 min of hard lifting ≈ TSS 50.
    """
    return (duration_minutes / 45) * 50


def estimate_activity_tss(
    discipline: str,
    duration_seconds: float,
    avg_hr: int | None,
    avg_power: int | None,
    ftp_watts: int | None,
    threshold_hr: int | None,
) -> float:
    ftp = ftp_watts or DEFAULT_FTP_WATTS
    thr_hr = threshold_hr or DEFAULT_THRESHOLD_HR

    if discipline == "cycling" and avg_power:
        return round(cycling_tss(duration_seconds, avg_power, ftp), 1)

    if avg_hr:
        return round(hr_based_tss(duration_seconds, avg_hr, thr_hr), 1)

    # Fallback: assume moderate effort based on duration alone
    return round((duration_seconds / 3600) * 50, 1)
