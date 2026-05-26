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
  weight_kg: number | null;
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

export const api = {
  getMetrics: (days = 90) => get<MetricsSummary>(`/metrics/?days=${days}`),
  getActivities: (limit = 30) => get<ActivityRecord[]>(`/activities/?limit=${limit}`),
  getTodayPlan: () => get<{ plan: string }>("/plan/today"),
  getGymWorkouts: () => get<GymWorkout[]>("/gym/"),
  logGymWorkout: (payload: unknown) => post<GymWorkout>("/gym/", payload),
  triggerSync: () => post<{ status: string }>("/sync/", {}),
};
