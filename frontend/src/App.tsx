import { useEffect, useState, useCallback } from "react";
import { api, ApiNotReadyError } from "./api/client";
import type { MetricsSummary, ActivityRecord, SleepSummary } from "./api/client";
import WeeklyChart from "./components/WeeklyChart";
import SleepCard from "./components/SleepCard";
import FitnessChart from "./components/FitnessChart";
import ActivityList from "./components/ActivityList";
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
    <div className="glass relative flex flex-col gap-2 p-4 rounded-2xl overflow-hidden
      motion-safe:transition-transform motion-safe:duration-300 hover:-translate-y-0.5">
      {/* Corner accent */}
      <div className={`absolute top-0 left-0 w-8 h-8 opacity-20`}
        style={{ background: `radial-gradient(circle at 0 0, ${color}, transparent 70%)` }} />
      <span className="text-[10px] font-semibold tracking-widest uppercase text-paper-muted">{label}</span>
      <div className="flex items-end gap-1">
        <span className={`text-3xl font-black mono flicker`} style={{ color }}>{display}</span>
        {unit && <span className="text-xs text-paper-dim mb-1">{unit}</span>}
      </div>
      {sub && <span className="text-[11px] text-paper-dim leading-tight">{sub}</span>}
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
      className="relative flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold border border-white/15
        backdrop-blur-md motion-safe:transition-all disabled:opacity-50 hover:border-accent/60
        motion-safe:hover:-translate-y-0.5 cursor-pointer"
      style={{ background: "rgba(255,255,255,0.07)", boxShadow: "inset 0 1px 0 rgba(255,255,255,0.18)" }}
    >
      {syncing ? (
        <>
          <span className="w-3 h-3 border border-accent border-t-transparent rounded-full animate-spin" />
          <span className="text-paper-muted">Syncing…</span>
        </>
      ) : (
        <>
          <span className="text-accent text-base">⟳</span>
          <span className="text-paper hidden sm:inline">Sync</span>
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
        <span className="text-[9px] tracking-widest text-paper-muted uppercase">days</span>
      </div>
      <div className="w-px h-8 bg-ironman-red/20" />
      <div className="flex flex-col">
        <span className="text-[10px] font-semibold text-paper-muted">IRONMAN 70.3</span>
        <span className="text-[10px] text-paper-dim">La Quinta · Dec 6, 2026</span>
      </div>
    </div>
  );
}

export default function App() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [activities, setActivities] = useState<ActivityRecord[]>([]);
  const [sleep, setSleep] = useState<SleepSummary | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [apiDown, setApiDown] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [m, a, s] = await Promise.all([
        api.getMetrics(),
        api.getActivities(),
        api.getSleep(),
      ]);
      setMetrics(m);
      setActivities(a);
      setSleep(s);
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
      // Poll every 5s for up to 60s — Garmin sync on Render takes 20-30s
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        await loadAll();
        if (attempts >= 12) {
          clearInterval(poll);
          setSyncing(false);
        }
      }, 5000);
    } catch {
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
    <div className="relative min-h-screen">
      {/* Ambient colour field. Glass has nothing to refract without it. */}
      <div className="aurora" aria-hidden>
        <span className="a1" /><span className="a2" /><span className="a3" />
      </div>
      <div className="relative z-10">

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-white/10 px-5 py-3 flex items-center justify-between
          backdrop-blur-xl backdrop-saturate-150"
        style={{ background: "rgba(15,23,42,0.55)", boxShadow: "inset 0 -1px 0 rgba(255,255,255,0.06)" }}>
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div className="relative w-9 h-9 rounded-xl flex items-center justify-center text-white font-black text-sm shrink-0 overflow-hidden"
            style={{ background: "linear-gradient(135deg, #22C55E, #0080FF)", boxShadow: "0 6px 18px -8px #22C55E" }}>
            <span className="relative z-10">IM</span>
            <div className="absolute inset-0 opacity-30"
              style={{ background: "linear-gradient(135deg, rgba(255,255,255,0.3), transparent)" }} />
          </div>
          <div>
            <h1 className="text-sm font-bold text-paper tracking-tight">Ironman Intel</h1>
            <p className="text-[11px] text-paper-dim mono">
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
        <WeeklyChart />

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

        {/* ── SLEEP + ACTIVITY ─────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SleepCard data={sleep} />
          <ActivityList activities={activities} />
        </div>
      </main>
      </div>
    </div>
  );
}
