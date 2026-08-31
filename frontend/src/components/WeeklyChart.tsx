import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { Requirement, WeekPlan } from "../api/client";
import { DISCIPLINE_ICON, CheckIcon } from "./DisciplineIcon";

const DISCIPLINE = {
  swim:  { color: "#22D3EE", name: "Swim" },
  bike:  { color: "#F59E0B", name: "Bike" },
  run:   { color: "#34D399", name: "Run" },
  brick: { color: "#A78BFA", name: "Brick" },
  rest:  { color: "#8B94A7", name: "Rest" },
} as const;

const FOCUS =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40 " +
  "focus-visible:ring-offset-1 focus-visible:ring-offset-[#0E0E1A]";

function formatRange(startISO: string, endISO: string) {
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  // The ISO date is parsed as UTC, so format in UTC too. Using local time here
  // would shift the label back a day for anyone west of Greenwich.
  const fmt = (iso: string) =>
    new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, { ...opts, timeZone: "UTC" });
  return `${fmt(startISO)} – ${fmt(endISO)}`;
}

function RequirementChip({ req, onToggle, busy }: {
  req: Requirement;
  onToggle: (r: Requirement) => void;
  busy: boolean;
}) {
  const meta = DISCIPLINE[req.discipline];

  return (
    <button
      type="button"
      onClick={() => onToggle(req)}
      disabled={busy}
      aria-pressed={req.completed}
      aria-label={`${meta.name} ${req.label}${req.completed ? ", done" : ""}`}
      className={`group relative flex items-center gap-2 pl-2 pr-3 py-2 rounded-xl border
        motion-safe:transition-all motion-safe:duration-200 cursor-pointer ${FOCUS}
        hover:border-white/25 motion-safe:hover:-translate-y-px motion-safe:active:translate-y-0
        motion-safe:active:scale-[0.97] ${busy ? "opacity-40" : ""}
        ${req.completed ? "border-white/12" : "border-white/[0.07]"}`}
      style={{
        background: req.completed
          ? `linear-gradient(115deg, ${meta.color}26, ${meta.color}0A 60%, transparent)`
          : "rgba(255,255,255,0.03)",
      }}
    >
      <span
        aria-hidden
        className="shrink-0 grid place-items-center w-[18px] h-[18px] rounded-md border
          motion-safe:transition-all motion-safe:duration-200"
        style={{
          borderColor: req.completed ? meta.color : "rgba(255,255,255,0.18)",
          background: req.completed ? meta.color : "transparent",
          color: "#0B0B14",
        }}
      >
        <CheckIcon className={`w-2.5 h-2.5 motion-safe:transition-all motion-safe:duration-200
          ${req.completed ? "opacity-100 scale-100" : "opacity-0 scale-50"}`} />
      </span>

      <span className={`text-[12px] font-semibold leading-none whitespace-nowrap
        motion-safe:transition-colors
        ${req.completed ? "text-zinc-500 line-through decoration-white/25" : "text-zinc-200"}`}>
        {req.label}
      </span>
    </button>
  );
}

function Group({ group, onToggle, pending }: {
  group: WeekPlan["groups"][number];
  onToggle: (r: Requirement) => void;
  pending: Set<string>;
}) {
  const meta = DISCIPLINE[group.discipline];
  const Icon = DISCIPLINE_ICON[group.discipline];
  const complete = group.done >= group.target;

  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 py-2.5">
      <div className="flex items-center gap-2 sm:w-[104px] shrink-0">
        <Icon className="w-4 h-4 shrink-0" style={{ color: meta.color, opacity: complete ? 1 : 0.6 }} />
        <span className="text-[11px] font-bold uppercase tracking-[0.09em] text-zinc-300">
          {meta.name}
        </span>
        <span className={`ml-auto sm:ml-0 text-[11px] mono tabular-nums
          ${complete ? "text-zinc-200" : "text-zinc-600"}`}>
          {group.done}/{group.target}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {group.requirements.map((r) => (
          <RequirementChip key={r.key} req={r} onToggle={onToggle} busy={pending.has(r.key)} />
        ))}
      </div>
    </div>
  );
}

function ProgressRing({ done, total }: { done: number; total: number }) {
  const size = 92;
  const stroke = 7;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = total ? done / total : 0;
  const color = done >= total ? "#34D399" : done > 0 ? "#22D3EE" : "#4B5563";

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90 overflow-visible" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="rgba(255,255,255,0.055)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`}
          className="motion-safe:transition-all motion-safe:duration-500"
          style={{ filter: done > 0 ? `drop-shadow(0 0 5px ${color}55)` : undefined }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[26px] font-black mono leading-none tabular-nums" style={{ color }}>
          {done}
        </span>
        <span className="text-[9px] uppercase tracking-wider text-zinc-600 leading-none mt-1">
          of {total}
        </span>
      </div>
    </div>
  );
}

export default function WeeklyChart() {
  const [week, setWeek] = useState<WeekPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<Set<string>>(new Set());

  const load = useCallback(async () => {
    try {
      setWeek(await api.getWeek());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the week");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = useCallback(async (req: Requirement) => {
    setPending((p) => new Set(p).add(req.key));
    try {
      // The API returns the recomputed week, so the ring and the counts stay
      // consistent with the chips without a second request.
      setWeek(req.completed
        ? await api.uncompleteSession(req.key)
        : await api.completeSession(req.key));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save that");
    } finally {
      setPending((p) => {
        const next = new Set(p);
        next.delete(req.key);
        return next;
      });
    }
  }, []);

  if (error && !week) {
    return (
      <div className="p-4 rounded-2xl border border-white/6 text-sm text-zinc-500"
        style={{ background: "rgba(255,255,255,0.025)" }}>
        {error}
      </div>
    );
  }

  if (!week) {
    return (
      <div className="rounded-2xl border border-white/6 h-64 motion-safe:animate-pulse"
        style={{ background: "rgba(255,255,255,0.025)" }} />
    );
  }

  const { progress } = week;
  const restDone = (progress.by_discipline.rest ?? 0) > 0;

  return (
    <section
      aria-label="This week's training requirements"
      className="relative rounded-2xl border border-white/[0.07] overflow-hidden backdrop-blur-xl"
      style={{
        background: "linear-gradient(160deg, rgba(255,255,255,0.045), rgba(255,255,255,0.018))",
        boxShadow: "0 1px 0 0 rgba(255,255,255,0.05) inset, 0 18px 40px -22px rgba(0,0,0,0.8)",
      }}
    >
      <div className="flex items-center gap-5 p-4 border-b border-white/[0.06]">
        <ProgressRing done={progress.training_completed} total={progress.training_total} />

        <div className="min-w-0">
          <h2 className="text-sm font-bold text-zinc-100 tracking-tight">This Week</h2>
          <p className="text-[11px] text-zinc-500 mt-0.5">
            {formatRange(week.week_start, week.week_end)} · Monday to Sunday
          </p>
          <p className="text-[11px] text-zinc-600 mt-1.5 leading-snug">
            {progress.training_completed === 0
              ? "Nothing logged yet. Tick each session as you finish it."
              : progress.training_completed >= progress.training_total
              ? "Full week done."
              : `${progress.training_total - progress.training_completed} sessions left.`}
            {restDone && " Rest taken."}
          </p>
        </div>
      </div>

      {error && (
        <p role="status" className="px-4 py-2 text-[11px] text-amber-400/90 border-b border-white/[0.06]">
          {error}
        </p>
      )}

      <div className="px-4 py-1 divide-y divide-white/[0.05]">
        {week.groups.map((g) => (
          <Group key={g.discipline} group={g} onToggle={toggle} pending={pending} />
        ))}
      </div>
    </section>
  );
}
