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


def _format_gym(g: GymWorkout) -> str:
    ex_names = [e["name"] for e in (g.exercises or [])]
    exercises = ", ".join(ex_names[:5]) or "general strength"
    dur = f"{g.duration_minutes}min" if g.duration_minutes else ""
    return f"  • {g.date.strftime('%a %b %d')} — Gym {dur}: {exercises}"


def build_plan_prompt(
    athlete: Athlete,
    recent_activities: list[Activity],
    recent_gym: list[GymWorkout],
    today_metrics: DailyMetrics | None,
) -> str:
    ctl = f"{today_metrics.ctl:.1f}" if today_metrics else "unknown"
    atl = f"{today_metrics.atl:.1f}" if today_metrics else "unknown"
    tsb = f"{today_metrics.tsb:.1f}" if today_metrics else "unknown"

    activity_block = "\n".join(_format_activity(a) for a in recent_activities) or "  No recent activities"
    gym_block = "\n".join(_format_gym(g) for g in recent_gym) or "  No recent gym sessions"

    return f"""You are an elite Ironman triathlon and strength coach. Your job is to write today's personalized training plan.

ATHLETE PROFILE
- Name: {athlete.display_name or "Athlete"}
- FTP (cycling threshold power): {athlete.ftp_watts or "not set — assume 200W"}
- Running threshold pace: {f"{athlete.threshold_pace_per_km} min/km" if athlete.threshold_pace_per_km else "not set"}

CURRENT TRAINING LOAD (as of {date.today().strftime("%B %d, %Y")})
- CTL {ctl} — 42-day fitness (higher = more base fitness built up)
- ATL {atl} — 7-day fatigue (higher = more tired right now)
- TSB {tsb} — Form score = CTL minus ATL
  - TSB > 5: Fresh and ready to perform
  - TSB -10 to 5: Normal training load
  - TSB -10 to -30: Accumulating fatigue, be careful
  - TSB < -30: Danger zone, risk of overtraining

LAST 14 DAYS — TRIATHLON TRAINING
{activity_block}

LAST 14 DAYS — GYM SESSIONS
{gym_block}

GOALS
- Complete an Ironman triathlon (3.8km swim, 180km bike, 42.2km run)
- Build functional strength and muscle at the gym
- Balance endurance training and strength work without burning out

TODAY'S DATE: {date.today().strftime("%A, %B %d, %Y")}

Write today's training plan. Structure your response with these sections:

## Today's Plan

**Form Assessment** (1-2 sentences on what the TSB and recent history tell you)

**Primary Workout** (the main triathlon session today — be specific: discipline, duration, exact intensity targets like heart rate zone or pace range or watts)

**Strength Session** (gym exercises with sets/reps — choose based on what muscle groups they haven't hit recently, and keep volume appropriate for where they are in the training week)

**Recovery & Nutrition** (1-2 specific tips based on their fatigue level)

**Tomorrow Preview** (one sentence on what to expect tomorrow)

Be specific, not generic. Reference their actual numbers. If TSB is very negative, pull back the intensity even if they want to train hard."""


def generate_plan(db: Session, athlete: Athlete) -> str:
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

    today_metrics = (
        db.query(DailyMetrics)
        .filter_by(athlete_id=athlete.id, date=today)
        .first()
    )

    prompt = build_plan_prompt(athlete, recent_activities, recent_gym, today_metrics)

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        system="You are a precise, data-driven triathlon and strength coach. Write actionable training plans grounded in the athlete's actual numbers. Never be vague.",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
