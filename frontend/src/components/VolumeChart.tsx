import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import type { DailyMetric } from "../api/client";

interface Props {
  history: DailyMetric[];
}

function weekLabel(dateStr: string) {
  const d = new Date(dateStr);
  return `${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}

function rollupByWeek(history: DailyMetric[]) {
  const weeks: Record<string, { week: string; Swim: number; Bike: number; Run: number }> = {};

  history.forEach((d) => {
    const date = new Date(d.date);
    const dayOfWeek = date.getDay(); // 0=Sun
    const monday = new Date(date);
    monday.setDate(date.getDate() - ((dayOfWeek + 6) % 7));
    const key = monday.toISOString().slice(0, 10);

    if (!weeks[key]) {
      weeks[key] = { week: weekLabel(key), Swim: 0, Bike: 0, Run: 0 };
    }
    weeks[key].Swim += d.swim_km * 1000;            // meters
    weeks[key].Bike += d.bike_km * 0.621371;        // miles
    weeks[key].Run  += d.run_km  * 0.621371;        // miles
  });

  return Object.values(weeks).map((w) => ({
    ...w,
    Swim: Math.round(w.Swim * 10) / 10,
    Bike: Math.round(w.Bike * 10) / 10,
    Run:  Math.round(w.Run  * 10) / 10,
  }));
}

export default function VolumeChart({ history }: Props) {
  // Show only the last 8 weeks so the current week is clearly visible
  const data = rollupByWeek(history).slice(-4);

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider mb-4">
        Weekly Volume · Swim (m) · Run/Bike (mi)
      </h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" />
          <XAxis dataKey="week" tick={{ fill: "#6B7280", fontSize: 11 }} />
          <YAxis tick={{ fill: "#6B7280", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: 8 }}
            labelStyle={{ color: "#F3F4F6" }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#9CA3AF" }} />
          <Bar dataKey="Swim" fill="#38BDF8" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Bike" fill="#A78BFA" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Run"  fill="#F97316" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
