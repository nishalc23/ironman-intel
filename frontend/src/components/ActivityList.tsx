import type { ActivityRecord } from "../api/client";

interface Props {
  activities: ActivityRecord[];
}

const DISCIPLINE_EMOJI: Record<string, string> = {
  swimming: "🏊",
  cycling:  "🚴",
  running:  "🏃",
  other:    "⚡",
};

function fmtDuration(s: number) {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

function fmtDist(meters: number | null, discipline: string) {
  if (!meters) return "—";
  if (discipline === "swimming") {
    return `${Math.round(meters)} m`;
  }
  // run + bike in miles
  const miles = meters / 1609.34;
  return `${miles.toFixed(1)} mi`;
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", weekday: "short",
  });
}

export default function ActivityList({ activities }: Props) {
  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider mb-4">
        Recent Activities
      </h2>
      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {activities.length === 0 && (
          <p className="text-ironman-muted text-sm">No activities yet — run a sync.</p>
        )}
        {activities.map((a) => (
          <div
            key={a.id}
            className="flex items-center justify-between bg-[#111] border border-[#2A2A2A] rounded-xl px-4 py-3"
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">{DISCIPLINE_EMOJI[a.discipline] ?? "⚡"}</span>
              <div>
                <p className="text-sm font-medium capitalize">{a.discipline}</p>
                <p className="text-xs text-ironman-muted">{fmtDate(a.start_time)}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium">{fmtDist(a.distance_meters, a.discipline)}</p>
              <p className="text-xs text-ironman-muted">
                {fmtDuration(a.duration_seconds)}
                {a.avg_heart_rate ? ` · ${a.avg_heart_rate} bpm` : ""}
                {a.tss ? ` · TSS ${Math.round(a.tss)}` : ""}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
