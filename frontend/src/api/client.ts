const BASE = "/api";

export interface DailyMetric {
  date: string;
  ctl: number | null;
  atl: number | null;
  tsb: number | null;
  daily_tss: number;
  swim_km: number;
  bike_km: number;
  run_km: number;
}

export interface MetricsSummary {
  athlete_name: string | null;
  today: DailyMetric | null;
  history: DailyMetric[];
  overtraining_risk: "low" | "moderate" | "high";
}

export interface ActivityRecord {
  id: number;
  garmin_activity_id: string;
  discipline: string;
  start_time: string;
  duration_seconds: number;
  distance_meters: number | null;
  avg_heart_rate: number | null;
  avg_power: number | null;
  calories: number | null;
  tss: number | null;
}

export interface GymSet {
  reps: number;
  weight_lbs: number | null;
}

export interface GymExercise {
  name: string;
  sets: GymSet[];
}

export interface GymWorkout {
  id: number;
  date: string;
  duration_minutes: number | null;
  notes: string | null;
  exercises: GymExercise[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export interface AdaptivePlan {
  week_number: number;
  week_start: string;
  phase: string;
  adaptation_notes: string | null;
  volume_adjustment: string | null;
  missed_sessions: string[];
  prior_ctl: string | null;
  prior_atl: string | null;
  prior_tsb: string | null;
  days: unknown[];
  generated_at: string;
}

export const api = {
  getMetrics: (days = 90) => get<MetricsSummary>(`/metrics/?days=${days}`),
  getActivities: (limit = 30) => get<ActivityRecord[]>(`/activities/?limit=${limit}`),
  getTodayPlan: (gym: boolean, discipline: string, split?: string) =>
    get<{ plan: string }>(`/plan/today?gym=${gym}&discipline=${discipline}${split ? `&split=${split}` : ""}`),
  getSplit: () => get<{ split_day: string; allowed: string[] }>("/plan/split"),
  getGymWorkouts: () => get<GymWorkout[]>("/gym/"),
  getExerciseNames: () => get<string[]>("/gym/exercises"),
  logGymWorkout: (payload: unknown) => post<GymWorkout>("/gym/", payload),
  triggerSync: () => post<{ status: string }>("/sync/", {}),
  getAdaptivePlan: (weekNum: number) => get<AdaptivePlan>(`/plan/adaptive/${weekNum}`),
  triggerAdaptiveGeneration: (weekNum?: number) =>
    post<{ status: string; week_number: number; adaptation_notes: string }>(
      `/plan/adaptive/generate${weekNum ? `?week_number=${weekNum}` : ""}`,
      {}
    ),
};
