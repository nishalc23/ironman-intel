import { useState } from "react";
import { MISTAKES } from "../data/plan";

export default function Warnings() {
  const [dismissed, setDismissed] = useState<number[]>([]);

  const visible = MISTAKES.filter(m => !dismissed.includes(m.num));

  return (
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">
          ⚠️ Top 10 Race-Killing Mistakes
        </h2>
        {dismissed.length > 0 && (
          <button
            onClick={() => setDismissed([])}
            className="text-[10px] text-zinc-500 hover:text-white transition-colors"
          >
            Reset ({dismissed.length} hidden)
          </button>
        )}
      </div>

      {visible.length === 0 ? (
        <p className="text-xs text-zinc-500 text-center py-4">All warnings dismissed. You know what you're doing. 🏁</p>
      ) : (
        <div className="space-y-2">
          {visible.map(m => (
            <div
              key={m.num}
              className="flex gap-3 items-start bg-red-500/5 border border-red-500/20 rounded-xl px-3 py-2.5 group"
            >
              <span className="text-[11px] font-black text-red-400 w-5 shrink-0 mt-0.5">#{m.num}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-white">{m.title}</p>
                <p className="text-[11px] text-zinc-400 mt-0.5 leading-relaxed">{m.fix}</p>
              </div>
              <button
                onClick={() => setDismissed(d => [...d, m.num])}
                className="text-zinc-700 hover:text-zinc-400 text-xs opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              >
                ✓
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
