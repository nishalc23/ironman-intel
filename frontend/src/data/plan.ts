// ─── 26-Week Ironman 70.3 La Quinta Plan ────────────────────────────────────
// Race: December 6, 2026  |  Start: June 1, 2026  |  Goal: Sub 5:00:00

// Use local-time dates (avoid UTC parsing shift)
export const RACE_DATE = new Date(2026, 11, 6);   // Dec 6 2026
export const PLAN_START = new Date(2026, 5, 1);   // Jun 1 2026 (month is 0-indexed)

export type Sport = "swim" | "bike" | "run" | "gym" | "rest" | "brick";
export type Phase = "foundation" | "build" | "peak" | "taper" | "race_week";
export type GymDay = "upper" | "lower";
export type NutritionLoad = "rest" | "moderate" | "hard" | "taper" | "carb_load" | "race_morning";

export interface Set {
  reps?: number | string;
  weight?: string;
  duration?: string;
}

export interface Exercise {
  name: string;
  sets: Set[];
  note?: string;
}

export interface WorkoutBlock {
  sport: Sport;
  name: string;
  duration: string;
  detail: string;
  exercises?: Exercise[];
  gutTraining?: boolean;
}

export interface DayPlan {
  dayOfWeek: "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday";
  label: string;
  nutritionLoad: NutritionLoad;
  blocks: WorkoutBlock[];
}

export interface Week {
  weekNumber: number;
  startDate: Date;
  phase: Phase;
  phaseLabel: string;
  focus: string;
  isRecovery: boolean;
  days: DayPlan[];
}

// ─── Exercises by phase ──────────────────────────────────────────────────────

// All working sets are 2 sets to failure (RIR 0) — load based on what breaks form first

const UPPER_BASE: Exercise[] = [
  { name: "Incline Bench Press (Smith)", sets: [{ reps: "→ failure", weight: "135 lbs" }, { reps: "→ failure", weight: "135 lbs" }], note: "2 sets to failure" },
  { name: "Pull Ups", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure" },
  { name: "Seated Row Machine", sets: [{ reps: "→ failure", weight: "115 lbs" }, { reps: "→ failure", weight: "115 lbs" }], note: "2 sets to failure" },
  { name: "Lat Pulldown Cable", sets: [{ reps: "→ failure", weight: "160 lbs" }, { reps: "→ failure", weight: "160 lbs" }], note: "2 sets to failure" },
  { name: "Shoulder Press Machine", sets: [{ reps: "→ failure", weight: "180 lbs" }, { reps: "→ failure", weight: "180 lbs" }], note: "2 sets to failure" },
  { name: "Rear Delt Reverse Fly", sets: [{ reps: "→ failure", weight: "180 lbs" }, { reps: "→ failure", weight: "180 lbs" }], note: "2 sets to failure" },
  { name: "Chest Fly Machine", sets: [{ reps: "→ failure", weight: "160 lbs" }, { reps: "→ failure", weight: "160 lbs" }], note: "2 sets to failure" },
  { name: "Chest Dips", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure" },
  { name: "Preacher Curl Machine", sets: [{ reps: "→ failure", weight: "130 lbs/arm" }, { reps: "→ failure", weight: "130 lbs/arm" }], note: "2 sets to failure" },
  { name: "Triceps Pushdown", sets: [{ reps: "→ failure", weight: "65 lbs" }, { reps: "→ failure", weight: "65 lbs" }], note: "2 sets to failure" },
  { name: "Overhead Triceps Extension Cable", sets: [{ reps: "→ failure", weight: "57.5 lbs" }, { reps: "→ failure", weight: "57.5 lbs" }], note: "2 sets to failure" },
  { name: "Lateral Raise Cable", sets: [{ reps: "→ failure", weight: "40 lbs" }, { reps: "→ failure", weight: "30 lbs" }], note: "2 sets to failure — dropset on set 2" },
  { name: "Hammer Curl Dumbbell", sets: [{ reps: "→ failure", weight: "80 lbs" }, { reps: "→ failure", weight: "80 lbs" }], note: "2 sets to failure" },
];

const UPPER_TRI_ADDITIONS: Exercise[] = [
  { name: "Band Pull-Aparts", sets: [{ reps: 20 }, { reps: 20 }], note: "Swim shoulder health — controlled, not to failure" },
  { name: "Dead Bug", sets: [{ reps: "10 each side" }, { reps: "10 each side" }], note: "Core stability — controlled" },
  { name: "Pallof Press", sets: [{ reps: "12 each side" }, { reps: "12 each side" }], note: "Anti-rotation — controlled" },
];

const LOWER_BASE: Exercise[] = [
  { name: "Lying Leg Curl Machine", sets: [{ reps: "→ failure", weight: "110 lbs" }, { reps: "→ failure", weight: "110 lbs" }], note: "2 sets to failure" },
  { name: "Leg Extension Machine", sets: [{ reps: "→ failure", weight: "190 lbs" }, { reps: "→ failure", weight: "190 lbs" }], note: "2 sets to failure" },
  { name: "Crunch Machine", sets: [{ reps: "→ failure", weight: "90 lbs" }, { reps: "→ failure", weight: "90 lbs" }], note: "2 sets to failure" },
  { name: "Hip Adduction Machine", sets: [{ reps: "→ failure", weight: "260 lbs" }, { reps: "→ failure", weight: "260 lbs" }], note: "2 sets to failure" },
  { name: "Back Extension (Hyperextension)", sets: [{ reps: "→ failure", weight: "90 lbs" }, { reps: "→ failure", weight: "90 lbs" }], note: "2 sets to failure" },
  { name: "Side Bend Dumbbell", sets: [{ reps: "→ failure", weight: "25 lbs/side" }, { reps: "→ failure", weight: "25 lbs/side" }], note: "2 sets to failure" },
  { name: "Leg Raise (Parallel Bars)", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure" },
];

const LOWER_TRI_ADDITIONS: Exercise[] = [
  { name: "Hip Thrust", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure — add weight when easy. Glute/bike power." },
  { name: "Romanian Deadlift", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure — moderate weight, posterior chain/run power" },
  { name: "Copenhagen Plank", sets: [{ duration: "→ failure/side" }, { duration: "→ failure/side" }], note: "Injury prevention — hold until form breaks" },
  { name: "Clamshells with Band", sets: [{ reps: "→ failure/side" }, { reps: "→ failure/side" }], note: "Hip health — controlled burn" },
];

const LOWER_PHASE3: Exercise[] = [
  { name: "Hip Thrust", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure" },
  { name: "Romanian Deadlift", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure" },
  { name: "Back Extension (Hyperextension)", sets: [{ reps: "→ failure", weight: "90 lbs" }, { reps: "→ failure", weight: "90 lbs" }], note: "2 sets to failure" },
  { name: "Crunch Machine", sets: [{ reps: "→ failure", weight: "90 lbs" }, { reps: "→ failure", weight: "90 lbs" }], note: "2 sets to failure" },
  { name: "Copenhagen Plank", sets: [{ duration: "→ failure/side" }, { duration: "→ failure/side" }] },
  { name: "Clamshells with Band", sets: [{ reps: "→ failure/side" }, { reps: "→ failure/side" }] },
  { name: "Leg Raise (Parallel Bars)", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure" },
  { name: "Dead Bug", sets: [{ reps: "10 each side" }, { reps: "10 each side" }], note: "Controlled — not to failure" },
];

const TAPER_UPPER: Exercise[] = [
  { name: "Pull Ups", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "2 sets to failure — light, stay fresh" },
  { name: "Band Pull-Aparts", sets: [{ reps: 20 }, { reps: 20 }], note: "Shoulder health — controlled" },
  { name: "Dead Bug", sets: [{ reps: "10 each side" }, { reps: "10 each side" }] },
  { name: "Pallof Press", sets: [{ reps: "12 each side" }, { reps: "12 each side" }] },
  { name: "Copenhagen Plank", sets: [{ duration: "→ failure/side" }, { duration: "→ failure/side" }] },
];

const TAPER_LOWER: Exercise[] = [
  { name: "Hip Thrust (bodyweight)", sets: [{ reps: "→ failure" }, { reps: "→ failure" }], note: "Bodyweight only in taper" },
  { name: "Clamshells with Band", sets: [{ reps: "→ failure/side" }, { reps: "→ failure/side" }] },
  { name: "Copenhagen Plank", sets: [{ duration: "→ failure/side" }, { duration: "→ failure/side" }] },
  { name: "Dead Bug", sets: [{ reps: "10 each side" }, { reps: "10 each side" }] },
  { name: "Leg Raise (Parallel Bars)", sets: [{ reps: "→ failure" }, { reps: "→ failure" }] },
];

// ─── Workout block builders ───────────────────────────────────────────────────

function upperGym(phase: Phase, label = "Upper Body + Tri Additions"): WorkoutBlock {
  const exPhase = phase === "taper" || phase === "race_week" ? TAPER_UPPER : [...UPPER_BASE, ...UPPER_TRI_ADDITIONS];
  return {
    sport: "gym",
    name: label,
    duration: phase === "taper" || phase === "race_week" ? "30 min" : "60–70 min",
    detail: "Gym first — then run after",
    exercises: exPhase,
  };
}

function lowerGym(phase: Phase, label = "Lower Body + Tri Additions"): WorkoutBlock {
  let exercises: Exercise[];
  let duration: string;
  if (phase === "taper" || phase === "race_week") {
    exercises = TAPER_LOWER;
    duration = "25 min";
  } else if (phase === "peak") {
    exercises = LOWER_PHASE3;
    duration = "50 min";
  } else {
    exercises = [...LOWER_BASE, ...LOWER_TRI_ADDITIONS];
    duration = "60–70 min";
  }
  return {
    sport: "gym",
    name: label,
    duration,
    detail: "Gym first — then bike after",
    exercises,
  };
}

function swimBlock(meters: number, detail: string, gutTraining = false): WorkoutBlock {
  return {
    sport: "swim",
    name: `Swim — ${meters}m`,
    duration: `${Math.round(meters / 35)} min`,
    detail,
    gutTraining,
  };
}

function bikeBlock(hours: number, detail: string, gutTraining = false): WorkoutBlock {
  return {
    sport: "bike",
    name: `Bike — ${hours < 1 ? `${hours * 60} min` : `${hours} hr${hours > 1 ? "s" : ""}`}`,
    duration: `${hours < 1 ? `${hours * 60} min` : `${hours} hrs`}`,
    detail,
    gutTraining,
  };
}

function runBlock(miles: number, detail: string): WorkoutBlock {
  return {
    sport: "run",
    name: `Run — ${miles} miles`,
    duration: `${Math.round(miles * 9.5)} min`,
    detail,
  };
}

function brickBlock(bikeHours: number, runMins: number, detail: string): WorkoutBlock {
  return {
    sport: "brick",
    name: `Brick — ${bikeHours} hr Bike → ${runMins} min Run`,
    duration: `${bikeHours} hrs + ${runMins} min`,
    detail,
    gutTraining: true,
  };
}

function restBlock(note = "Full rest — hydrate, sleep 8+ hrs"): WorkoutBlock {
  return { sport: "rest", name: "Rest Day", duration: "—", detail: note };
}

// ─── Day builders ─────────────────────────────────────────────────────────────

function monday(phase: Phase, wk: number): DayPlan {
  const runMiles = {
    foundation: wk <= 2 ? 6 : wk <= 4 ? 7 : 8,
    build: wk <= 9 ? 8 : wk <= 12 ? 9 : 10,
    peak: wk <= 17 ? 10 : wk <= 19 ? 11 : 10,
    taper: 6,
    race_week: 3,
  }[phase] ?? 8;

  const runDetail = {
    foundation: "Easy Zone 2 pace (9:30–10:00/mile) — aerobic base building",
    build: wk >= 7 ? "Moderate-easy run (9:00–9:30/mile) — building aerobic capacity" : "Easy Zone 2 (9:30/mile)",
    peak: "Long-ish run (9:00–9:30/mile easy) — keep HR controlled",
    taper: "Easy shakeout (9:30/mile) — legs loose and fresh",
    race_week: "Very easy 30 min (9:30–10:00/mile) + 4 race-pace strides at end",
  }[phase] ?? "Easy Zone 2";

  return {
    dayOfWeek: "Monday",
    label: "Upper + Run (Evening)",
    nutritionLoad: phase === "taper" ? "taper" : phase === "race_week" ? "moderate" : "moderate",
    blocks: [
      upperGym(phase),
      runBlock(runMiles, runDetail),
    ],
  };
}

function tuesday(phase: Phase, wk: number): DayPlan {
  let meters: number;
  let detail: string;

  if (phase === "foundation") {
    meters = wk <= 2 ? 1200 : wk <= 4 ? 1500 : 1800;
    detail = wk <= 2
      ? "Pure technique drills: catch-up drill, fingertip drag, bilateral breathing, 6-kick drill. Short sets with long rest. No pace pressure."
      : wk <= 4
      ? "Drills + 4×200m continuous at easy effort. Focus on catch and pull."
      : "100m interval sets at moderate effort. Introduce flip turns. Build continuous blocks.";
  } else if (phase === "build") {
    meters = wk <= 9 ? 2000 : wk <= 12 ? 2500 : 2800;
    detail = wk <= 9
      ? "Threshold work: 5×400m at race pace (1:52/100m) with 45 sec rest. Build race confidence."
      : wk <= 12
      ? "Sustained efforts: 3×600m, then 2×800m at race pace. Minimal rest."
      : "Race-pace confidence: 4×500m at target pace. Practice sighting every 10 strokes.";
  } else if (phase === "peak") {
    meters = wk <= 17 ? 3000 : wk <= 19 ? 3500 : 3000;
    detail = wk <= 19
      ? "Race simulation: 1×1900m straight at target race pace (1:52/100m). Wetsuit practice mandatory."
      : "Taper down: 3×600m at race pace. Stay sharp, don't overcook.";
  } else if (phase === "taper") {
    meters = 2000;
    detail = "Maintain feel — 4×400m at race pace. Keep technique crisp. No heroics.";
  } else {
    meters = 1500;
    detail = "Easy technique session — drills only. Save legs for race day.";
  }

  return {
    dayOfWeek: "Tuesday",
    label: "SWIM ONLY — Nothing else today (Evening)",
    nutritionLoad: phase === "race_week" ? "carb_load" : "moderate",
    blocks: [swimBlock(meters, detail)],
  };
}

function wednesday(phase: Phase, wk: number): DayPlan {
  let bikeHours: number;
  let bikeDetail: string;

  if (phase === "foundation") {
    bikeHours = 0.625;
    bikeDetail = "Easy Zone 2 spin on stationary bike (RPE 4–5/10). Hold 85–90 rpm cadence. No intervals — pure aerobic base.";
  } else if (phase === "build") {
    bikeHours = wk <= 9 ? 1.25 : 1.5;
    bikeDetail = "Sweet Spot Intervals: 15 min easy warmup → 3×15 min hard sustained effort (RPE 7–8, short sentences only) → 3 min easy between → 10 min cooldown. Practice nutrition: 1 gel at min 20.";
  } else if (phase === "peak") {
    bikeHours = 1.5;
    bikeDetail = "Race-pace intervals: 15 min warmup → 5×8 min at 19 mph equivalent effort → 4 min easy spin between → 15 min cooldown. GPS watch: target 19 mph, cap at 19.5 mph.";
  } else if (phase === "taper") {
    bikeHours = 0.75;
    bikeDetail = "Easy spin 45 min — flush the legs. Keep cadence high, resistance low.";
  } else {
    bikeHours = 0.75;
    bikeDetail = "Easy 45 min spin — carb-loaded legs. Stay loose for race Saturday.";
  }

  return {
    dayOfWeek: "Wednesday",
    label: "Lower + Bike (Evening)",
    nutritionLoad: phase === "race_week" ? "carb_load" : phase === "taper" ? "taper" : phase === "foundation" ? "moderate" : "hard",
    blocks: [
      lowerGym(phase),
      bikeBlock(bikeHours, bikeDetail, phase !== "foundation"),
    ],
  };
}

function thursday(_phase: Phase): DayPlan {
  return {
    dayOfWeek: "Thursday",
    label: "Rest Day",
    nutritionLoad: "rest",
    blocks: [restBlock("Full rest. Prioritize sleep (8+ hrs). Hydrate — 100–120 oz water. Light walk OK.")],
  };
}

function friday(phase: Phase, wk: number): DayPlan {
  let runDetail: string;
  let runMiles: number;

  if (phase === "foundation") {
    runMiles = wk <= 2 ? 6 : wk <= 4 ? 7 : 8;
    runDetail = "Easy Zone 2 (9:30–10:00/mile). Mirror Monday's effort. Keep heart rate controlled.";
  } else if (phase === "build") {
    runMiles = wk <= 9 ? 5 : wk <= 12 ? 5 : 6;
    runDetail = "Tempo run: 1 mi warmup → 3–5 mi at 8:15–8:30/mile (RPE 7) → 1 mi cooldown. This is your quality run of the week.";
  } else if (phase === "peak") {
    runMiles = 8;
    runDetail = "Track intervals: 1 mi warmup → 8×800m at 7:50/mile pace (90 sec rest) → 1 mi cooldown. Hard session — caffeine 45 min before OK.";
  } else if (phase === "taper") {
    runMiles = 5;
    runDetail = "Easy run — 9:30/mile. No tempo. Legs should feel fresh.";
  } else {
    runMiles = 2;
    runDetail = "15 min very easy + 4 race-pace strides (10 sec each). Done. Do not overdo it.";
  }

  return {
    dayOfWeek: "Friday",
    label: "Upper + Run (Evening)",
    nutritionLoad: phase === "taper" ? "taper" : "moderate",
    blocks: [
      upperGym(phase),
      runBlock(runMiles, runDetail),
    ],
  };
}

function saturday(phase: Phase, wk: number, hasBrick: boolean): DayPlan {
  if (phase === "race_week") {
    return {
      dayOfWeek: "Saturday",
      label: "Race Prep Day",
      nutritionLoad: "moderate",
      blocks: [
        {
          sport: "swim",
          name: "10 min Easy Swim",
          duration: "10 min",
          detail: "Open water at race venue — easy loosen-up only. Practice sighting. Get comfortable.",
        },
        restBlock("Transition check, rack bike, athlete briefing. Pasta dinner. In bed by 9 PM."),
      ],
    };
  }

  let bikeHours: number;
  let bikeDetail: string;

  if (phase === "foundation") {
    bikeHours = wk <= 2 ? 1.5 : wk <= 4 ? 2 : 2.5;
    bikeDetail = "Long easy Zone 2 ride. Stationary bike OK — increase resistance to simulate outdoor. Hold 85–90 rpm. Drink every 15 min.";
  } else if (phase === "build") {
    bikeHours = wk <= 9 ? 3 : wk <= 12 ? 3.5 : 4;
    bikeDetail = `Long ride Zone 2. Every 20–25 min: 1 gel + fluid. This is gut training — no skipping nutrition. ${hasBrick ? "BRICK: immediately run after — do not change shoes, just go." : ""}`;
  } else if (phase === "peak") {
    const isSimulation = wk >= 20;
    bikeHours = wk <= 17 ? 4.5 : wk <= 19 ? 5 : 4;
    bikeDetail = isSimulation
      ? "Race simulation: 56 miles at 19 mph target. GPS watch — do not exceed 19.5 mph. Full race nutrition protocol active."
      : `Long race-pace ride. Every 20 min: gel + fluid. ${hasBrick ? "BRICK: immediately run after at 9:00/mile." : ""}`;
  } else {
    bikeHours = 2.5;
    bikeDetail = "Easy long ride — maintain feel. 80% of peak volume. Some race-pace efforts OK but nothing grinding.";
  }

  const brickRunMins =
    phase === "build" ? (wk <= 9 ? 20 : wk <= 12 ? 22 : 25) :
    phase === "peak" ? (wk <= 17 ? 25 : 30) :
    20;

  const brickRunDetail = `Run at race target pace (9:00–9:15/mile) immediately off the bike. ${
    phase === "peak" ? "Gut training: gel at minute 5." : "Practice the T2 feeling — legs will be heavy first 5 min, push through."
  }`;

  return {
    dayOfWeek: "Saturday",
    label: hasBrick ? "Lower + Long Ride → Brick Run (Evening)" : "Lower + Long Ride (Evening)",
    nutritionLoad: "hard",
    blocks: hasBrick
      ? [lowerGym(phase), brickBlock(bikeHours, brickRunMins, brickRunDetail)]
      : [lowerGym(phase), bikeBlock(bikeHours, bikeDetail, false)],
  };
}

function sunday(phase: Phase): DayPlan {
  return {
    dayOfWeek: "Sunday",
    label: "Rest Day",
    nutritionLoad: phase === "taper" ? "taper" : "rest",
    blocks: [restBlock("Full rest. Review next week's plan. Reflect on this week's training.")],
  };
}

// ─── Phase boundaries ─────────────────────────────────────────────────────────

function getPhase(wk: number): { phase: Phase; label: string; focus: string } {
  if (wk <= 6)  return { phase: "foundation", label: "Phase 1 — Foundation",  focus: "Build aerobic base, learn swim technique, keep gym strong" };
  if (wk <= 14) return { phase: "build",      label: "Phase 2 — Build",       focus: "Increase volume, start intervals, begin brick workouts" };
  if (wk <= 21) return { phase: "peak",       label: "Phase 3 — Peak",        focus: "Race-specific intensity, peak volume, full gut training" };
  if (wk <= 25) return { phase: "taper",      label: "Phase 4 — Taper",       focus: "Preserve fitness, reduce fatigue, execute race week" };
  return           { phase: "race_week",   label: "Race Week",            focus: "Carb load, race prep, rest — execute perfectly" };
}

// ─── Generate all 26 weeks ────────────────────────────────────────────────────

export function generatePlan(): Week[] {
  const weeks: Week[] = [];

  for (let wk = 1; wk <= 26; wk++) {
    const { phase, label, focus } = getPhase(wk);
    const hasBrick = wk >= 7;
    const isRecovery = wk % 4 === 0 && wk < 22;

    const startDate = new Date(PLAN_START);
    startDate.setDate(PLAN_START.getDate() + (wk - 1) * 7);

    weeks.push({
      weekNumber: wk,
      startDate,
      phase,
      phaseLabel: label,
      focus: isRecovery ? focus + " — RECOVERY WEEK (−40% volume)" : focus,
      isRecovery,
      days: [
        monday(phase, wk),
        tuesday(phase, wk),
        wednesday(phase, wk),
        thursday(phase),
        friday(phase, wk),
        saturday(phase, wk, hasBrick),
        sunday(phase),
      ],
    });
  }

  return weeks;
}

export const PLAN: Week[] = generatePlan();

// ─── Race week override (Dec 1–6) ─────────────────────────────────────────────

export const RACE_WEEK: DayPlan[] = [
  {
    dayOfWeek: "Monday",
    label: "Upper (Light) + Easy Run — Normal eating, begin carb increase",
    nutritionLoad: "moderate",
    blocks: [
      { ...upperGym("race_week", "Upper — Light"), duration: "30 min" },
      runBlock(3, "Easy 30 min — 9:30/mile. No tempo. Just move the legs."),
    ],
  },
  {
    dayOfWeek: "Tuesday",
    label: "SWIM ONLY — Carb Load Day 1",
    nutritionLoad: "carb_load",
    blocks: [swimBlock(1500, "Easy technique session — drills, sighting practice, nothing hard.")],
  },
  {
    dayOfWeek: "Wednesday",
    label: "Lower (Light) + Easy Bike Spin — Carb Load Day 2",
    nutritionLoad: "carb_load",
    blocks: [
      { ...lowerGym("race_week"), duration: "25 min" },
      bikeBlock(0.75, "Easy 45 min spin — flush the legs. High cadence, low resistance."),
    ],
  },
  {
    dayOfWeek: "Thursday",
    label: "REST — 20 min walk only — Carb Load Day 3",
    nutritionLoad: "carb_load",
    blocks: [restBlock("20 min easy walk only. Cut ALL fiber and fat today. Carbs only. Sleep 9 hrs.")],
  },
  {
    dayOfWeek: "Friday",
    label: "15 min Easy Run + Strides — Light meals, hydrate",
    nutritionLoad: "moderate",
    blocks: [
      runBlock(2, "15 min easy jog + 4×10 sec strides at race pace. Done. Nothing more."),
    ],
  },
  {
    dayOfWeek: "Saturday",
    label: "Race Prep — Transition check, rack bike, easy swim",
    nutritionLoad: "moderate",
    blocks: [
      swimBlock(400, "10 min easy open water loosen-up at race venue. Just feel the water."),
      restBlock("Rack bike in transition. Check gear. Pasta dinner. Bed by 9 PM. Do not train."),
    ],
  },
];

// ─── Nutrition targets ────────────────────────────────────────────────────────

export const NUTRITION: Record<NutritionLoad, { calories: number; carbs: number; protein: number; fat: number; label: string }> = {
  rest:         { calories: 2600, carbs: 290,  protein: 150, fat: 90, label: "Rest Day" },
  moderate:     { calories: 3000, carbs: 360,  protein: 155, fat: 87, label: "Moderate Training" },
  hard:         { calories: 3650, carbs: 500,  protein: 160, fat: 90, label: "Hard / Long Training" },
  taper:        { calories: 2800, carbs: 360,  protein: 150, fat: 80, label: "Taper" },
  carb_load:    { calories: 3200, carbs: 620,  protein: 130, fat: 55, label: "Carb Load" },
  race_morning: { calories: 750,  carbs: 150,  protein: 20,  fat: 15, label: "Race Morning" },
};

// ─── Supplements ──────────────────────────────────────────────────────────────

export const SUPPLEMENTS = [
  { name: "Creatine Monohydrate", dose: "3–5g post-workout", timing: "All phases", note: "Maintain muscle + power during endurance training" },
  { name: "Vitamin D3", dose: "2,000–4,000 IU", timing: "All phases — with fat meal", note: "Recovery, immune function" },
  { name: "Omega-3 Fish Oil", dose: "2–3g EPA+DHA", timing: "All phases — with meals", note: "Reduce inflammation" },
  { name: "Magnesium Glycinate", dose: "300–400mg", timing: "All phases — before bed", note: "Sleep quality + cramp prevention" },
  { name: "Caffeine", dose: "100–200mg", timing: "Phase 2–4 — before hard sessions only", note: "Do not use daily — preserve sensitivity for race day" },
  { name: "Beta-Alanine", dose: "3.2–6.4g/day divided", timing: "Phase 2–4", note: "Tingling is normal — reduces fatigue in hard efforts" },
  { name: "Electrolyte Tabs", dose: "1 tab/hour", timing: "All sessions over 90 min", note: "Never pair plain water with long sessions" },
];

// ─── 10 mistakes ──────────────────────────────────────────────────────────────

export const MISTAKES = [
  { num: 1, title: "Fueling too late on bike", fix: "Set a 20-min timer. Start at minute 15 — not when hungry, not when thirsty." },
  { num: 2, title: "New food on race day", fix: "Only use products you've practiced 10+ times in training. Nothing new." },
  { num: 3, title: "Going too hard on the bike", fix: "GPS/HR monitor — hold 19 mph strictly. Exceeding 19.5 mph will blow up your run." },
  { num: 4, title: "Skipping brick workouts", fix: "Mandatory from Week 7. Even 10 minutes off the bike counts." },
  { num: 5, title: "Under-fueling during training", fix: "Fueling = better adaptation = faster race. Treat long sessions like mini-races." },
  { num: 6, title: "Neglecting swim", fix: "Swim takes longest to develop. Prioritize from Week 1. Find a masters group." },
  { num: 7, title: "Plain water without sodium", fix: "Always pair water with electrolytes on sessions over 60 min." },
  { num: 8, title: "Skipping the taper", fix: "Fitness is locked in by Week 22. Taper is mandatory — trust it." },
  { num: 9, title: "No gut training", fix: "Starting Week 7: consume gels/liquids every 20–25 min on all long sessions." },
  { num: 10, title: "Fiber/fat 3 days before race", fix: "Carb load protocol only Dec 3–5 — cut ALL fiber and fat completely." },
];

// ─── Split targets ────────────────────────────────────────────────────────────

export const RACE_SPLITS = {
  swim: { distance: "1.2 miles", target: "36:00", pace: "1:52/100m" },
  t1:   { target: "4:00" },
  bike: { distance: "56 miles",  target: "2:55:00", pace: "19.2 mph avg" },
  t2:   { target: "2:00" },
  run:  { distance: "13.1 miles", target: "1:58:00", pace: "9:00/mile" },
  total: { target: "4:55:00" },
};

// ─── Race day fueling timeline ────────────────────────────────────────────────

export const RACE_FUELING = [
  { time: "3 hrs before", segment: "Pre-Race", detail: "600–800 cal | 120–150g carbs | oatmeal + banana + sports drink | 16–24 oz water | 500mg sodium" },
  { time: "45 min before", segment: "Top-Up", detail: "200mg caffeine + 1 gel (100 cal) + 8 oz water + electrolyte tab (200mg sodium)" },
  { time: "Swim", segment: "Swim — No fuel", detail: "Nothing. Stay calm, draft off other athletes, negative split second half." },
  { time: "T1", segment: "T1", detail: "Optional 1 chew or sip sports drink if T1 allows" },
  { time: "Bike min 15", segment: "Bike — Start fueling", detail: "First gel + sip drink. Set a 20-min timer NOW." },
  { time: "Every 20–25 min", segment: "Bike — Repeat", detail: "60–90g carbs/hr | 24–32 oz fluid/hr | 500–1,000mg sodium/hr | Maurten / SIS / Clif Bloks" },
  { time: "T2", segment: "T2", detail: "Caffeine gel if not already used (100mg). 4 oz water." },
  { time: "Run miles 1–4", segment: "Run — Early", detail: "30–45g carbs/hr | 6–8 oz water at each aid station | 300mg sodium/hr | gels + water" },
  { time: "Run miles 6 & 9", segment: "Run — Mid", detail: "Cola at aid stations for caffeine boost. Sip, do not chug." },
  { time: "Run miles 10–13.1", segment: "Run — Finish", detail: "Cola or final gel + water only. Push to the line." },
];
