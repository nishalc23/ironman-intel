import { NUTRITION, type NutritionLoad } from "../data/plan";

function MacroBar({ label, grams, max, color }: { label: string; grams: number; max: number; color: string }) {
  const pct = Math.min(100, (grams / max) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-zinc-500 w-12 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[11px] text-zinc-300 w-10 text-right shrink-0">{grams}g</span>
    </div>
  );
}

export default function NutritionPanel({ load, compact = false }: {
  load: NutritionLoad;
  compact?: boolean;
}) {
  const n = NUTRITION[load];

  if (compact) {
    return (
      <div className="bg-white/3 border border-white/5 rounded-lg px-2.5 py-2 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-zinc-500">{n.label}</span>
          <span className="text-[11px] font-semibold text-white">{n.calories} cal</span>
        </div>
        <MacroBar label="Carbs" grams={n.carbs}   max={650} color="bg-yellow-400" />
        <MacroBar label="Protein" grams={n.protein} max={200} color="bg-blue-400" />
        <MacroBar label="Fat"   grams={n.fat}     max={100} color="bg-orange-400" />
      </div>
    );
  }

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">Daily Nutrition</h2>
        <span className="text-xs text-zinc-400 border border-ironman-border px-2 py-1 rounded-lg">{n.label}</span>
      </div>

      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Calories", value: n.calories, unit: "cal", color: "text-white" },
          { label: "Carbs", value: n.carbs, unit: "g", color: "text-yellow-400" },
          { label: "Protein", value: n.protein, unit: "g", color: "text-blue-400" },
          { label: "Fat", value: n.fat, unit: "g", color: "text-orange-400" },
        ].map(m => (
          <div key={m.label} className="bg-white/3 rounded-xl p-3 text-center">
            <p className={`text-xl font-bold ${m.color}`}>{m.value}</p>
            <p className="text-[10px] text-zinc-500">{m.unit}</p>
            <p className="text-[10px] text-zinc-500 mt-0.5">{m.label}</p>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <MacroBar label="Carbs"   grams={n.carbs}   max={650} color="bg-yellow-400" />
        <MacroBar label="Protein" grams={n.protein} max={200} color="bg-blue-400" />
        <MacroBar label="Fat"     grams={n.fat}     max={120} color="bg-orange-400" />
      </div>

      {load === "carb_load" && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl px-3 py-2.5">
          <p className="text-xs font-semibold text-yellow-400">⚡ Carb Load Protocol</p>
          <p className="text-[11px] text-zinc-400 mt-1">
            8–10g carbs per kg bodyweight (72.7 kg) = 580–730g/day. White rice, pasta, bread, bananas — easy to digest.
            Cut ALL fiber and fat. No new foods.
          </p>
        </div>
      )}

      {load === "race_morning" && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-xl px-3 py-2.5">
          <p className="text-xs font-semibold text-green-400">🏁 Race Morning Protocol</p>
          <p className="text-[11px] text-zinc-400 mt-1">
            2.5–3 hrs before gun: oatmeal + banana + sports drink. 16–24 oz water. 500mg sodium.
            45 min before: 200mg caffeine + 1 gel. Nothing new.
          </p>
        </div>
      )}
    </div>
  );
}
