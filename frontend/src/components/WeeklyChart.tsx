import { useCallback, useEffect, useRef, useState } from "react";
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
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-white/50 " +
  "focus-visible:ring-offset-2 focus-visible:ring-offset-[#0F172A]";

function formatRange(startISO: string, endISO: string) {
  // ISO dates parse as UTC, so format as UTC too. Local time would shift the
  // label back a day for anyone west of Greenwich.
  const fmt = (iso: string) =>
    new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, {
      month: "short", day: "numeric", timeZone: "UTC",
    });
  return `${fmt(startISO)} – ${fmt(endISO)}`;
}

function Chip({ req, onToggle, busy, justDone }: {
  req: Requirement;
  onToggle: (r: Requirement) => void;
  busy: boolean;
  justDone: boolean;
}) {
  const meta = DISCIPLINE[req.discipline];

  return (
    <button
      type="button"
      onClick={() => onToggle(req)}
      disabled={busy}
      aria-pressed={req.completed}
      aria-label={`${meta.name} ${req.label}${req.completed ? ", done" : ""}`}
      className={`group relative flex items-center gap-2 pl-2 pr-3.5 py-2 rounded-xl border
        overflow-hidden backdrop-blur-md cursor-pointer ${FOCUS} ${justDone ? "pop" : ""}
        motion-safe:transition-[transform,border-color,background] motion-safe:duration-200
        motion-safe:hover:-translate-y-0.5 motion-safe:active:translate-y-0
        motion-safe:active:scale-[0.96] ${busy ? "opacity-50" : ""}`}
      style={{
        borderColor: req.completed ? `${meta.color}66` : "rgba(255,255,255,0.14)",
        background: req.completed
          ? `linear-gradient(120deg, ${meta.color}33, ${meta.color}0D 60%, rgba(255,255,255,0.04))`
          : "rgba(255,255,255,0.06)",
        boxShadow: req.completed
          ? `inset 0 1px 0 0 rgba(255,255,255,0.2), 0 6px 18px -10px ${meta.color}`
          : "inset 0 1px 0 0 rgba(255,255,255,0.16)",
      }}
    >
      {/* Light sweeping across the chip on hover, so it reads as glass. */}
      <span aria-hidden
        className="absolute inset-0 opacity-0 group-hover:opacity-100 motion-safe:transition-opacity duration-300"
        style={{ background: "linear-gradient(115deg, transparent 30%, rgba(255,255,255,0.13) 50%, transparent 70%)" }} />

      <span aria-hidden className="relative shrink-0 grid place-items-center w-[19px] h-[19px]">
        {/* A ring of light thrown off the moment it lands. */}
        {justDone && (
          <span className="burst absolute inset-0 rounded-full"
            style={{ boxShadow: `0 0 0 2px ${meta.color}` }} />
        )}
        <span className="grid place-items-center w-full h-full rounded-md border
            motion-safe:transition-all motion-safe:duration-200"
          style={{
            borderColor: req.completed ? meta.color : "rgba(255,255,255,0.28)",
            background: req.completed ? meta.color : "rgba(255,255,255,0.04)",
            boxShadow: req.completed ? `0 0 12px ${meta.color}99` : "none",
            color: "#0B1020",
          }}>
          <CheckIcon className={`w-2.5 h-2.5 ${justDone ? "stamp" : ""}
            ${req.completed ? "opacity-100" : "opacity-0 scale-50"}
            motion-safe:transition-all motion-safe:duration-200`} />
        </span>
      </span>

      <span className={`relative text-[12px] font-semibold leading-none whitespace-nowrap
        motion-safe:transition-colors
        ${req.completed ? "text-paper-dim line-through decoration-white/30" : "text-paper"}`}>
        {req.label}
      </span>
    </button>
  );
}

function Group({ group, onToggle, pending, justDone, celebrating }: {
  group: WeekPlan["groups"][number];
  onToggle: (r: Requirement) => void;
  pending: Set<string>;
  justDone: string | null;
  celebrating: boolean;
}) {
  const meta = DISCIPLINE[group.discipline];
  const Icon = DISCIPLINE_ICON[group.discipline];
  const complete = group.done >= group.target;

  return (
    <div className="relative flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4 py-3 overflow-hidden">
      {/* Light sweeps the row when the discipline hits its weekly target. */}
      {celebrating && (
        <span aria-hidden className="sweep absolute inset-y-0 w-1/3 pointer-events-none"
          style={{ background: `linear-gradient(90deg, transparent, ${meta.color}40, transparent)` }} />
      )}

      <div className="flex items-center gap-2.5 sm:w-[118px] shrink-0">
        <Icon className="w-[18px] h-[18px] shrink-0 motion-safe:transition-all motion-safe:duration-300"
          style={{
            color: meta.color,
            opacity: complete ? 1 : 0.55,
            filter: complete ? `drop-shadow(0 0 6px ${meta.color}AA)` : "none",
          }} />
        <span className="text-[11px] font-bold uppercase tracking-[0.11em] text-paper">
          {meta.name}
        </span>
        <span className={`ml-auto sm:ml-0 text-[11px] mono tabular-nums motion-safe:transition-colors
          ${complete ? "" : "text-paper-dim"}`}
          style={complete ? { color: meta.color } : undefined}>
          {group.done}/{group.target}
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {group.requirements.map((r) => (
          <Chip key={r.key} req={r} onToggle={onToggle}
            busy={pending.has(r.key)} justDone={justDone === r.key} />
        ))}
      </div>
    </div>
  );
}

function ProgressRing({ done, total, celebrating }: {
  done: number; total: number; celebrating: boolean;
}) {
  const size = 104;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = total ? done / total : 0;
  const finished = done >= total && total > 0;
  const color = finished ? "#22C55E" : done > 0 ? "#22D3EE" : "#475569";

  return (
    <div className={`relative shrink-0 ${celebrating ? "triumph" : ""}`}
      style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90 overflow-visible" aria-hidden>
        <defs>
          <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={color} />
            <stop offset="100%" stopColor={finished ? "#A78BFA" : "#0080FF"} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="rgba(255,255,255,0.08)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="url(#ringGrad)" strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`}
          className="motion-safe:transition-all motion-safe:duration-700"
          style={{
            transitionTimingFunction: "cubic-bezier(0.34, 1.4, 0.64, 1)",
            filter: done > 0 ? `drop-shadow(0 0 8px ${color}AA)` : undefined,
          }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[30px] font-black mono leading-none tabular-nums"
          style={{ color, textShadow: done > 0 ? `0 0 18px ${color}77` : undefined }}>
          {done}
        </span>
        <span className="text-[9px] uppercase tracking-[0.16em] text-paper-dim leading-none mt-1">
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
  const [justDone, setJustDone] = useState<string | null>(null);
  const [celebrating, setCelebrating] = useState<string | null>(null);
  const [weekDone, setWeekDone] = useState(false);
  const prev = useRef<WeekPlan | null>(null);

  const load = useCallback(async () => {
    try {
      const w = await api.getWeek();
      setWeek(w);
      prev.current = w;
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the week");
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const toggle = useCallback(async (req: Requirement) => {
    setPending((p) => new Set(p).add(req.key));
    try {
      // The API returns the recomputed week, so the ring, counts and chips
      // stay consistent without a second request.
      const updated = req.completed
        ? await api.uncompleteSession(req.key)
        : await api.completeSession(req.key);

      if (!req.completed) {
        setJustDone(req.key);
        window.setTimeout(() => setJustDone(null), 700);

        // Reward the milestone, not just the tap: a discipline finishing its
        // weekly target, and the week itself being complete.
        const before = prev.current?.groups.find((g) => g.discipline === req.discipline);
        const after = updated.groups.find((g) => g.discipline === req.discipline);
        if (after && before && after.done >= after.target && before.done < before.target) {
          setCelebrating(req.discipline);
          window.setTimeout(() => setCelebrating(null), 1000);
        }
        const finishedWeek =
          updated.progress.training_completed >= updated.progress.training_total &&
          (prev.current?.progress.training_completed ?? 0) < updated.progress.training_total;
        if (finishedWeek) {
          setWeekDone(true);
          window.setTimeout(() => setWeekDone(false), 1400);
        }
      }

      setWeek(updated);
      prev.current = updated;
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
    return <div className="glass rounded-2xl p-4 text-sm text-paper-muted">{error}</div>;
  }

  if (!week) {
    return <div className="glass rounded-2xl h-64 motion-safe:animate-pulse" />;
  }

  const { progress } = week;
  const left = progress.training_total - progress.training_completed;
  const restDone = (progress.by_discipline.rest ?? 0) > 0;

  return (
    <section aria-label="This week's training requirements"
      className={`glass glass-raised rounded-2xl overflow-hidden ${weekDone ? "triumph" : ""}`}>

      <div className="relative flex items-center gap-5 p-5 border-b border-white/10">
        <ProgressRing done={progress.training_completed}
          total={progress.training_total} celebrating={weekDone} />

        <div className="min-w-0">
          <h2 className="text-base font-bold text-paper tracking-tight">This Week</h2>
          <p className="text-[11px] text-paper-muted mt-1 mono">
            {formatRange(week.week_start, week.week_end)} · Mon to Sun
          </p>
          <p className="text-[12px] text-paper-muted mt-2 leading-snug">
            {left === progress.training_total
              ? "Nothing logged yet. Tick each session as you finish it."
              : left === 0
              ? "Full week done."
              : `${left} session${left === 1 ? "" : "s"} to go.`}
            {restDone && " Rest taken."}
          </p>
        </div>
      </div>

      {error && (
        <p role="status" className="px-5 py-2 text-[11px] text-danger border-b border-white/10">
          {error}
        </p>
      )}

      <div className="px-5 py-1 divide-y divide-white/[0.07]">
        {week.groups.map((g) => (
          <Group key={g.discipline} group={g} onToggle={toggle} pending={pending}
            justDone={justDone} celebrating={celebrating === g.discipline} />
        ))}
      </div>
    </section>
  );
}
