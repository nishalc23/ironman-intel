import { useEffect, useState, useCallback } from "react";
import { api } from "./api/client";
import type { MetricsSummary, ActivityRecord, GymWorkout } from "./api/client";
import FitnessChart from "./components/FitnessChart";
import VolumeChart from "./components/VolumeChart";
import ActivityList from "./components/ActivityList";
import TrainingPlan from "./components/TrainingPlan";
import GymLog from "./components/GymLog";

function StatCard({ label, value, sub, color }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="card flex flex-col gap-1">
      <p className="text-xs text-ironman-muted uppercase tracking-wider">{label}</p>
      <p className={`text-3xl font-bold ${color ?? "text-white"}`}>{value}</p>
      {sub && <p className="text-xs text-ironman-muted">{sub}</p>}
    </div>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [activities, setActivities] = useState<ActivityRecord[]>([]);
  const [gymWorkouts, setGymWorkouts] = useState<GymWorkout[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [apiDown, setApiDown] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [m, a, g] = await Promise.all([
        api.getMetrics(),
        api.getActivities(),
        api.getGymWorkouts(),
      ]);
      setMetrics(m);
      setActivities(a);
      setGymWorkouts(g);
      setApiDown(false);
    } catch {
      setApiDown(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  async function handleSync() {
    setSyncing(true);
    try {
      await api.triggerSync();
      setTimeout(loadAll, 8000); // give sync time to complete
    } finally {
      setSyncing(false);
    }
  }

  const today = metrics?.today;
  const tsbColor =
    !today?.tsb ? "text-white" :
    today.tsb > 5 ? "text-green-400" :
    today.tsb < -30 ? "text-red-400" :
    today.tsb < -10 ? "text-yellow-400" :
    "text-white";

  return (
    <div className="min-h-screen bg-ironman-dark">
      {/* Header */}
      <header className="border-b border-ironman-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-ironman-red rounded-lg flex items-center justify-center text-white font-black text-sm">
            IM
          </div>
          <div>
            <h1 className="font-bold text-white text-sm leading-none">Ironman Intel</h1>
            <p className="text-xs text-ironman-muted mt-0.5">
              {metrics?.athlete_name ?? "Loading…"}
            </p>
          </div>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="bg-[#1A1A1A] hover:bg-[#2A2A2A] disabled:opacity-50 border border-ironman-border text-white text-xs font-medium px-4 py-2 rounded-xl transition-colors flex items-center gap-2"
        >
          {syncing ? (
            <>
              <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
              Syncing…
            </>
          ) : (
            "⟳ Sync Garmin"
          )}
        </button>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6 space-y-5">
        {apiDown && (
          <div className="bg-yellow-400/10 border border-yellow-400/30 text-yellow-400 text-sm rounded-xl px-4 py-3">
            API is not running. Start it with <code className="font-mono bg-black/30 px-1 rounded">make api</code> then refresh.
          </div>
        )}

        {loading && !apiDown && (
          <div className="flex justify-center py-20">
            <div className="w-8 h-8 border-2 border-ironman-red border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {!loading && !apiDown && (
          <>
            {/* Stat strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard
                label="Fitness (CTL)"
                value={today?.ctl != null ? Math.round(today.ctl).toString() : "—"}
                sub="42-day base"
                color="text-blue-400"
              />
              <StatCard
                label="Fatigue (ATL)"
                value={today?.atl != null ? Math.round(today.atl).toString() : "—"}
                sub="7-day load"
                color="text-orange-400"
              />
              <StatCard
                label="Form (TSB)"
                value={today?.tsb != null ? Math.round(today.tsb).toString() : "—"}
                sub={
                  !today?.tsb ? "" :
                  today.tsb > 5 ? "Fresh — race ready" :
                  today.tsb < -30 ? "Danger zone" :
                  today.tsb < -10 ? "Accumulating fatigue" :
                  "Normal training load"
                }
                color={tsbColor}
              />
              <StatCard
                label="TSS Today"
                value={today?.daily_tss != null ? Math.round(today.daily_tss).toString() : "0"}
                sub="training stress"
              />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <FitnessChart history={metrics?.history ?? []} />
              <VolumeChart history={metrics?.history ?? []} />
            </div>

            {/* Training plan + activity list */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <TrainingPlan riskLevel={metrics?.overtraining_risk ?? "low"} />
              <ActivityList activities={activities} />
            </div>

            {/* Gym log */}
            <GymLog
              recentWorkouts={gymWorkouts}
              onSaved={loadAll}
            />
          </>
        )}
      </main>
    </div>
  );
}
