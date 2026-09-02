// Demo mode: serve a frozen snapshot of real training data instead of calling
// the API. The public build has no backend behind it — no Postgres, no Garmin
// credentials on a server — so every read resolves from these JSON files and
// every write stays in memory for the length of the visit.
//
// Refresh the snapshot with `scripts/snapshot.sh`.
import type {
  MetricsSummary,
  ActivityRecord,
  SleepSummary,
  WeekPlan,
  Requirement,
  GymWorkout,
  AdaptivePlan,
} from "../api/client";

import metricsJson from "./snapshot/metrics.json";
import activitiesJson from "./snapshot/activities.json";
import sleepJson from "./snapshot/sleep.json";
import weekJson from "./snapshot/week.json";

// True in the build published to GitHub Pages. It means "there is no backend
// on this origin", not "never talk to an API" — signing in points the same
// build at the live API instead of the snapshot.
export const DEMO_BUILD = import.meta.env.VITE_DEMO === "true";

const metrics = metricsJson as unknown as MetricsSummary;
const activities = activitiesJson as unknown as ActivityRecord[];
const sleep = sleepJson as unknown as SleepSummary;

// The date the snapshot was taken. Shown in the demo banner so a visitor reads
// the numbers as a captured moment rather than as today's training.
export const SNAPSHOT_DATE = metrics.today?.date ?? metrics.history[metrics.history.length - 1]?.date ?? null;

// Mutable so the weekly checklist still responds to clicks. Structured clone
// keeps the imported module untouched, so a reload restores the original.
let week: WeekPlan = structuredClone(weekJson) as unknown as WeekPlan;

function recount(plan: WeekPlan): WeekPlan {
  // Mirror the server's counting exactly. The rest day is part of `completed`
  // but not of `training_completed`, and the ring renders the training pair —
  // so folding rest into both makes a week with an unticked session read as
  // finished.
  let completed = 0;
  let trainingCompleted = 0;
  const byDiscipline: Record<string, number> = {};

  for (const group of plan.groups) {
    group.done = group.requirements.filter((r) => r.completed).length;
    byDiscipline[group.discipline] = group.done;
    completed += group.done;
    if (group.discipline !== "rest") trainingCompleted += group.done;
  }

  plan.progress.completed = completed;
  plan.progress.training_completed = trainingCompleted;
  plan.progress.by_discipline = byDiscipline;
  return plan;
}

function setCompletion(key: string, value: boolean): WeekPlan {
  for (const group of week.groups) {
    const req = group.requirements.find((r: Requirement) => r.key === key);
    if (req) {
      req.completed = value;
      req.completed_at = value ? new Date().toISOString() : null;
    }
  }
  return recount(week);
}

const ok = <T>(value: T): Promise<T> => Promise.resolve(value);

export const demoApi = {
  getWeek: () => ok(week),
  completeSession: (key: string) => ok(setCompletion(key, true)),
  uncompleteSession: (key: string) => ok(setCompletion(key, false)),
  getMetrics: () => ok(metrics),
  getActivities: (limit = 30) => ok(activities.slice(0, limit)),
  getSleep: () => ok(sleep),
  getTodayPlan: () =>
    ok({ plan: "Session planning runs on the live backend and is disabled in this demo." }),
  getSplit: () => ok({ split_day: "push", allowed: ["push", "pull", "legs"] }),
  getGymWorkouts: () => ok([] as GymWorkout[]),
  getExerciseNames: () => ok([] as string[]),
  logGymWorkout: () => Promise.reject(new Error("Read-only demo")),
  triggerSync: () => ok({ status: "demo" }),
  getAdaptivePlan: () => Promise.reject(new Error("Read-only demo")) as Promise<AdaptivePlan>,
  triggerAdaptiveGeneration: () => Promise.reject(new Error("Read-only demo")),
};
