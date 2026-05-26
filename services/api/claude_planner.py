import os
import anthropic
from datetime import date, timedelta
from sqlalchemy.orm import Session

from db.models import Athlete, Activity, DailyMetrics, GymWorkout

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _format_activity(act: Activity) -> str:
    dist = f"{act.distance_meters/1000:.1f}km" if act.distance_meters else "—"
    hr   = f"avg HR {act.avg_hr}bpm" if act.avg_heart_rate else ""
    pwr  = f"avg {act.avg_power}W" if act.avg_power else ""
    tss  = f"TSS {act.tss:.0f}" if act.tss else ""
    dur  = f"{act.duration_seconds/60:.0f}min"
    details = ", ".join(filter(None, [dist, dur, hr, pwr, tss]))
    return f"  • {act.start_time.strftime('%a %b %d')} — {act.discipline}: {details}"


UPPER_KEYWORDS = {
    "bench", "press", "fly", "flye", "row", "pull", "pulldown", "curl",
    "tricep", "dip", "shoulder", "lateral", "overhead", "chest", "back",
    "bicep", "face pull", "shrug", "upright",
}
LOWER_KEYWORDS = {
    "squat", "deadlift", "lunge", "leg press", "leg curl", "leg extension",
    "calf", "hip thrust", "glute", "rdl", "romanian", "hack squat",
    "step up", "split squat", "goblet",
}


def _classify_gym_day(g: GymWorkout) -> str:
    """Return 'upper', 'lower', or 'unknown' based on exercises in the session."""
    names = " ".join(e["name"].lower() for e in (g.exercises or []))
    upper = sum(1 for k in UPPER_KEYWORDS if k in names)
    lower = sum(1 for k in LOWER_KEYWORDS if k in names)
    if upper > lower:
        return "upper"
    if lower > upper:
        return "lower"
    return "unknown"


def _next_split_day(recent_gym: list[GymWorkout], split: str) -> str:
    """Given recent gym history, return what today's split day should be."""
    if split != "upper_lower":
        return split  # PPL/Arnold handled generically for now

    for g in recent_gym:  # most recent first
        day = _classify_gym_day(g)
        if day == "upper":
            return "lower"
        if day == "lower":
            return "upper"
    return "upper"  # default if no history


def _format_gym(g: GymWorkout) -> str:
    ex_names = [e["name"] for e in (g.exercises or [])]
    day_type = _classify_gym_day(g)
    label = f"Gym [{day_type}]" if day_type != "unknown" else "Gym"
    exercises = ", ".join(ex_names[:5]) or "general strength"
    dur = f"{g.duration_minutes}min" if g.duration_minutes else ""
    return f"  • {g.date.strftime('%a %b %d')} — {label} {dur}: {exercises}"


def _classify_exercise_name(name: str) -> str:
    """Classify a single exercise as 'upper' or 'lower' based on its name."""
    n = name.lower()
    lower_words = {
        "squat", "leg press", "leg curl", "leg extension", "lunge", "calf",
        "hip adduction", "hip thrust", "glute", "rdl", "romanian", "deadlift",
        "hack squat", "step up", "split squat", "goblet", "back extension",
        "hyperextension", "leg raise", "crunch", "ab ", "abs", "core",
        "hip abduction", "lying leg", "seated leg", "decline crunch",
    }
    for kw in lower_words:
        if kw in n:
            return "lower"
    return "upper"


def _build_exercise_library(all_gym: list[GymWorkout]) -> dict[str, dict]:
    """
    Walk all gym history and build a dict of exercise_name → {last_weight_kg, category}.
    Classifies each exercise by its own name (not the session).
    Skips cardio-only entries (treadmill, swimming, etc.).
    """
    CARDIO = {"treadmill", "swimming", "stair machine", "bike", "elliptical", "rower"}
    library: dict[str, dict] = {}

    for workout in all_gym:  # oldest first so latest overwrites
        for ex in (workout.exercises or []):
            name = ex["name"]
            if any(c in name.lower() for c in CARDIO):
                continue
            working_sets = [
                s for s in ex.get("sets", [])
                if s.get("set_type") not in ("warmup",) and s.get("reps")
            ]
            if not working_sets:
                continue
            # Use heaviest working set weight as the reference
            weights = [s["weight_kg"] for s in working_sets if s.get("weight_kg")]
            best_weight = max(weights) if weights else None
            category = _classify_exercise_name(name)
            library[name] = {"category": category, "last_kg": best_weight}

    return library


def _format_library_for_prompt(library: dict[str, dict], category: str) -> str:
    """Return a compact list of exercises for the given category with last weights."""
    lines = []
    for name, info in library.items():
        if info["category"] != category:
            continue
        weight = f" @ {info['last_kg']}kg" if info["last_kg"] else ""
        lines.append(f"  {name}{weight}")
    return "\n".join(lines) if lines else "  (no history yet)"


def build_plan_prompt(
    athlete: Athlete,
    recent_activities: list[Activity],
    recent_gym: list[GymWorkout],
    today_metrics: DailyMetrics | None,
    gym: bool = True,
    exercise_library: dict | None = None,
) -> str:
    ctl = f"{today_metrics.ctl:.1f}" if today_metrics else "unknown"
    atl = f"{today_metrics.atl:.1f}" if today_metrics else "unknown"
    tsb = f"{today_metrics.tsb:.1f}" if today_metrics else "unknown"

    activity_block = "\n".join(_format_activity(a) for a in recent_activities) or "  No recent activities"
    gym_block = "\n".join(_format_gym(g) for g in recent_gym) or "  No recent gym sessions"

    split = athlete.gym_split or "upper_lower"
    today_gym_day = _next_split_day(recent_gym, split)
    split_label = {"upper_lower": "Upper/Lower", "ppl": "Push/Pull/Legs", "arnold": "Arnold Split"}.get(split, split)

    if gym:
        # Tri discipline is constrained by which gym day it is:
        # Upper day  → swim is off-limits (arms/back overlap) → bike or run only
        # Lower day  → bike/run are off-limits (legs overlap) → swim only
        if today_gym_day == "upper":
            allowed_tri = "Bike or Run (NOT swim — upper body needs to recover)"
        elif today_gym_day == "lower":
            allowed_tri = "Swim ONLY (NOT bike or run — legs need to recover)"
        else:
            allowed_tri = "any discipline"

        ex_library = exercise_library or {}
        available = _format_library_for_prompt(ex_library, today_gym_day)

        # Build exact name list to paste verbatim into prompt
        ex_library = exercise_library or {}
        lower_ex = {n: v for n, v in ex_library.items() if v["category"] == today_gym_day}
        ex_lines = "\n".join(
            f'  "{name}" @ {info["last_kg"]}kg' if info["last_kg"] else f'  "{name}"'
            for name, info in lower_ex.items()
        ) or "  (no history yet — ask athlete)"

        gym_section = f"""GYM SPLIT: {split_label} — today is a {today_gym_day.upper()} day
RECOVERY RULE: {allowed_tri}
RECENT GYM (classified):
{gym_block}

ALLOWED EXERCISES FOR TODAY (exact names, exact last weights — use ONLY these, copy names exactly):
{ex_lines}

SET PROTOCOL: 2 working sets to failure per exercise."""
        gym_format = f"""
**Gym — {today_gym_day.capitalize()} Day**
- [exact exercise name from list] — 2 sets to failure @ ~[last weight]kg
- [exact exercise name from list] — 2 sets to failure @ ~[last weight]kg
- [exact exercise name from list] — 2 sets to failure @ ~[last weight]kg
- [exact exercise name from list] — 2 sets to failure @ ~[last weight]kg"""
        gym_rules = """1. Upper day → tri must be bike or run. Lower day → tri must be swim.
2. If TSB < -20, replace tri with "Rest".
3. CRITICAL: Use ONLY exercise names from the ALLOWED EXERCISES list above. Copy them exactly. Any exercise not in that list is forbidden."""
    else:
        allowed_tri = "any discipline — no gym today so no muscle group conflicts"
        gym_section = f"NO GYM TODAY. Cardio only.\nRECENT GYM (for context):\n{gym_block}"
        gym_format = ""
        gym_rules = "1. No gym section — cardio only.\n2. If TSB < -20, prescribe full rest."

    return f"""Ironman coach. Write a short, scannable training plan for today. No explanations, no fluff.

ATHLETE: {athlete.display_name or "Athlete"} | FTP: {athlete.ftp_watts or 200}W | Run threshold: {f"{athlete.threshold_pace_per_km} min/km" if athlete.threshold_pace_per_km else "unknown"}
LOAD: CTL {ctl} · ATL {atl} · TSB {tsb}
{gym_section}
RECENT TRI:
{activity_block}
TODAY: {date.today().strftime("%A %b %d")}

STRICT RULES — never break these:
{gym_rules}

Reply in this exact format — nothing else:

**Status:** one sentence on TSB + effort level

**Tri Session**
[discipline] · [duration] · [single intensity target e.g. "Z2" or "130–150W" or "HR <140"]{gym_format}

**Tomorrow:** one sentence"""


def generate_plan(db: Session, athlete: Athlete, gym: bool = True) -> str:
    today = date.today()
    since = today - timedelta(days=14)

    recent_activities = (
        db.query(Activity)
        .filter(
            Activity.athlete_id == athlete.id,
            Activity.start_time >= since,
        )
        .order_by(Activity.start_time.desc())
        .all()
    )

    recent_gym = (
        db.query(GymWorkout)
        .filter(
            GymWorkout.athlete_id == athlete.id,
            GymWorkout.date >= since,
        )
        .order_by(GymWorkout.date.desc())
        .all()
    )

    all_gym = (
        db.query(GymWorkout)
        .filter_by(athlete_id=athlete.id)
        .order_by(GymWorkout.date.asc())
        .all()
    )

    today_metrics = (
        db.query(DailyMetrics)
        .filter_by(athlete_id=athlete.id, date=today)
        .first()
    )

    exercise_library = _build_exercise_library(all_gym)
    prompt = build_plan_prompt(athlete, recent_activities, recent_gym, today_metrics, gym=gym, exercise_library=exercise_library)

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        system="You are a concise triathlon coach. Write short, scannable plans. No preamble, no explanations, no filler. Just the workout.",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
