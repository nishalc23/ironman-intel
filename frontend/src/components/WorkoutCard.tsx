import { useState } from "react";
import type { WorkoutBlock, Exercise } from "../data/plan";

const SPORT_CONFIG: Record<string, { border: string; glow: string; icon: string; tag: string }> = {
  swim:  { border: "border-cyan-500/25",    glow: "rgba(6,182,212,0.08)",   icon: "🏊", tag: "tag-swim" },
  bike:  { border: "border-emerald-500/25", glow: "rgba(16,185,129,0.08)",  icon: "🚴", tag: "tag-bike" },
  run:   { border: "border-orange-500/25",  glow: "rgba(249,115,22,0.08)",  icon: "🏃", tag: "tag-run" },
  gym:   { border: "border-violet-500/25",  glow: "rgba(139,92,246,0.08)",  icon: "💪", tag: "tag-gym" },
  brick: { border: "border-yellow-500/25",  glow: "rgba(234,179,8,0.08)",   icon: "⚡", tag: "tag-brick" },
  rest:  { border: "border-zinc-700/40",    glow: "rgba(63,63,70,0.15)",    icon: "😴", tag: "tag-rest" },
};

function SetChip({ s }: { s: { reps?: number | string; weight?: string; duration?: string } }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] mono border border-white/8"
      style={{ background: "rgba(255,255,255,0.04)" }}>
      {s.reps !== undefined && <span className="text-zinc-300">{s.reps}</span>}
      {s.weight && <span className="text-zinc-500">@ {s.weight}</span>}
      {s.duration && <span className="text-zinc-300">{s.duration}</span>}
    </span>
  );
}

function ExRow({ ex }: { ex: Exercise }) {
  return (
    <div className="py-2 border-b border-white/4 last:border-0">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-xs font-medium text-zinc-200 leading-snug">{ex.name}</span>
        {ex.note && <span className="text-[10px] text-zinc-600 italic shrink-0 ml-2">{ex.note}</span>}
      </div>
      <div className="flex flex-wrap gap-1">
        {ex.sets.map((s, i) => <SetChip key={i} s={s} />)}
      </div>
    </div>
  );
}

// Tri-specific target chips shown on the card face
const TRI_TARGETS: Record<string, (name: string, detail: string) => { label: string; value: string }[]> = {
  run: (name, detail) => {
    const paceMatch = detail.match(/(\d+:\d+(?:–\d+:\d+)?\/mile)/);
    const hrMatch = detail.match(/(\d+)\s*bpm/);
    const targets = [];
    if (paceMatch) targets.push({ label: "pace", value: paceMatch[1] });
    else if (name.includes("tempo")) targets.push({ label: "pace", value: "8:15–8:30/mi" });
    else targets.push({ label: "pace", value: "9:30–10:00/mi" });
    if (hrMatch) targets.push({ label: "HR", value: `<${hrMatch[1]}` });
    else targets.push({ label: "zone", value: "Z2" });
    return targets;
  },
  swim: (name, detail) => {
    const mMatch = name.match(/(\d+)m/);
    const paceMatch = detail.match(/(\d+:\d+\/100m)/);
    const targets = [];
    if (mMatch) targets.push({ label: "dist", value: mMatch[1] + "m" });
    if (paceMatch) targets.push({ label: "target", value: paceMatch[1] });
    else targets.push({ label: "target", value: "1:52/100m" });
    return targets;
  },
  bike: (_name, detail) => {
    const effortMatch = detail.match(/(\d+(?:\.\d+)?\s*mph)/i);
    const targets = [];
    if (effortMatch) targets.push({ label: "target", value: effortMatch[1] });
    targets.push({ label: "zone", value: detail.includes("Sweet Spot") ? "SS" : "Z2" });
    return targets;
  },
  brick: (_name, detail) => [
    { label: "run pace", value: "9:00–9:15/mi" },
    { label: "gut train", value: "gel/25min" },
  ],
};

export default function WorkoutCard({ block, completed, onToggle }: {
  block: WorkoutBlock;
  completed?: boolean;
  onToggle?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const cfg = SPORT_CONFIG[block.sport] ?? SPORT_CONFIG.rest;
  const isGym = block.sport === "gym";
  const isTri = ["swim", "bike", "run", "brick"].includes(block.sport);
  const targets = isTri ? (TRI_TARGETS[block.sport]?.(block.name, block.detail) ?? []) : [];

  return (
    <div
      className={`rounded-xl border transition-all duration-200 ${cfg.border} ${completed ? "opacity-40" : ""}`}
      style={{ background: cfg.glow }}
    >
      {/* Summary row */}
      <div
        className={`flex items-center gap-3 px-3 py-2.5 select-none ${isGym ? "" : "cursor-pointer"}`}
        onClick={() => !isGym && setExpanded(e => !e)}
      >
        <span className="text-base shrink-0">{cfg.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-white leading-tight line-clamp-2">{block.name}</p>
          <p className="text-[11px] text-zinc-500 mono mt-0.5">{block.duration}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {block.gutTraining && (
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded border border-yellow-500/30 text-yellow-400"
              style={{ background: "rgba(234,179,8,0.08)" }}>Gut</span>
          )}
          {onToggle && (
            <button
              onClick={e => { e.stopPropagation(); onToggle(); }}
              className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                completed ? "border-emerald-500 bg-emerald-500" : "border-zinc-600 hover:border-zinc-300"
              }`}
            >
              {completed && <span className="text-[9px] text-white font-bold">✓</span>}
            </button>
          )}
          {!isGym && <span className="text-zinc-700 text-[10px]">{expanded ? "▲" : "▼"}</span>}
        </div>
      </div>

      {/* Tri target chips — always visible on tri cards */}
      {isTri && targets.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-3 pb-2.5">
          {targets.map((t, i) => (
            <div key={i} className="flex items-center gap-1 px-2 py-0.5 rounded-md border border-white/10"
              style={{ background: "rgba(255,255,255,0.04)" }}>
              <span className="text-[9px] text-zinc-600 uppercase tracking-wider">{t.label}</span>
              <span className="text-[11px] font-bold mono text-white">{t.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Expanded detail — tri only */}
      {!isGym && expanded && (
        <div className="px-3 pb-3 border-t border-white/5 pt-3 space-y-2">
          <p className="text-xs text-zinc-400 leading-relaxed">{block.detail}</p>
          {block.gutTraining && (
            <div className="flex gap-2 items-start px-3 py-2 rounded-lg border border-yellow-500/20"
              style={{ background: "rgba(234,179,8,0.05)" }}>
              <span className="text-yellow-400 text-xs">◈</span>
              <div>
                <p className="text-[11px] font-semibold text-yellow-400">Gut Training Active</p>
                <p className="text-[11px] text-zinc-500 mt-0.5">Gel every 20–25 min. Race products only.</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
