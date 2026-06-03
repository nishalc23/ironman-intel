import os
import json
import hashlib
import redis as redis_lib
import anthropic
from datetime import date, timedelta
from sqlalchemy.orm import Session

from db.models import Athlete, Activity, DailyMetrics, GymWorkout

_redis = redis_lib.Redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _format_activity(act: Activity) -> str:
    # Swim in meters, run/bike in miles
    if act.distance_meters:
        if act.discipline == "swimming":
            dist = f"{act.distance_meters:.0f}m"
        else:
            dist = f"{act.distance_meters / 1609.34:.1f}mi"
    else:
        dist = "—"
    hr   = f"avg HR {act.avg_heart_rate}bpm" if act.avg_heart_rate else ""
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
    Walk all gym history and build a dict of exercise_name → {last_lbs, category, typical_position}.
    - last_lbs: heaviest working-set weight in lbs from the most recent session
    - typical_position: median position index across recent sessions (for ordering)
    Skips cardio-only entries (treadmill, swimming, etc.).
    Handles both new format (weight_lbs) and legacy format (weight_kg → converted).
    """
    CARDIO = {"treadmill", "swimming", "stair machine", "bike", "elliptical", "rower"}
    library: dict[str, dict] = {}
    positions: dict[str, list[int]] = {}

    for workout in all_gym:  # oldest first so latest overwrites for weight
        strength_exs = [
            ex for ex in (workout.exercises or [])
            if not any(c in ex["name"].lower() for c in CARDIO)
        ]
        for pos, ex in enumerate(strength_exs):
            name = ex["name"]
            working_sets = [
                s for s in ex.get("sets", [])
                if s.get("set_type") not in ("warmup",) and s.get("reps")
            ]
            if not working_sets:
                continue
            # Support both weight_lbs (new) and weight_kg (legacy Hevy import)
            lbs_values = []
            for s in working_sets:
                if s.get("weight_lbs") is not None:
                    lbs_values.append(s["weight_lbs"])
                elif s.get("weight_kg") is not None:
                    lbs_values.append(round(s["weight_kg"] * 2.2046))
            best_lbs = max(lbs_values) if lbs_values else None
            category = _classify_exercise_name(name)
            library[name] = {"category": category, "last_lbs": best_lbs}
            positions.setdefault(name, []).append(pos)

    # Attach median position so we can sort by typical order
    import statistics
    for name in library:
        pos_list = positions.get(name, [999])
        library[name]["typical_pos"] = statistics.median(pos_list)

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
    discipline: str | None = None,
    split_override: str | None = None,
) -> str:
    ctl = f"{today_metrics.ctl:.1f}" if today_metrics else "unknown"
    atl = f"{today_metrics.atl:.1f}" if today_metrics else "unknown"
    tsb = f"{today_metrics.tsb:.1f}" if today_metrics else "unknown"

    activity_block = "\n".join(_format_activity(a) for a in recent_activities) or "  No recent activities"
    gym_block = "\n".join(_format_gym(g) for g in recent_gym) or "  No recent gym sessions"

    split = athlete.gym_split or "upper_lower"
    today_gym_day = split_override if split_override in ("upper", "lower") else _next_split_day(recent_gym, split)
    split_label = {"upper_lower": "Upper/Lower", "ppl": "Push/Pull/Legs", "arnold": "Arnold Split"}.get(split, split)

    if gym:
        # Constraint rules (based on gym split day):
        #   Upper day → arms/back are worked → Bike or Run ONLY (no swim — shoulders overlap)
        #   Lower day → legs are worked      → Swim or Bike ONLY (no run — legs already taxed)
        ALLOWED_BY_SPLIT = {
            "upper": {"bike", "run"},
            "lower": {"swim", "bike"},
        }
        allowed_set = ALLOWED_BY_SPLIT.get(today_gym_day, {"swim", "bike", "run"})

        if discipline == "brick":
            forced_tri = "Bike → Run (brick)"
            allowed_tri = "Brick — bike immediately followed by run"
        elif discipline and discipline not in ("", "rest"):
            forced_tri = discipline.capitalize()
            allowed_tri = f"{forced_tri} — athlete's choice"
        else:
            # Claude picks best cardio from allowed set based on load, phase, recent history
            forced_tri = None
            allowed_tri = f"{' or '.join(d.capitalize() for d in sorted(allowed_set))} — pick whichever fits phase + recent history best"

        ex_library = exercise_library or {}
        # Filter to today's split, sort by typical workout order
        lower_ex = {
            n: v for n, v in ex_library.items() if v["category"] == today_gym_day
        }
        sorted_ex = sorted(lower_ex.items(), key=lambda x: x[1].get("typical_pos", 999))
        ex_lines = "\n".join(
            f'  "{name}" @ {info["last_lbs"]}lbs' if info.get("last_lbs") else f'  "{name}"'
            for name, info in sorted_ex
        ) or "  (no history yet — ask athlete)"

        gym_section = f"""GYM SPLIT: {split_label} — today is a {today_gym_day.upper()} day
TRI DISCIPLINE: {allowed_tri}"""
        gym_format = f"""
**Gym:** {today_gym_day.capitalize()} day

**Tri Session**
{forced_tri or "[discipline per TRI DISCIPLINE rule]"} · [duration] · [single intensity target]"""
        gym_rules = f"""1. FIXED PAIRINGS (athlete's training structure — never change):
   Upper day → RUN always. No bike, no swim.
   Lower day → BIKE always. No run, no swim.
2. Use miles for run/bike distances, meters for swim.
3. Give a specific distance target, not a vague "go for a run".
4. If TSB < -20, shorten the session 50% — don't skip it."""
    else:
        if discipline and discipline not in ("", "rest"):
            discipline_line = "Bike → Run (brick)" if discipline == "brick" else discipline.capitalize()
            rest_note = "REST DAY FROM GYM — light recovery session only. Keep HR low (Z1-Z2 max), short duration (20-40min). No intensity."
        else:
            discipline_line = "[no cardio — full rest]"
            rest_note = "FULL REST DAY. No gym, no cardio. Prescribe sleep, nutrition, and recovery only."
        gym_section = f"NO GYM TODAY.\n{rest_note}\nTRI DISCIPLINE: {discipline_line}\nRECENT GYM (for context):\n{gym_block}"
        gym_format = f"\n**Recovery Session**\n{discipline_line} · [20-40min] · [Z1-Z2 easy — recovery pace only]" if discipline and discipline not in ("", "rest") else "\n**Full Rest**\nNo training — sleep 8-9h, hydrate, eat well."
        gym_rules = "1. REST DAY = SWIM always. Give a specific meter target (e.g. 1000m, 1500m) broken into sets.\n2. Use meters for swim distances. Keep HR low (Z1-Z2), no intensity."

    days_to_race = (date(2026, 12, 6) - date.today()).days
    weeks_to_race = days_to_race // 7

    # Periodization phase — drives session length targets and weekly discipline balance
    if days_to_race > 168:  # 24+ weeks out
        phase = "Foundation"
        phase_guidance = (
            "Build aerobic base. All 3 disciplines 1-2x/week total — frequency matters more than volume. "
            "Gym 4x/week. Sessions short (30-45min). No bricks yet. "
            "Weekly discipline balance target: swim 1x, bike 1x, run 1x minimum."
        )
    elif days_to_race > 112:  # 16-24 weeks out
        phase = "Build"
        phase_guidance = (
            "Increase tri volume. Hit all 3 disciplines every week. Gym 3x/week. "
            "Sessions building to 60-90min. Introduce occasional brick (bike→run). "
            "Weekly target: swim 2x, bike 2x, run 2x."
        )
    elif days_to_race > 56:  # 8-16 weeks out
        phase = "Race-Specific"
        phase_guidance = (
            "Race simulation. All 3 disciplines multiple times/week. Gym 2x/week, lifts shorter. "
            "Weekly brick required. Sessions approaching race distance (1.9km swim / 90km bike / 21km run). "
            "Weekly target: swim 2-3x, bike 3x, run 3x."
        )
    elif days_to_race > 28:  # 4-8 weeks out
        phase = "Peak"
        phase_guidance = (
            "Peak load then sharpen. All 3 disciplines 2-3x/week. Gym 1-2x/week only. "
            "Race-pace intervals. Long brick weekly. Build toward near-race distances."
        )
    else:  # final 4 weeks — taper
        phase = "Taper"
        phase_guidance = (
            "TAPER — protect fitness, recover. Cut volume 30-50% but keep intensity. "
            "All 3 disciplines short, sharp sessions. Gym max 1x/week. Prioritize sleep."
        )

    # Count this week's sessions per discipline (Mon–today)
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_acts = [a for a in recent_activities if a.start_time.date() >= week_start]
    week_counts = {"swim": 0, "bike": 0, "run": 0}
    for a in week_acts:
        if a.discipline == "swimming":   week_counts["swim"] += 1
        elif a.discipline == "cycling":  week_counts["bike"] += 1
        elif a.discipline == "running":  week_counts["run"] += 1

    missing = [d.upper() for d, n in week_counts.items() if n == 0]
    done    = [f"{d.upper()} {n}x" for d, n in week_counts.items() if n > 0]

    week_summary = (
        f"This week so far: {', '.join(done) if done else 'nothing yet'}\n"
        f"MISSING this week: {', '.join(missing) if missing else 'all 3 disciplines hit ✓'}\n"
        f"→ PRIORITIZE missing disciplines when choosing today's tri session."
    )

    return f"""Ironman 70.3 coach. Write a short, scannable training plan for today. No explanations, no fluff. Use MILES for run/bike, METERS for swim.

RACE: IRONMAN 70.3 La Quinta — Dec 6, 2026 ({days_to_race} days out · {weeks_to_race} weeks)
COURSE: 1,200m swim (Lake Cahuilla) · 56mi bike (flat, fast) · 13.1mi run (2-loop Silver Rock) · 8h30m cutoff

ATHLETE: {athlete.display_name or "Athlete"} | FTP: {athlete.ftp_watts or 200}W | Run threshold: {f"{athlete.threshold_pace_per_km} min/mi" if athlete.threshold_pace_per_km else "unknown"}
LOAD: CTL {ctl} · ATL {atl} · TSB {tsb}

TRAINING PHASE: {phase} ({days_to_race} days out)
{phase_guidance}

WEEKLY DISCIPLINE BALANCE:
{week_summary}

{gym_section}
TODAY: {date.today().strftime("%A %b %d")}

STRICT RULES — never break these:
{gym_rules}

Reply in this exact format — nothing else. Do NOT list any exercises:

**Status:** one sentence on TSB + effort level
{gym_format}

**Tomorrow:** one sentence — what discipline is most urgent next"""


def generate_plan(db: Session, athlete: Athlete, gym: bool = True, discipline: str | None = None, split_override: str | None = None) -> str:
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
    prompt = build_plan_prompt(athlete, recent_activities, recent_gym, today_metrics, gym=gym, exercise_library=exercise_library, discipline=discipline, split_override=split_override)

    # Cache key: athlete + date + split + discipline — same inputs = same plan
    # Invalidated automatically at midnight (TTL until end of day)
    cache_key = f"plan:{athlete.id}:{today}:{split_override or 'auto'}:{discipline or 'auto'}:{gym}"
    cached = _redis.get(cache_key)
    if cached:
        return cached.decode()

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=400,
        system="You are a concise triathlon coach. Write short, scannable plans. No preamble, no explanations, no filler. Just the workout.",
        messages=[{"role": "user", "content": prompt}],
    )

    plan_text = response.content[0].text

    # Cache until midnight so regenerating returns the same plan (only changes after a sync)
    seconds_until_midnight = (
        (date.today() + timedelta(days=1) - date.today()).seconds
        or 86400
    )
    try:
        _redis.setex(cache_key, 86400, plan_text)
    except Exception:
        pass  # Redis unavailable — just return without caching

    return plan_text


# ---------------------------------------------------------------------------
# Weekly training schedule generator
# ---------------------------------------------------------------------------

SUB5_COACHING = """
=== SUB-5:00 IRONMAN 70.3 COACHING KNOWLEDGE ===

RACE DISTANCE: 1.2mi swim · 56mi bike · 13.1mi run
SUB-5 TARGET SPLITS:
  Swim:  30-32 min  (1:34-1:41/100m pace)
  T1+T2: 3-4 min
  Bike:  2:18-2:24  (23-24 mph average, ~75-80% FTP)
  Run:   2:04-2:10  (9:27-9:54/mi — this is POST-BIKE pace, legs are already tired)
  Total: 4:58-5:08

ATHLETE'S TRAINING CYCLE (fixed rotation, no exceptions):
  Day A → Upper gym + Run
  Day B → Lower gym + Bike
  Day C → Rest (no gym) + Swim
  Repeat A → B → C → A → B → C...

FOUNDATION PHASE TRAINING TARGETS (24+ weeks out):
  Goal: build aerobic base, establish all 3 disciplines, no racing yet.

  RUN (targeting 9:30/mi race pace by race day):
  - Easy run:  3-5mi @ 10:30-11:00/mi · HR 130-145 · conversational
  - Tempo run: 2-3mi @ 8:45-9:15/mi · HR 158-168 · comfortably hard (once every 2 Upper cycles)
  - Long run:  6-8mi @ 10:30/mi · HR 130-145 (assign on 3rd Upper day of week if it occurs)
  → DO NOT run faster than 9:15/mi in easy runs — you burn out aerobic base
  → 182 bpm runs are RACE EFFORT, not training — save that for race day

  BIKE (targeting 23mph average by race day):
  - Easy spin:    12-15mi @ RPE 5/10 · easy gear · HR 120-135
  - Moderate:     15-20mi @ RPE 6-7/10 · HR 135-150
  - Long ride:    20-30mi @ RPE 6/10 · steady aerobic (assign once/week if 2+ Lower days)
  → Build from 12mi now to 40mi by race-specific phase

  SWIM (targeting 1:35/100m by race day; currently ~1:50-2:00/100m):
  - Technique:  800-1200m · 50m repeats w/ 30s rest · focus on form NOT speed
  - Endurance:  1200-1600m · 100m repeats w/ 30s rest · build aerobic engine
  - Threshold:  (introduce week 8+) 200m repeats descending pace
  → RIGHT NOW: form first. Once stroke is efficient, speed comes fast.
  → Build weekly swim volume from 1000m → 3000m by peak phase

WEEKLY VOLUME TARGETS (Foundation):
  Run:  8-12 miles/week total
  Bike: 25-40 miles/week total
  Swim: 1500-2500m/week total

KEY COACHING RULES:
1. Easy days MUST be easy (HR <145). If it's not easy, it's not an easy day.
2. The run after Upper gym is always shorter/easier than a standalone run.
3. Swim on rest days = no leg fatigue = can push pace slightly more.
4. Never do tempo run AND long run in same A-B-C cycle.
5. Alternate: easy run → tempo run → easy run → easy run → tempo run...
"""


def generate_weekly_plan(db: Session, athlete: Athlete) -> str:
    """Generate a structured 7-day training schedule for the coming week."""
    today = date.today()
    # Cache for the whole week (Mon–Sun)
    days_since_monday = today.weekday()
    week_of = today - timedelta(days=days_since_monday)
    cache_key = f"weekly:{athlete.id}:{week_of}"

    cached = _redis.get(cache_key)
    if cached:
        return cached.decode()

    # Get recent gym history to determine where in the cycle we are
    recent_gym = (
        db.query(GymWorkout)
        .filter(
            GymWorkout.athlete_id == athlete.id,
            GymWorkout.date >= today - timedelta(days=14),
        )
        .order_by(GymWorkout.date.desc())
        .all()
    )

    recent_activities = (
        db.query(Activity)
        .filter(
            Activity.athlete_id == athlete.id,
            Activity.start_time >= today - timedelta(days=7),
        )
        .order_by(Activity.start_time.desc())
        .all()
    )

    today_metrics = (
        db.query(DailyMetrics)
        .filter_by(athlete_id=athlete.id, date=today)
        .first()
    )

    days_to_race = (date(2026, 12, 6) - today).days
    weeks_to_race = days_to_race // 7
    ctl = f"{today_metrics.ctl:.1f}" if today_metrics else "unknown"
    atl = f"{today_metrics.atl:.1f}" if today_metrics else "unknown"
    tsb = f"{today_metrics.tsb:.1f}" if today_metrics else "unknown"

    # Determine next split in cycle from last gym session
    last_gym_type = "unknown"
    for g in recent_gym:
        t = _classify_gym_day(g)
        if t in ("upper", "lower"):
            last_gym_type = t
            break

    if last_gym_type == "upper":
        next_split = "lower"
    elif last_gym_type == "lower":
        next_split = "rest"
    else:
        next_split = "upper"

    recent_acts_fmt = "\n".join(_format_activity(a) for a in recent_activities) or "  None"

    prompt = f"""{SUB5_COACHING}

ATHLETE: {athlete.display_name or "Athlete"} | CTL: {ctl} | ATL: {atl} | TSB: {tsb}
RACE: IRONMAN 70.3 La Quinta — Dec 6, 2026 ({weeks_to_race} weeks out)
TODAY: {today.strftime("%A %b %d, %Y")}
WEEK OF: {week_of.strftime("%b %d")}
NEXT SPLIT IN CYCLE: {next_split.upper()} (continue the A→B→C rotation from here)

RECENT ACTIVITY:
{recent_acts_fmt}

Generate a 7-day training schedule starting from TODAY ({today.strftime("%A")}).
Follow the A→B→C rotation strictly. Start at {next_split.upper()} for today.

RESPOND IN EXACTLY THIS FORMAT — one line per day, pipe-separated, 7 lines total:
DAY|SPLIT|TITLE|WORKOUT|PURPOSE

Rules:
- DAY: Mon / Tue / Wed / Thu / Fri / Sat / Sun
- SPLIT: upper / lower / rest
- TITLE: "Upper + Run" / "Lower + Bike" / "Rest + Swim"
- WORKOUT: specific (e.g. "4mi easy @ 10:30/mi · HR 130-145" or "1200m · 20×50m · 30s rest")
- PURPOSE: 3-5 words (e.g. "Aerobic base build")
- Use miles for run/bike, meters for swim
- Vary runs: easy → tempo → easy pattern
- No fluff. No headers. Just 7 pipe-separated lines."""

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        system="You are a precise triathlon coach. Output exactly 7 pipe-separated lines, nothing else.",
        messages=[{"role": "user", "content": prompt}],
    )

    plan_text = response.content[0].text.strip()

    # Cache until end of week (Sunday midnight)
    days_until_sunday = 6 - today.weekday()
    ttl = (days_until_sunday + 1) * 86400
    try:
        _redis.setex(cache_key, ttl, plan_text)
    except Exception:
        pass

    return plan_text
