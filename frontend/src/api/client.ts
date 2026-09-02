import { DEMO_BUILD, demoApi } from "../demo";

// The demo build is served from GitHub Pages with no API alongside it, so it
// needs an absolute URL. Everywhere else the dev server and nginx proxy /api.
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

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

export class ApiNotReadyError extends Error {}
export class UnauthorizedError extends Error {}

const TOKEN_KEY = "ironman_token";

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

function authHeaders(): Record<string, string> {
  const t = token.get();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function handle<T>(res: Response): Promise<T> {
  // A 401 means the token is missing, forged, or expired. Drop it so the app
  // falls back to the sign-in screen instead of retrying forever.
  if (res.status === 401) {
    token.clear();
    throw new UnauthorizedError("sign in again");
  }
  // 404 means API is up but no data yet — not the same as being offline
  if (res.status === 404) throw new ApiNotReadyError("no data yet");
  if (!res.ok) {
    // Surface the server's reason. A bare status code tells the user nothing
    // about which field they got wrong.
    const detail = await res.json().catch(() => null);
    const message =
      typeof detail?.detail === "string"
        ? detail.detail
        : Array.isArray(detail?.detail)
        ? detail.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ")
        : `${res.status} ${res.statusText}`;
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  return handle<T>(await fetch(`${BASE}${path}`, { headers: authHeaders() }));
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return handle<T>(await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  }));
}

async function del<T>(path: string): Promise<T> {
  return handle<T>(await fetch(`${BASE}${path}`, {
    method: "DELETE",
    headers: authHeaders(),
  }));
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

export interface SleepEntry {
  date: string;
  sleep_score: number | null;
  sleep_score_qualifier: string | null;
  duration_hours: number | null;
  deep_sleep_hours: number | null;
  light_sleep_hours: number | null;
  rem_sleep_hours: number | null;
  hrv_nightly_avg: number | null;
  resting_hr: number | null;
  readiness_score: number | null;
  readiness_signal: "green" | "yellow" | "red" | null;
  readiness_headline: string | null;
  readiness_limiter: string | null;
}

export interface SleepSummary {
  today: SleepEntry | null;
  last_7_days: SleepEntry[];
  avg_score_7d: number | null;
  avg_hrv_7d: number | null;
  trend: "improving" | "stable" | "declining";
}

export interface Requirement {
  key: string;
  discipline: "swim" | "bike" | "run" | "brick" | "rest";
  intensity: "endurance" | "easy" | "threshold" | "intervals" | "brick" | "rest";
  label: string;
  completed: boolean;
  completed_at: string | null;
}

export interface WeekGroup {
  discipline: Requirement["discipline"];
  done: number;
  target: number;
  requirements: Requirement[];
}

export interface WeekProgress {
  completed: number;
  total: number;
  training_completed: number;
  training_total: number;
  by_discipline: Record<string, number>;
  targets: Record<string, number>;
}

export interface WeekPlan {
  week_start: string;
  week_end: string;
  groups: WeekGroup[];
  progress: WeekProgress;
}

export interface AuthResult {
  access_token: string;
  token_type: string;
  athlete_id: number;
  display_name: string | null;
}

export const auth = {
  signup: (email: string, password: string, display_name?: string) =>
    post<AuthResult>("/auth/signup", { email, password, display_name }),
  login: (email: string, password: string) =>
    post<AuthResult>("/auth/login", { email, password }),
  me: () => get<{ id: number; email: string; display_name: string | null; garmin_connected: boolean }>("/auth/me"),
};

const liveApi = {
  getWeek: (weekOf?: string) =>
    get<WeekPlan>(`/week/${weekOf ? `?week_of=${weekOf}` : ""}`),
  completeSession: (key: string, weekOf?: string) =>
    post<WeekPlan>(`/week/complete/${key}${weekOf ? `?week_of=${weekOf}` : ""}`, {}),
  uncompleteSession: (key: string, weekOf?: string) =>
    del<WeekPlan>(`/week/complete/${key}${weekOf ? `?week_of=${weekOf}` : ""}`),
  getMetrics: (days = 90) => get<MetricsSummary>(`/metrics/?days=${days}`),
  getActivities: (limit = 30) => get<ActivityRecord[]>(`/activities/?limit=${limit}`),
  getSleep: () => get<SleepSummary>("/sleep/"),
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

// The demo build serves the snapshot to anonymous visitors and the live API to
// anyone holding a token. Sync is the only control that needs the difference,
// and the server rejects it without a token regardless of what the UI shows.
//
// Read once at load: signing in reloads the page, which re-evaluates this.
export const USING_SNAPSHOT = DEMO_BUILD && !token.get();

export const api = USING_SNAPSHOT ? (demoApi as unknown as typeof liveApi) : liveApi;
