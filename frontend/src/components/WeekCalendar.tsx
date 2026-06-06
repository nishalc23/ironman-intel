import { useState, useMemo, useEffect } from "react";
import { PLAN, RACE_DATE, PLAN_START, type Week, type DayPlan } from "../data/plan";
import WorkoutCard from "./WorkoutCard";
import { api, type AdaptivePlan } from "../api/client";

const PHASE_CONFIG: Record<string, { color: string; glow: string; label: string }> = {
  foundation: { color: "#38BDF8", glow: "rgba(56,189,248,0.12)", label: "Foundation" },
  build:      { color: "#A78BFA", glow: "rgba(167,139,250,0.12)", label: "Build" },
  peak:       { color: "#F87171", glow: "rgba(248,113,113,0.12)", label: "Peak" },
  taper:      { color: "#FBBF24", glow: "rgba(251,191,36,0.12)",  label: "Taper" },
  race_week:  { color: "#34D399", glow: "rgba(52,211,153,0.12)",  label: "Race Week" },
};

const DAY_ACCENT: Record<string, string> = {
  Monday:    "#A78BFA",
  Tuesday:   "#38BDF8",
  Wednesday: "#34D399",
  Thursday:  "#3F3F46",
  Friday:    "#FB923C",
  Saturday:  "#FBBF24",
  Sunday:    "#3F3F46",
};

function currentWeekIndex(): number {
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  if (now < PLAN_START) return 0;
  const diff = Math.floor((now.getTime() - PLAN_START.getTime()) / (7 * 86400000));
  return Math.min(diff, PLAN.length - 1);
}

function fmt(d: Date): string {
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function SportDot({ sport }: { sport: string }) {
  const colors: Record<string, string> = {
    swim: "#38BDF8", bike: "#34D399", run: "#FB923C",
    gym: "#A78BFA", brick: "#FBBF24", rest: "#3F3F46",
  };
  return (
    <span className="inline-block w-1.5 h-1.5 rounded-full"
      style={{ background: colors[sport] ?? "#6B7280", boxShadow: `0 0 4px ${colors[sport] ?? "#6B7280"}` }} />
  );
}

function WeekPill({ week, isActive, isCurrent, onClick }: {
  week: Week; isActive: boolean; isCurrent: boolean; onClick: () => void;
}) {
  const cfg = PHASE_CONFIG[week.phase];
  return (
    <button
      onClick={onClick}
      className="shrink-0 w-9 h-9 rounded-xl text-[11px] font-bold mono transition-all border"
      style={isActive ? {
        background: cfg.color,
        borderColor: cfg.color,
        color: "#080810",
        boxShadow: `0 0 12px ${cfg.color}60`,
      } : isCurrent ? {
        background: "transparent",
        borderColor: cfg.color,
        color: cfg.color,
      } : {
        background: "rgba(255,255,255,0.03)",
        borderColor: "rgba(255,255,255,0.08)",
        color: cfg.color + "99",
      }}
    >
      {week.weekNumber}
    </button>
  );
}

function DayColumn({ day, date }: { day: DayPlan; date: Date }) {
  const storageKey = `completed-${date.toISOString().split("T")[0]}-${day.dayOfWeek}`;
  const [completed, setCompleted] = useState<Record<number, boolean>>(() => {
    try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch { return {}; }
  });
  const accent = DAY_ACCENT[day.dayOfWeek] ?? "#6B7280";
  const doneCount = Object.values(completed).filter(Boolean).length;
  const total = day.blocks.filter(b => b.sport !== "rest").length;
  const isToday = date.toDateString() === new Date().toDateString();
  const dateLabel = date.toLocaleDateString("en-US", { month: "short", day: "numeric" });

  function toggleBlock(i: number) {
    const next = { ...completed, [i]: !completed[i] };
    setCompleted(next);
    localStorage.setItem(storageKey, JSON.stringify(next));
  }

  return (
    <div className="flex flex-col rounded-2xl overflow-hidden"
      style={{
        border: isToday ? `1px solid ${accent}60` : "1px solid rgba(255,255,255,0.06)",
        background: isToday ? `${accent}08` : "rgba(255,255,255,0.02)",
        boxShadow: isToday ? `0 0 16px ${accent}20` : "none",
      }}>
      {/* Day header */}
      <div className="px-3 py-2.5 border-b flex items-center justify-between"
        style={{
          borderLeftWidth: 3,
          borderLeftColor: accent,
          borderLeftStyle: "solid",
          borderBottomColor: "rgba(255,255,255,0.05)",
          borderBottomStyle: "solid",
          borderBottomWidth: 1,
        }}>
        <div>
          <div className="flex items-center gap-1.5">
            <p className="text-xs font-bold text-white">{day.dayOfWeek.slice(0,3)}</p>
            {isToday && (
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full mono"
                style={{ background: accent, color: "#080810" }}>TODAY</span>
            )}
          </div>
          <p className="text-[11px] mono mt-0.5" style={{ color: accent + "99" }}>{dateLabel}</p>
        </div>
        {total > 0 && (
          <div className="flex items-center gap-1">
            <span className="text-[10px] mono text-zinc-600">{doneCount}/{total}</span>
            {doneCount === total && <span className="text-emerald-400 text-xs">✓</span>}
          </div>
        )}
      </div>

      {/* Blocks */}
      <div className="flex-1 p-2 space-y-2">
        {day.blocks.map((block, i) => (
          <WorkoutCard
            key={i}
            block={block}
            completed={completed[i]}
            onToggle={() => toggleBlock(i)}
          />
        ))}
      </div>
    </div>
  );
}

function SidebarWeekRow({ week, isActive, isCurrent, onClick }: {
  week: Week; isActive: boolean; isCurrent: boolean; onClick: () => void;
}) {
  const cfg = PHASE_CONFIG[week.phase];
  const end = new Date(week.startDate.getTime() + 6 * 86400000);
  return (
    <button onClick={onClick}
      className="w-full text-left rounded-xl border px-3 py-2.5 transition-all"
      style={isActive ? {
        borderColor: cfg.color + "50",
        background: cfg.color + "12",
      } : {
        borderColor: "rgba(255,255,255,0.06)",
        background: "rgba(255,255,255,0.02)",
      }}>
      <div className="flex items-center gap-2.5">
        <div className="w-1.5 h-8 rounded-full shrink-0" style={{ background: cfg.color, opacity: isActive ? 1 : 0.4 }} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold mono" style={{ color: isActive ? cfg.color : "#fff" }}>
              W{week.weekNumber}
            </span>
            {isCurrent && !isActive && (
              <span className="text-[9px] border px-1 rounded" style={{ borderColor: cfg.color, color: cfg.color }}>NOW</span>
            )}
            {week.isRecovery && (
              <span className="text-[9px] text-amber-400 border border-amber-400/30 px-1 rounded">REC</span>
            )}
            <span className="text-[10px] text-zinc-600 ml-auto mono">{fmt(week.startDate)}</span>
          </div>
          <div className="flex gap-1 mt-1.5 flex-wrap">
            {week.days.map((d, i) =>
              d.blocks.map((b, j) => <SportDot key={`${i}-${j}`} sport={b.sport} />)
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

export default function WeekCalendar() {
  const initWeek = useMemo(() => currentWeekIndex(), []);
  const [sel, setSel] = useState(initWeek);
  const [sidebar, setSidebar] = useState(false);
  const [adaptivePlan, setAdaptivePlan] = useState<AdaptivePlan | null>(null);
  const [adaptiveLoading, setAdaptiveLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const week = PLAN[sel];
  const cfg = PHASE_CONFIG[week.phase];
  const weekNum = week.weekNumber;

  // Fetch adaptive plan whenever selected week changes
  useEffect(() => {
    setAdaptivePlan(null);
    api.getAdaptivePlan(weekNum).then(setAdaptivePlan).catch(() => {
      // 404 = not generated yet, use static plan — that's fine
    });
  }, [weekNum]);

  // Use adaptive days if available, otherwise fall back to static plan
  const activeDays: DayPlan[] = adaptivePlan
    ? (adaptivePlan.days as DayPlan[])
    : week.days;

  async function handleGenerate() {
    setGenerating(true);
    try {
      // Fire and forget — backend returns immediately
      await api.triggerAdaptiveGeneration(weekNum);
      // Poll every 2s until the plan appears (Claude takes ~5-15s)
      const start = Date.now();
      while (Date.now() - start < 60000) {
        await new Promise(r => setTimeout(r, 2000));
        try {
          const plan = await api.getAdaptivePlan(weekNum);
          setAdaptivePlan(plan);
          break;
        } catch {
          // Not ready yet — keep polling
        }
      }
    } catch (e) {
      console.error("Generation failed", e);
    } finally {
      setGenerating(false);
    }
  }

  const end = new Date(week.startDate.getTime() + 6 * 86400000);
  const dtr = Math.ceil((RACE_DATE.getTime() - new Date().setHours(0,0,0,0)) / 86400000);

  return (
    <div className="space-y-4">
      {/* Week strip */}
      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {PLAN.map((w, i) => (
          <WeekPill key={i} week={w} isActive={i === sel} isCurrent={i === initWeek} onClick={() => setSel(i)} />
        ))}
      </div>

      {/* Active week header */}
      <div className="flex items-center justify-between px-4 py-3 rounded-2xl border"
        style={{ borderColor: cfg.color + "30", background: cfg.glow }}>
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full" style={{ background: cfg.color, boxShadow: `0 0 8px ${cfg.color}` }} />
          <div>
            <p className="text-xs font-bold text-white flex items-center gap-2">
              {week.phaseLabel}
              {adaptivePlan && (
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full mono"
                  style={{ background: "#34D399", color: "#080810" }}>
                  ⚡ ADAPTIVE
                </span>
              )}
            </p>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              {adaptivePlan ? adaptivePlan.adaptation_notes ?? week.focus : week.focus}
            </p>
            {adaptivePlan?.missed_sessions && adaptivePlan.missed_sessions.length > 0 && (
              <p className="text-[10px] text-amber-400 mt-0.5">
                ⚠ Last week missed: {adaptivePlan.missed_sessions.join(", ")}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-right hidden sm:block">
            <p className="text-[11px] mono text-zinc-400">{fmt(week.startDate)} – {fmt(end)}</p>
            <p className="text-[10px] text-zinc-600">Week {week.weekNumber} of 26</p>
          </div>
          {week.isRecovery && (
            <span className="text-[10px] font-bold px-2 py-1 rounded-lg border border-amber-400/30 text-amber-400"
              style={{ background: "rgba(251,191,36,0.08)" }}>
              RECOVERY
            </span>
          )}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="text-[11px] font-semibold px-3 py-1.5 rounded-lg border transition-all disabled:opacity-50"
            style={{ borderColor: "#34D39940", color: "#34D399", background: "rgba(52,211,153,0.08)" }}
            title="Generate adaptive plan using your real training data"
          >
            {generating ? (
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
                <span className="animate-pulse">Claude thinking…</span>
              </span>
            ) : adaptivePlan ? "↻ Regenerate" : "⚡ Adapt"}
          </button>
          <button onClick={() => setSidebar(true)}
            className="text-[11px] text-zinc-500 hover:text-white border px-3 py-1.5 rounded-lg transition-colors"
            style={{ borderColor: "rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.03)" }}>
            All weeks ↗
          </button>
        </div>
      </div>

      {/* M–S grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
        {activeDays.map((day, i) => {
          const date = new Date(week.startDate.getTime() + i * 86400000);
          return <DayColumn key={date.toISOString().split("T")[0]} day={day} date={date} />;
        })}
      </div>

      {/* Week nav */}
      <div className="flex items-center justify-between">
        <button disabled={sel === 0} onClick={() => setSel(s => s - 1)}
          className="text-xs text-zinc-500 hover:text-white disabled:opacity-20 border border-white/8 px-4 py-2 rounded-xl transition-colors"
          style={{ background: "rgba(255,255,255,0.03)" }}>
          ← Prev
        </button>
        <button onClick={() => setSel(initWeek)}
          className="text-xs font-semibold border px-4 py-2 rounded-xl transition-all"
          style={{ borderColor: cfg.color + "40", color: cfg.color, background: cfg.color + "10" }}>
          This Week
        </button>
        <button disabled={sel === PLAN.length - 1} onClick={() => setSel(s => s + 1)}
          className="text-xs text-zinc-500 hover:text-white disabled:opacity-20 border border-white/8 px-4 py-2 rounded-xl transition-colors"
          style={{ background: "rgba(255,255,255,0.03)" }}>
          Next →
        </button>
      </div>

      {/* All-weeks sidebar */}
      {sidebar && (
        <div className="fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setSidebar(false)} />
          <div className="relative ml-auto w-80 h-full overflow-y-auto border-l border-white/8 p-4 space-y-2"
            style={{ background: "rgba(8,8,16,0.97)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white">All 26 Weeks</h3>
              <button onClick={() => setSidebar(false)} className="text-zinc-500 hover:text-white text-lg transition-colors">✕</button>
            </div>
            {/* Phase legend */}
            <div className="flex flex-wrap gap-2 pb-3 mb-1 border-b border-white/6">
              {Object.entries(PHASE_CONFIG).map(([key, c]) => (
                <div key={key} className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full" style={{ background: c.color }} />
                  <span className="text-[10px] text-zinc-500">{c.label}</span>
                </div>
              ))}
            </div>
            {PLAN.map((w, i) => (
              <SidebarWeekRow
                key={i} week={w} isActive={i === sel} isCurrent={i === initWeek}
                onClick={() => { setSel(i); setSidebar(false); }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
