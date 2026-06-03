import { useState, useMemo } from "react";
import { RACE_SPLITS } from "../data/plan";

function timeToSeconds(h: number, m: number, s: number) {
  return h * 3600 + m * 60 + s;
}

function secondsToDisplay(total: number): string {
  if (total < 0) return "—";
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

interface Split {
  label: string;
  color: string;
  icon: string;
  defaultMins: number;
  defaultSecs: number;
  paceHint: string;
}

const SPLITS: Split[] = [
  { label: "Swim 1.2 mi",  color: "text-blue-400",   icon: "🏊", defaultMins: 36, defaultSecs: 0,  paceHint: "Target: 1:52/100m" },
  { label: "T1",           color: "text-zinc-300",   icon: "⏱", defaultMins: 4,  defaultSecs: 0,  paceHint: "Practice transitions" },
  { label: "Bike 56 mi",   color: "text-green-400",  icon: "🚴", defaultMins: 175,defaultSecs: 0,  paceHint: "Target: 19.2 mph avg" },
  { label: "T2",           color: "text-zinc-300",   icon: "⏱", defaultMins: 2,  defaultSecs: 0,  paceHint: "Quick change" },
  { label: "Run 13.1 mi",  color: "text-orange-400", icon: "🏃", defaultMins: 118,defaultSecs: 0,  paceHint: "Target: 9:00/mile" },
];

export default function SplitCalculator() {
  const [mins, setMins] = useState(SPLITS.map(s => s.defaultMins));
  const [secs, setSecs] = useState(SPLITS.map(s => s.defaultSecs));

  const totalSeconds = useMemo(
    () => mins.reduce((sum, m, i) => sum + timeToSeconds(0, m, secs[i]), 0),
    [mins, secs]
  );

  const underFive = totalSeconds < 5 * 3600;
  const diff = 5 * 3600 - totalSeconds;

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">Split Calculator</h2>
        <div className={`text-xs font-bold px-3 py-1 rounded-full border ${
          underFive
            ? "bg-green-500/15 border-green-500/30 text-green-400"
            : "bg-red-500/15 border-red-500/30 text-red-400"
        }`}>
          {underFive ? `✓ Sub-5 by ${secondsToDisplay(Math.abs(diff))}` : `✗ Over by ${secondsToDisplay(Math.abs(diff))}`}
        </div>
      </div>

      <div className="space-y-3">
        {SPLITS.map((split, i) => (
          <div key={i} className="flex items-center gap-3">
            <span className="text-base shrink-0">{split.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-1">
                <span className={`text-xs font-medium ${split.color}`}>{split.label}</span>
                <span className="text-[10px] text-zinc-600">{split.paceHint}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  min={0}
                  max={599}
                  value={mins[i]}
                  onChange={e => setMins(arr => arr.map((v, j) => j === i ? Math.max(0, +e.target.value) : v))}
                  className="w-14 bg-white/5 border border-white/10 rounded-lg text-white text-xs text-center py-1.5 focus:border-ironman-red outline-none"
                />
                <span className="text-zinc-500 text-xs">min</span>
                <input
                  type="number"
                  min={0}
                  max={59}
                  value={secs[i]}
                  onChange={e => setSecs(arr => arr.map((v, j) => j === i ? Math.min(59, Math.max(0, +e.target.value)) : v))}
                  className="w-12 bg-white/5 border border-white/10 rounded-lg text-white text-xs text-center py-1.5 focus:border-ironman-red outline-none"
                />
                <span className="text-zinc-500 text-xs">sec</span>
                <span className={`ml-auto text-sm font-mono font-bold ${split.color}`}>
                  {secondsToDisplay(timeToSeconds(0, mins[i], secs[i]))}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Total */}
      <div className={`rounded-xl border px-4 py-3 ${underFive ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5"}`}>
        <div className="flex items-center justify-between">
          <span className="text-xs text-zinc-400">Total Finish Time</span>
          <span className={`text-2xl font-black font-mono ${underFive ? "text-green-400" : "text-red-400"}`}>
            {secondsToDisplay(totalSeconds)}
          </span>
        </div>
        {!underFive && (
          <p className="text-xs text-red-400 mt-1.5">
            Adjust splits — total must be under 5:00:00 to accept this plan.
          </p>
        )}
      </div>

      {/* Target reference */}
      <div className="bg-white/3 rounded-xl p-3 space-y-1.5">
        <p className="text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Your Target Splits</p>
        {[
          { label: "Swim", value: RACE_SPLITS.swim.target, note: RACE_SPLITS.swim.pace, color: "text-blue-400" },
          { label: "T1",   value: RACE_SPLITS.t1.target,   note: "",                    color: "text-zinc-400" },
          { label: "Bike", value: RACE_SPLITS.bike.target, note: RACE_SPLITS.bike.pace, color: "text-green-400" },
          { label: "T2",   value: RACE_SPLITS.t2.target,   note: "",                    color: "text-zinc-400" },
          { label: "Run",  value: RACE_SPLITS.run.target,  note: RACE_SPLITS.run.pace,  color: "text-orange-400" },
        ].map(r => (
          <div key={r.label} className="flex items-center gap-2">
            <span className={`text-xs font-mono font-bold w-14 ${r.color}`}>{r.value}</span>
            <span className="text-[11px] text-zinc-500">{r.label}</span>
            {r.note && <span className="text-[10px] text-zinc-600 ml-auto">{r.note}</span>}
          </div>
        ))}
        <div className="border-t border-white/10 pt-1.5 flex items-center gap-2">
          <span className="text-sm font-black font-mono text-white w-14">4:55:00</span>
          <span className="text-xs text-zinc-400">Total target</span>
          <span className="text-[10px] text-green-400 ml-auto">✓ 5 min buffer</span>
        </div>
      </div>
    </div>
  );
}
