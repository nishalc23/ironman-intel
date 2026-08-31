import type { SleepSummary } from "../api/client";

// Fallback labels only. The real headline comes from the API, which knows
// which signal is limiting and says so.
const SIGNAL_CONFIG = {
  green:  { color: "#34D399", label: "Ready to train hard",   bg: "rgba(52,211,153,0.1)",  border: "rgba(52,211,153,0.25)" },
  yellow: { color: "#FBBF24", label: "Train, but keep it easy", bg: "rgba(251,191,36,0.1)",  border: "rgba(251,191,36,0.25)" },
  red:    { color: "#F87171", label: "Recover today",         bg: "rgba(248,113,113,0.1)", border: "rgba(248,113,113,0.25)" },
};

function ScoreRing({ score, color, size = 72 }: { score: number; color: string; size?: number }) {
  const r = (size / 2) - 6;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  return (
    <svg width={size} height={size} className="shrink-0">
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={5} />
      <circle
        cx={size/2} cy={size/2} r={r} fill="none"
        stroke={color} strokeWidth={5}
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ filter: `drop-shadow(0 0 6px ${color}80)` }}
      />
      <text x={size/2} y={size/2 + 5} textAnchor="middle" fill="white" fontSize="16" fontWeight="bold" fontFamily="monospace">
        {score}
      </text>
    </svg>
  );
}

function MiniBar({ label, hours, maxHours, color }: { label: string; hours: number | null; maxHours: number; color: string }) {
  if (!hours) return null;
  const pct = Math.min(100, (hours / maxHours) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-zinc-600 w-10 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[11px] mono text-zinc-400 w-8 text-right">{hours}h</span>
    </div>
  );
}

export default function SleepCard({ data }: { data: SleepSummary | null }) {
  const loading = data === null;

  if (loading) {
    return (
      <div className="rounded-2xl border p-5 flex items-center justify-center h-40"
        style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.02)" }}>
        <div className="w-5 h-5 border-2 border-ironman-red border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!data?.today && !data?.last_7_days?.length) {
    return (
      <div className="rounded-2xl border p-5 space-y-2"
        style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.02)" }}>
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Sleep & Readiness</p>
        <p className="text-xs text-zinc-600">No sleep data yet — hit ⟳ Sync to pull from Garmin.</p>
      </div>
    );
  }

  const today = data.today;
  const signal = today?.readiness_signal ?? "yellow";
  const cfg = SIGNAL_CONFIG[signal] ?? SIGNAL_CONFIG.yellow;
  // The ring shows readiness, not the raw sleep score. Painting a sleep score
  // of 68 in the readiness colour is what made a five hour night look green.
  const sleepScore = today?.sleep_score ?? data.avg_score_7d ?? 0;
  const readiness = today?.readiness_score ?? sleepScore;
  const headline = today?.readiness_headline ?? cfg.label;
  const hours = today?.duration_hours ?? null;

  const trendIcon = data.trend === "improving" ? "↑" : data.trend === "declining" ? "↓" : "→";
  const trendColor = data.trend === "improving" ? "#34D399" : data.trend === "declining" ? "#F87171" : "#6B7280";

  return (
    <div className="rounded-2xl border p-5 space-y-4"
      style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.02)" }}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Sleep & Readiness</p>
        <span className="text-[10px] mono" style={{ color: trendColor }}>{trendIcon} {data.trend}</span>
      </div>

      {/* Readiness signal + score ring */}
      <div className="flex items-center gap-4 px-3 py-3 rounded-xl border"
        style={{ background: cfg.bg, borderColor: cfg.border }}>
        <ScoreRing score={Math.round(readiness)} color={cfg.color} />
        <div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ background: cfg.color, boxShadow: `0 0 6px ${cfg.color}` }} />
            <p className="text-xs font-bold text-white">{headline}</p>
          </div>
          <p className="text-[11px] text-zinc-500 mt-1">
            Readiness {Math.round(readiness)}/100 · sleep score {Math.round(sleepScore)}
            {hours != null && (
              <span style={{ color: hours < 6 ? "#F87171" : undefined }}>
                {" "}· {hours.toFixed(1)}h
              </span>
            )}
          </p>
          <div className="flex gap-3 mt-1.5">
            {today?.hrv_nightly_avg && (
              <span className="text-[11px] mono text-zinc-400">HRV <span className="text-white font-bold">{Math.round(today.hrv_nightly_avg)}ms</span></span>
            )}
            {today?.resting_hr && (
              <span className="text-[11px] mono text-zinc-400">RHR <span className="text-white font-bold">{today.resting_hr}bpm</span></span>
            )}
            {today?.duration_hours && (
              <span className="text-[11px] mono text-zinc-400"><span className="text-white font-bold">{today.duration_hours}h</span> sleep</span>
            )}
          </div>
        </div>
      </div>

      {/* Sleep stages */}
      {today && (
        <div className="space-y-1.5">
          <MiniBar label="Deep"  hours={today.deep_sleep_hours} maxHours={3} color="#A78BFA" />
          <MiniBar label="REM"   hours={today.rem_sleep_hours}  maxHours={3} color="#38BDF8" />
        </div>
      )}

      {/* 7-day score strip */}
      {data.last_7_days.length > 1 && (
        <div>
          <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Last 7 nights</p>
          <div className="flex gap-1 items-end h-10">
            {[...data.last_7_days].reverse().map((entry, i) => {
              const s = entry.sleep_score ?? 0;
              const sig = entry.readiness_signal ?? "yellow";
              const c = SIGNAL_CONFIG[sig]?.color ?? "#6B7280";
              const h = Math.max(4, (s / 100) * 40);
              return (
                <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                  <div className="w-full rounded-sm" style={{ height: h, background: c, opacity: 0.8 }} />
                  <span className="text-[9px] mono text-zinc-700">
                    {new Date(entry.date).toLocaleDateString("en-US", { weekday: "narrow" })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Avg line */}
      <div className="flex justify-between text-[10px] text-zinc-600">
        <span>7-day avg score: <span className="text-zinc-400 font-medium">{data.avg_score_7d ?? "—"}</span></span>
        {data.avg_hrv_7d && <span>avg HRV: <span className="text-zinc-400 font-medium">{data.avg_hrv_7d}ms</span></span>}
      </div>
    </div>
  );
}
