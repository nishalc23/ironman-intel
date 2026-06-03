import { useEffect, useState, useCallback } from "react";
import { api, ApiNotReadyError } from "./api/client";
import type { MetricsSummary, ActivityRecord, GymWorkout } from "./api/client";
import WeekCalendar from "./components/WeekCalendar";
import SleepCard from "./components/SleepCard";
import FitnessChart from "./components/FitnessChart";
import ActivityList from "./components/ActivityList";
import GymLog from "./components/GymLog";
import { RACE_DATE } from "./data/plan";

function daysUntilRace() {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  return Math.ceil((RACE_DATE.getTime() - now.getTime()) / 86400000);
}

function HUDStat({ label, value, sub, color, unit }: {
  label: string; value: string | number | null; sub?: string; color: string; unit?: string;
}) {
  const display = value != null ? String(value) : "—";
  return (
    <div className="relative flex flex-col gap-2 p-4 rounded-2xl border border-white/6 overflow-hidden"
      style={{ background: "rgba(255,255,255,0.025)" }}>
      {/* Corner accent */}
      <div className={`absolute top-0 left-0 w-8 h-8 opacity-20`}
        style={{ background: `radial-gradient(circle at 0 0, ${color}, transparent 70%)` }} />
      <span className="text-[10px] font-semibold tracking-widest uppercase text-zinc-500">{label}</span>
      <div className="flex items-end gap-1">
        <span className={`text-3xl font-black mono flicker`} style={{ color }}>{display}</span>
        {unit && <span className="text-xs text-zinc-600 mb-1">{unit}</span>}
      </div>
      {sub && <span className="text-[11px] text-zinc-600 leading-tight">{sub}</span>}
      {/* Bottom glow line */}
      <div className="absolute bottom-0 left-0 right-0 h-px opacity-40"
        style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }} />
    </div>
  );
}

function SyncButton({ syncing, onClick }: { syncing: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      disabled={syncing}
      className="relative flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all disabled:opacity-50 border border-white/10 hover:border-ironman-red/50"
      style={{ background: "rgba(255,255,255,0.04)" }}
    >
      {syncing ? (
        <>
          <span className="w-3 h-3 border border-ironman-red border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Syncing…</span>
        </>
      ) : (
        <>
          <span className="text-ironman-red text-base">⟳</span>
          <span className="text-zinc-300 hidden sm:inline">Sync</span>
        </>
      )}
    </button>
  );
}

function RaceCountdown({ days }: { days: number }) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 rounded-xl border border-ironman-red/20 glow-pulse"
      style={{ background: "rgba(232,0,28,0.06)" }}>
      <div className="flex flex-col items-center">
        <span className="text-2xl font-black mono text-ironman-red leading-none flicker">{days}</span>
        <span className="text-[9px] tracking-widest text-zinc-500 uppercase">days</span>
      </div>
      <div className="w-px h-8 bg-ironman-red/20" />
      <div className="flex flex-col">
        <span className="text-[10px] font-semibold text-zinc-400">IRONMAN 70.3</span>
        <span className="text-[10px] text-zinc-600">La Quinta · Dec 6, 2026</span>
      </div>
    </div>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [activities, setActivities] = useState<ActivityRecord[]>([]);
  const [gymWorkouts, setGymWorkouts] = useState<GymWorkout[]>([]);
  const [syncing, setSyncing] = useState(false);
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
    } catch (e) {
      // 404 = API is up but no athlete synced yet — show "needs sync" not "offline"
      if (e instanceof ApiNotReadyError) {
        setApiDown(false);
      } else {
        setApiDown(true);
      }
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  async function handleSync() {
    setSyncing(true);
    try {
      await api.triggerSync();
      setTimeout(loadAll, 8000);
    } finally {
      setSyncing(false);
    }
  }

  const today = metrics?.today;
  const dtr = daysUntilRace();

  const tsbStatus = !today?.tsb ? { label: "No data", color: "#6B7280" }
    : today.tsb > 5   ? { label: "Race ready", color: "#34D399" }
    : today.tsb < -30 ? { label: "Danger zone", color: "#F87171" }
    : today.tsb < -10 ? { label: "Accumulating", color: "#FBBF24" }
    : { label: "Training load", color: "#A78BFA" };

  return (
    <div className="min-h-screen grid-bg" style={{ background: "#080810" }}>
      {/* Ambient top glow */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[600px] h-[200px] opacity-10 pointer-events-none"
        style={{ background: "radial-gradient(ellipse at top, #E8001C, transparent 70%)" }} />

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/6 px-5 py-3 flex items-center justify-between"
        style={{ background: "rgba(8,8,16,0.85)", backdropFilter: "blur(24px)" }}>
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="relative w-9 h-9 rounded-xl flex items-center justify-center text-white font-black text-sm shrink-0 overflow-hidden"
            style={{ background: "linear-gradient(135deg, #E8001C, #9B000E)" }}>
            <span className="relative z-10">IM</span>
            <div className="absolute inset-0 opacity-30"
              style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.3), transparent)" }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-white tracking-tight">Ironman Intel</h1>
              <span className="hidden sm:block text-[10px] border border-ironman-red/30 text-ironman-red px-1.5 py-0.5 rounded mono">v2</span>
            </div>
            <p className="text-[11px] text-zinc-600 mono">
              {metrics?.athlete_name ?? "nishal"} · sub-5:00 target
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <RaceCountdown days={dtr} />
          <SyncButton syncing={syncing} onClick={handleSync} />
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 space-y-6">

        {/* API down banner */}
        {apiDown && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-yellow-500/20 text-yellow-400 text-xs"
            style={{ background: "rgba(234,179,8,0.05)" }}>
            <span className="text-base">⚠</span>
            <span>No data yet — hit ⟳ Sync to pull your Garmin data</span>
          </div>
        )}

        {/* ── HUD STAT ROW ─────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <HUDStat
            label="Fitness · CTL"
            value={today?.ctl != null ? Math.round(today.ctl) : null}
            sub="42-day chronic load"
            color="#38BDF8"
          />
          <HUDStat
            label="Fatigue · ATL"
            value={today?.atl != null ? Math.round(today.atl) : null}
            sub="7-day acute load"
            color="#FB923C"
          />
          <HUDStat
            label="Form · TSB"
            value={today?.tsb != null ? Math.round(today.tsb) : null}
            sub={tsbStatus.label}
            color={tsbStatus.color}
          />
          <HUDStat
            label="TSS Today"
            value={today?.daily_tss != null ? Math.round(today.daily_tss) : 0}
            sub="training stress score"
            color="#A78BFA"
          />
        </div>

        {/* ── CHARTS ROW ───────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="lg:col-span-3">
            <FitnessChart history={metrics?.history ?? []} />
          </div>
        </div>

        {/* ── DIVIDER ──────────────────────────────────────────── */}
        <div className="flex items-center gap-4">
          <div className="flex-1 h-px" style={{ background: "linear-gradient(90deg, transparent, rgba(232,0,28,0.3), transparent)" }} />
          <span className="text-[10px] tracking-widest text-zinc-600 uppercase mono">26-week plan</span>
          <div className="flex-1 h-px" style={{ background: "linear-gradient(90deg, transparent, rgba(232,0,28,0.3), transparent)" }} />
        </div>

        {/* ── WEEK CALENDAR ────────────────────────────────────── */}
        <WeekCalendar />

        {/* ── SLEEP + ACTIVITY ─────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SleepCard />
          <ActivityList activities={activities} />
        </div>

        {/* ── GYM LOG ──────────────────────────────────────────── */}
        <GymLog recentWorkouts={gymWorkouts} onSaved={loadAll} />
      </main>
    </div>
  );
}
