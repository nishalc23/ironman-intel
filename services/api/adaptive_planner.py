"""
Adaptive weekly plan engine.
Runs every Sunday night — reads real training data, compares vs the static plan,
and has Claude rewrite next week's workouts with real weights and adjusted volume.
"""
import json
import os
from datetime import date, timedelta
from sqlalchemy.orm import Session
import anthropic

from db.models import Athlete, Activity, DailyMetrics, GymWorkout
from db.weekly_plan_model import WeeklyAdaptivePlan

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# ─── Plan constants (mirrors frontend plan.ts) ────────────────────────────────

PLAN_START = date(2026, 6, 1)
RACE_DATE  = date(2026, 12, 6)

PHASE_MAP = {
    range(1, 7):   ("foundation", "Foundation — build aerobic base, learn swim technique"),
    range(7, 15):  ("build",      "Build — increase volume, start intervals, brick workouts"),
    range(15, 22): ("peak",       "Peak — race-specific intensity, peak volume"),
    range(22, 26): ("taper",      "Taper — preserve fitness, reduce fatigue"),
    range(26, 27): ("race_week",  "Race Week — carb load, rest, execute"),
}

WEEKLY_TEMPLATE = {
    "Monday":    {"gym": "upper", "cardio": "run"},
    "Tuesday":   {"gym": None,    "cardio": "swim"},   # swim only
    "Wednesday": {"gym": "lower", "cardio": "bike"},
    "Thursday":  {"gym": None,    "cardio": None},     # rest
    "Friday":    {"gym": "upper", "cardio": "run"},
    "Saturday":  {"gym": "lower", "cardio": "brick"},  # brick from week 7
    "Sunday":    {"gym": None,    "cardio": None},     # rest
}

NUTRITION_BY_DAY = {
    "Monday":    "moderate",
    "Tuesday":   "moderate",
    "Wednesday": "hard",
    "Thursday":  "rest",
    "Friday":    "moderate",
    "Saturday":  "hard",
    "Sunday":    "rest",
}

NUTRITION_TARGETS = {
    "rest":      {"calories": 2600, "carbs": 290, "protein": 150, "fat": 90},
    "moderate":  {"calories": 3000, "carbs": 360, "protein": 155, "fat": 87},
    "hard":      {"calories": 3650, "carbs": 500, "protein": 160, "fat": 90},
    "taper":     {"calories": 2800, "carbs": 360, "protein": 150, "fat": 80},
    "carb_load": {"calories": 3200, "carbs": 620, "protein": 130, "fat": 55},
}


def get_week_number(for_date: date) -> int:
    """Return which week of the 26-week plan a date falls in (1-indexed)."""
    if for_date < PLAN_START:
        return 1
    days = (for_date - PLAN_START).days
    week = days // 7 + 1
    return min(week, 26)


def get_phase(week_num: int) -> tuple[str, str]:
    for r, (phase, desc) in PHASE_MAP.items():
        if week_num in r:
            return phase, desc
    return "taper", "Taper"


def get_week_start(week_num: int) -> date:
    return PLAN_START + timedelta(weeks=week_num - 1)


# ─── Data gathering ───────────────────────────────────────────────────────────

def _get_prior_week_activities(db: Session, athlete_id: int, week_start: date) -> list[Activity]:
    prior_start = week_start - timedelta(weeks=1)
    prior_end   = week_start - timedelta(days=1)
    return (
        db.query(Activity)
        .filter(
            Activity.athlete_id == athlete_id,
            Activity.start_time >= prior_start,
            Activity.start_time <= prior_end,
        )
        .order_by(Activity.start_time)
        .all()
    )


def _get_prior_week_gym(db: Session, athlete_id: int, week_start: date) -> list[GymWorkout]:
    prior_start = week_start - timedelta(weeks=1)
    prior_end   = week_start - timedelta(days=1)
    return (
        db.query(GymWorkout)
        .filter(
            GymWorkout.athlete_id == athlete_id,
            GymWorkout.date >= prior_start,
            GymWorkout.date <= prior_end,
        )
        .order_by(GymWorkout.date)
        .all()
    )


def _get_latest_metrics(db: Session, athlete_id: int) -> DailyMetrics | None:
    return (
        db.query(DailyMetrics)
        .filter(DailyMetrics.athlete_id == athlete_id)
        .order_by(DailyMetrics.date.desc())
        .first()
    )


def _get_exercise_library(db: Session, athlete_id: int) -> dict:
    """Build exercise → last_lbs dict from all Hevy history."""
    all_gym = (
        db.query(GymWorkout)
        .filter(GymWorkout.athlete_id == athlete_id)
        .order_by(GymWorkout.date)
        .all()
    )
    library: dict[str, float | None] = {}
    for workout in all_gym:
        for ex in (workout.exercises or []):
            name = ex.get("name", "")
            sets = ex.get("sets", [])
            lbs_vals = []
            for s in sets:
                if s.get("weight_lbs") is not None:
                    lbs_vals.append(s["weight_lbs"])
                elif s.get("weight_kg") is not None:
                    lbs_vals.append(round(s["weight_kg"] * 2.2046, 1))
            if lbs_vals:
                library[name] = max(lbs_vals)
    return library


def _summarize_prior_week(activities: list[Activity], gym: list[GymWorkout]) -> str:
    """Produce a compact text summary of last week for the Claude prompt."""
    lines = []

    # Swim / Bike / Run
    by_sport: dict[str, list] = {}
    for a in activities:
        by_sport.setdefault(a.discipline, []).append(a)

    for sport, acts in by_sport.items():
        total_min = sum(a.duration_seconds for a in acts) / 60
        total_dist_m = sum(a.distance_meters or 0 for a in acts)
        avg_hr = sum(a.avg_heart_rate or 0 for a in acts) / len(acts) if acts else 0
        if sport == "swimming":
            dist = f"{total_dist_m:.0f}m"
        else:
            dist = f"{total_dist_m / 1609:.1f}mi"
        lines.append(f"  {sport}: {len(acts)} session(s), {total_min:.0f} min total, {dist}"
                     + (f", avg HR {avg_hr:.0f}bpm" if avg_hr else ""))

    if not activities:
        lines.append("  No cardio recorded — all sessions missed or data not synced")

    # Gym
    if gym:
        for g in gym:
            ex_names = [e["name"] for e in (g.exercises or [])][:5]
            lines.append(f"  Gym {g.date}: {', '.join(ex_names)}")
    else:
        lines.append("  No gym sessions recorded this week")

    return "\n".join(lines)


def _what_was_planned(week_num: int, phase: str) -> str:
    """Describe what the static plan called for this week."""
    swim_m = {1: 1200, 2: 1200, 3: 1500, 4: 1500, 5: 1800, 6: 1800,
              7: 2000, 8: 2000, 9: 2000, 10: 2500, 11: 2500, 12: 2500,
              13: 2800, 14: 2800}.get(week_num, 3000)
    run_mi = {1: 15, 2: 15, 3: 18, 4: 18, 5: 20, 6: 20,
              7: 25, 8: 25, 9: 25, 10: 28, 11: 28, 12: 28}.get(week_num, 30)
    bike_hrs = {1: 3, 2: 3, 3: 4, 4: 4, 5: 5, 6: 5,
                7: 4.5, 8: 4.5, 9: 4.5, 10: 5.5, 11: 5.5, 12: 5.5}.get(week_num, 6.5)

    return (f"  Swim: {swim_m}m total (Tuesday standalone)\n"
            f"  Run: ~{run_mi} miles/week (Mon + Fri)\n"
            f"  Bike: ~{bike_hrs} hrs/week (Wed intervals + Sat long ride)\n"
            f"  Gym: 4x/week Upper/Lower split\n"
            f"  Brick: {'Yes — Sat long ride → run' if week_num >= 7 else 'Not yet (starts Week 7)'}")


# ─── Claude prompt ────────────────────────────────────────────────────────────

def _build_adaptive_prompt(
    week_num: int,
    phase: str,
    phase_desc: str,
    week_start: date,
    prior_summary: str,
    planned_summary: str,
    metrics: DailyMetrics | None,
    exercise_library: dict,
    is_recovery_week: bool,
) -> str:

    ctl = f"{metrics.ctl:.1f}" if metrics else "unknown"
    atl = f"{metrics.atl:.1f}" if metrics else "unknown"
    tsb = f"{metrics.tsb:.1f}" if metrics else "unknown"

    ex_lines = "\n".join(
        f'  "{name}": last working set {lbs}lbs → 2 sets to failure'
        for name, lbs in sorted(exercise_library.items())
        if lbs is not None
    ) or "  (no Hevy data yet)"

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    week_dates = [week_start + timedelta(days=i) for i in range(7)]
    date_lines = "\n".join(f"  {d}: {dt.strftime('%b %d')}" for d, dt in zip(days, week_dates))

    recovery_note = "⚡ THIS IS A RECOVERY WEEK — reduce all volumes by 40%. Keep intensity but cut duration." if is_recovery_week else ""

    return f"""You are an expert Ironman 70.3 coach generating next week's adaptive training plan.

═══ ATHLETE ═══
Name: Nishal | Weight: 160 lbs | Goal: Sub-5:00 at IRONMAN 70.3 La Quinta, Dec 6 2026
Current fitness (CTL): {ctl} | Fatigue (ATL): {atl} | Form (TSB): {tsb}
{recovery_note}

═══ NEXT WEEK ═══
Week {week_num} of 26 | Phase: {phase_desc}
Dates:
{date_lines}

═══ WHAT WAS PLANNED LAST WEEK ═══
{planned_summary}

═══ WHAT ACTUALLY HAPPENED LAST WEEK ═══
{prior_summary}

═══ FIXED WEEKLY STRUCTURE (non-negotiable) ═══
Monday:    Upper gym + Run (evening — gym FIRST)
Tuesday:   SWIM ONLY — nothing else, no exceptions
Wednesday: Lower gym + Bike (evening — gym FIRST)
Thursday:  Full rest day
Friday:    Upper gym + Run (evening — gym FIRST)
Saturday:  Lower gym + Long ride → Brick run (gym FIRST, then bike, then run immediately after)
Sunday:    Full rest day

Gym rules:
- ALL gym sets are 2 sets to failure (RIR 0)
- Use the athlete's REAL working weights from Hevy history below
- Triathlon additions (band pull-aparts, dead bug, pallof press, Copenhagen plank, clamshells) are 2×fixed reps, NOT to failure
- Gym always precedes cardio on the same day — never after

═══ ATHLETE'S REAL EXERCISE LIBRARY (from Hevy) ═══
{ex_lines}

═══ ADAPTATION RULES ═══
1. If TSB < -20: reduce cardio volume 15%, keep gym same
2. If TSB < -30: reduce ALL volume 25%, flag "overreach risk"
3. If TSB > +10: add 5-10% volume, athlete is underloaded
4. If swim was missed last week: add a note in Tuesday to make up focus
5. If brick was missed: note it and re-emphasize Saturday importance
6. If gym was missed: use same weights (no progression without session)
7. Recovery week: cut all cardio volume 40%, gym stays 2×failure

═══ RACE FUELING REMINDER (embed in long sessions) ═══
- Gut training active from Week 7: gel every 20-25 min on all long rides/bricks
- Only use: Maurten gels, SIS gels, Clif Bloks, Skratch Labs

═══ OUTPUT FORMAT ═══
Raw JSON only — no markdown fences. Schema:
{{
  "adaptation_notes": "1-2 sentences explaining changes based on last week",
  "volume_adjustment": "normal|reduced_10|reduced_25|increased_5",
  "days": [
    {{
      "dayOfWeek": "Monday",
      "label": "Upper + Run (Evening)",
      "nutritionLoad": "moderate",
      "blocks": [
        {{
          "sport": "gym",
          "name": "Upper Body + Tri Additions",
          "duration": "60-70 min",
          "detail": "Gym before run. 2 sets to failure all compounds.",
          "exercises": [
            {{"name": "Exercise Name", "sets": [{{"reps": "→ failure", "weight": "XXX lbs"}}, {{"reps": "→ failure", "weight": "XXX lbs"}}], "note": "2 sets to failure"}}
          ]
        }},
        {{"sport": "run", "name": "Run — X miles", "duration": "XX min", "detail": "pace/zone instruction"}}
      ]
    }}
  ]
}}

All 7 days required. Thursday + Sunday = rest. Use real Hevy weights. Be specific on intervals and paces.
"""


# ─── Main generation function ─────────────────────────────────────────────────

def generate_adaptive_weekly_plan(db: Session, athlete: Athlete, target_week_num: int | None = None) -> WeeklyAdaptivePlan:
    """
    Generate the adaptive plan for next week (or a specific week).
    Saves to DB and returns the model instance.
    """
    # Determine which week to generate
    today = date.today()
    if target_week_num is None:
        next_week_num = get_week_number(today) + 1
    else:
        next_week_num = target_week_num
    next_week_num = min(max(next_week_num, 1), 26)

    week_start = get_week_start(next_week_num)
    phase, phase_desc = get_phase(next_week_num)
    is_recovery = next_week_num % 4 == 0 and next_week_num < 22

    # Gather data
    prior_activities = _get_prior_week_activities(db, athlete.id, week_start)
    prior_gym        = _get_prior_week_gym(db, athlete.id, week_start)
    metrics          = _get_latest_metrics(db, athlete.id)
    exercise_library = _get_exercise_library(db, athlete.id)

    prior_summary   = _summarize_prior_week(prior_activities, prior_gym)
    planned_summary = _what_was_planned(next_week_num - 1, phase)

    prompt = _build_adaptive_prompt(
        week_num=next_week_num,
        phase=phase,
        phase_desc=phase_desc,
        week_start=week_start,
        prior_summary=prior_summary,
        planned_summary=planned_summary,
        metrics=metrics,
        exercise_library=exercise_library,
        is_recovery_week=is_recovery,
    )

    # Call Claude — use Haiku for speed (smart enough for structured JSON plan)
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    plan_data = json.loads(raw)

    # Determine what was missed for metadata
    completed_sports = {a.discipline for a in prior_activities}
    missed = []
    if "swimming" not in completed_sports:
        missed.append("swim")
    if "running" not in completed_sports:
        missed.append("run")
    if "cycling" not in completed_sports:
        missed.append("bike")
    if not prior_gym:
        missed.append("gym")

    # Upsert into DB
    existing = (
        db.query(WeeklyAdaptivePlan)
        .filter_by(athlete_id=athlete.id, week_start=week_start)
        .first()
    )
    if existing:
        existing.plan_json          = plan_data.get("days", [])
        existing.adaptation_notes   = plan_data.get("adaptation_notes")
        existing.volume_adjustment  = plan_data.get("volume_adjustment", "normal")
        existing.missed_sessions    = missed
        existing.prior_ctl          = str(metrics.ctl) if metrics else None
        existing.prior_atl          = str(metrics.atl) if metrics else None
        existing.prior_tsb          = str(metrics.tsb) if metrics else None
        existing.generated_at       = __import__("datetime").datetime.utcnow()
        db.commit()
        return existing
    else:
        plan = WeeklyAdaptivePlan(
            athlete_id=athlete.id,
            week_start=week_start,
            week_number=next_week_num,
            phase=phase,
            plan_json=plan_data.get("days", []),
            adaptation_notes=plan_data.get("adaptation_notes"),
            volume_adjustment=plan_data.get("volume_adjustment", "normal"),
            missed_sessions=missed,
            prior_ctl=str(metrics.ctl) if metrics else None,
            prior_atl=str(metrics.atl) if metrics else None,
            prior_tsb=str(metrics.tsb) if metrics else None,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan
