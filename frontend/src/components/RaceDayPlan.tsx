import { RACE_WEEK, RACE_FUELING, SUPPLEMENTS } from "../data/plan";
import WorkoutCard from "./WorkoutCard";

const CARB_LOAD_DAYS = [1, 2, 3]; // Tue, Wed, Thu indices in RACE_WEEK

export default function RaceDayPlan() {
  return (
    <div className="space-y-5">
      {/* Race week header */}
      <div className="card bg-gradient-to-br from-green-900/30 to-emerald-900/20 border-green-500/30">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 bg-green-500/20 rounded-xl flex items-center justify-center text-xl">🏁</div>
          <div>
            <h2 className="text-sm font-bold text-white">Race Week — Dec 1–6, 2026</h2>
            <p className="text-[11px] text-zinc-400">IRONMAN 70.3 La Quinta, California</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "Water temp", value: "~65°F", note: "Wetsuit legal" },
            { label: "Weather", value: "65–75°F", note: "Sunny, dry" },
            { label: "Wind", value: "Possible", note: "Santa Ana winds" },
          ].map(s => (
            <div key={s.label} className="bg-white/5 rounded-lg p-2 text-center">
              <p className="text-xs font-bold text-white">{s.value}</p>
              <p className="text-[10px] text-zinc-500">{s.label}</p>
              <p className="text-[10px] text-green-400">{s.note}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Race week schedule */}
      <div className="card space-y-3">
        <h3 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">Dec 1–6 Schedule</h3>
        {RACE_WEEK.map((day, i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white">{day.dayOfWeek}</span>
              {CARB_LOAD_DAYS.includes(i) && (
                <span className="text-[10px] bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 px-1.5 py-0.5 rounded-full">
                  Carb Load Day {i}
                </span>
              )}
              <span className="text-[11px] text-zinc-500 ml-2">{day.label}</span>
            </div>
            {day.blocks.map((block, j) => (
              <WorkoutCard key={j} block={block} />
            ))}
          </div>
        ))}
      </div>

      {/* Race day fueling */}
      <div className="card space-y-3">
        <h3 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">Race Day Fueling Timeline</h3>
        <div className="relative pl-5 space-y-0">
          <div className="absolute left-2 top-0 bottom-0 w-px bg-ironman-border" />
          {RACE_FUELING.map((item, i) => (
            <div key={i} className="relative pb-4 last:pb-0">
              <div className="absolute left-[-12px] top-0.5 w-3 h-3 rounded-full bg-ironman-red border-2 border-ironman-dark" />
              <div className="bg-[#141414] border border-ironman-border rounded-xl px-3 py-2.5">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[10px] font-mono text-ironman-red font-bold">{item.time}</span>
                  <span className="text-[10px] text-zinc-400">·</span>
                  <span className="text-xs font-semibold text-white">{item.segment}</span>
                </div>
                <p className="text-[11px] text-zinc-400 leading-relaxed">{item.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pacing rules */}
      <div className="card space-y-3">
        <h3 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">Race Day Pacing Rules</h3>
        {[
          { sport: "🏊 Swim", rule: "Start conservative — find feet to draft off. Negative split second half. Sight every 10 strokes at Lake Cahuilla.", color: "text-blue-400" },
          { sport: "🚴 Bike", rule: "Hold 19.2 mph average. Never exceed 19.5 mph — exceeding it blows up your run. GPS watch active. No heroics on hills.", color: "text-green-400" },
          { sport: "🏃 Run", rule: "Miles 1–3 at 9:15/mile (resist the urge to run faster — legs will feel dead). Miles 3–10 at 8:50/mile. Finish strong last 5K.", color: "text-orange-400" },
        ].map(r => (
          <div key={r.sport} className="flex gap-3 bg-white/3 rounded-xl p-3">
            <span className={`text-xs font-bold shrink-0 w-16 ${r.color}`}>{r.sport}</span>
            <p className="text-[11px] text-zinc-400 leading-relaxed">{r.rule}</p>
          </div>
        ))}
      </div>

      {/* Supplements reference */}
      <div className="card space-y-3">
        <h3 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">Supplement Stack</h3>
        <div className="space-y-2">
          {SUPPLEMENTS.map((s, i) => (
            <div key={i} className="flex items-start gap-3 bg-white/3 rounded-xl p-3">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-white">{s.name}</p>
                <p className="text-[11px] text-zinc-400 mt-0.5">{s.note}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-[11px] text-ironman-red font-medium">{s.dose}</p>
                <p className="text-[10px] text-zinc-600">{s.timing}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
