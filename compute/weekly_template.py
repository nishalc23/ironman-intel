"""
The weekly training requirements.

A flat checklist, not a schedule. Sessions are not pinned to days, because the
athlete decides when each one happens and ticks it off afterwards. What the
week owes you is the count per discipline and intensity:

    swim  2x   1 endurance, 1 intervals
    bike  4x   2 easy, 1 threshold, 1 intervals
    run   4x   2 easy, 1 threshold, 1 intervals
    brick 1x   bike into run
    rest  1x   one full day off

Weeks open Monday 00:00 and close Sunday 23:59. Completions are bucketed by
the opening Monday, so a session ticked on Sunday night lands in the week that
is about to close rather than the one starting the next morning.

Completion keys are stable strings, so renaming a label keeps existing
checkmarks while changing a key deliberately orphans them.
"""
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Requirement:
    key: str          # stable identifier used by completion records
    discipline: str   # swim | bike | run | brick | rest
    intensity: str    # endurance | easy | threshold | intervals | brick | rest
    label: str


# Order matters: this is the order they appear in the UI, hardest last within
# each discipline so the easy volume reads first.
REQUIREMENTS: list[Requirement] = [
    Requirement("swim_endurance", "swim", "endurance", "Endurance"),
    Requirement("swim_intervals", "swim", "intervals", "Intervals"),

    Requirement("bike_easy_1", "bike", "easy", "Easy"),
    Requirement("bike_easy_2", "bike", "easy", "Easy"),
    Requirement("bike_threshold", "bike", "threshold", "Threshold"),
    Requirement("bike_intervals", "bike", "intervals", "Intervals"),

    Requirement("run_easy_1", "run", "easy", "Easy"),
    Requirement("run_easy_2", "run", "easy", "Easy"),
    Requirement("run_threshold", "run", "threshold", "Threshold"),
    Requirement("run_intervals", "run", "intervals", "Intervals"),

    Requirement("brick", "brick", "brick", "Bike into run"),

    Requirement("rest", "rest", "rest", "Full day off"),
]

ALL_KEYS = {r.key for r in REQUIREMENTS}

DISCIPLINE_ORDER = ["swim", "bike", "run", "brick", "rest"]

# Sessions that count as training. Rest is a requirement you tick, but it is
# not work, so it stays out of the training totals.
TRAINING_KEYS = {r.key for r in REQUIREMENTS if r.discipline != "rest"}


def targets() -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in REQUIREMENTS:
        counts[r.discipline] = counts.get(r.discipline, 0) + 1
    return counts


def week_start(on: date) -> date:
    """The Monday on or before `on`. Python's weekday() is already Monday 0."""
    return on - timedelta(days=on.weekday())


def week_end(on: date) -> date:
    """The Sunday that closes the week, six days after it opens."""
    return week_start(on) + timedelta(days=6)


def by_discipline() -> dict[str, list[Requirement]]:
    grouped: dict[str, list[Requirement]] = {}
    for r in REQUIREMENTS:
        grouped.setdefault(r.discipline, []).append(r)
    return grouped
