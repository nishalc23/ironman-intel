"""
The fixed weekly training template.

Eleven sessions across six training days plus one full rest day, repeating
every week. Session keys are stable strings so completion records survive a
template edit: renaming a label does not orphan a checkmark, but changing a
key does, which is deliberate.

Weekly volume:
    swim  2x   1 endurance, 1 intervals
    bike  4x   2 easy, 1 threshold, 1 intervals
    run   4x   2 easy, 1 threshold, 1 intervals
    brick 1x   bike into run off the bike
    rest  1x   one full day off
"""
from dataclasses import dataclass, asdict
from datetime import date, timedelta

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass(frozen=True)
class Session:
    key: str          # stable identifier, used for completion records
    discipline: str   # swim | bike | run | brick | rest
    intensity: str    # endurance | easy | threshold | intervals | brick | rest
    label: str

    def to_dict(self):
        return asdict(self)


# Hard days are spaced so no two interval or threshold sessions in the same
# discipline land back to back, and the brick sits the day before the rest day.
TEMPLATE: dict[int, list[Session]] = {
    0: [  # Monday
        Session("mon_swim_endurance", "swim", "endurance", "Swim endurance"),
        Session("mon_bike_easy", "bike", "easy", "Bike easy"),
    ],
    1: [  # Tuesday
        Session("tue_run_intervals", "run", "intervals", "Run intervals"),
        Session("tue_bike_easy", "bike", "easy", "Bike easy"),
    ],
    2: [  # Wednesday
        Session("wed_swim_intervals", "swim", "intervals", "Swim intervals"),
        Session("wed_run_easy", "run", "easy", "Run easy"),
    ],
    3: [  # Thursday
        Session("thu_bike_threshold", "bike", "threshold", "Bike threshold"),
        Session("thu_run_easy", "run", "easy", "Run easy"),
    ],
    4: [  # Friday
        Session("fri_bike_intervals", "bike", "intervals", "Bike intervals"),
        Session("fri_run_threshold", "run", "threshold", "Run threshold"),
    ],
    5: [  # Saturday
        Session("sat_brick", "brick", "brick", "Brick: bike into run"),
    ],
    6: [  # Sunday
        Session("sun_rest", "rest", "rest", "Full rest day"),
    ],
}

ALL_KEYS = {s.key for day in TEMPLATE.values() for s in day}

# What a complete week looks like, used to validate the template and to show
# progress counts in the UI.
WEEKLY_TARGETS = {"swim": 2, "bike": 4, "run": 4, "brick": 1, "rest": 1}


def week_start(on: date) -> date:
    """The Monday of the week containing `on`. Weeks are Monday to Sunday."""
    return on - timedelta(days=on.weekday())


def sessions_for(day_index: int) -> list[Session]:
    return TEMPLATE[day_index]


def counts_by_discipline() -> dict[str, int]:
    counts = {}
    for day in TEMPLATE.values():
        for s in day:
            counts[s.discipline] = counts.get(s.discipline, 0) + 1
    return counts
