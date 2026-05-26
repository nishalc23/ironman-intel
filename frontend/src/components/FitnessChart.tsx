import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from "recharts";
import type { DailyMetric } from "../api/client";

interface Props {
  history: DailyMetric[];
}

function fmt(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function FitnessChart({ history }: Props) {
  const data = history.map((d) => ({
    date: fmt(d.date),
    CTL: d.ctl != null ? Math.round(d.ctl) : null,
    ATL: d.atl != null ? Math.round(d.atl) : null,
    TSB: d.tsb != null ? Math.round(d.tsb) : null,
  }));

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider mb-4">
        Fitness · Fatigue · Form
      </h2>
      <p className="text-xs text-ironman-muted mb-4">
        <span className="text-blue-400 font-medium">CTL</span> = 42-day fitness &nbsp;·&nbsp;
        <span className="text-orange-400 font-medium">ATL</span> = 7-day fatigue &nbsp;·&nbsp;
        <span className="text-green-400 font-medium">TSB</span> = form (CTL − ATL)
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#6B7280", fontSize: 11 }}
            interval={13}
          />
          <YAxis tick={{ fill: "#6B7280", fontSize: 11 }} />
          <Tooltip
            contentStyle={{ background: "#1A1A1A", border: "1px solid #2A2A2A", borderRadius: 8 }}
            labelStyle={{ color: "#F3F4F6" }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "#9CA3AF" }} />
          <ReferenceLine y={0} stroke="#3A3A3A" strokeDasharray="4 2" />
          <Line type="monotone" dataKey="CTL" stroke="#60A5FA" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="ATL" stroke="#FB923C" strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="TSB" stroke="#4ADE80" strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
