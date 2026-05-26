import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "../api/client";

interface Props {
  riskLevel: "low" | "moderate" | "high";
}

const RISK_COLORS = {
  low:      "text-green-400 bg-green-400/10 border-green-400/30",
  moderate: "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  high:     "text-red-400 bg-red-400/10 border-red-400/30",
};

const RISK_LABELS = {
  low:      "Form: Good",
  moderate: "Accumulating Fatigue",
  high:     "Overtraining Risk",
};

export default function TrainingPlan({ riskLevel }: Props) {
  const [plan, setPlan] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gymToday, setGymToday] = useState(true);

  async function fetchPlan() {
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const data = await api.getTodayPlan(gymToday);
      setPlan(data.plan);
    } catch {
      setError("Could not generate plan — make sure the API is running and ANTHROPIC_API_KEY is set.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">
          Today's Training Plan
        </h2>
        <span className={`text-xs font-medium px-3 py-1 rounded-full border ${RISK_COLORS[riskLevel]}`}>
          {RISK_LABELS[riskLevel]}
        </span>
      </div>

      {!plan && !loading && (
        <div className="flex flex-col items-center justify-center py-10 gap-4">
          <p className="text-ironman-muted text-sm text-center max-w-xs">
            Claude will read your Garmin data and fatigue score, then write a personalized plan for today.
          </p>
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <div
              onClick={() => setGymToday(g => !g)}
              className={`w-9 h-5 rounded-full transition-colors relative ${gymToday ? "bg-ironman-red" : "bg-ironman-border"}`}
            >
              <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${gymToday ? "translate-x-4" : "translate-x-0.5"}`} />
            </div>
            <span className="text-xs text-ironman-muted">Gym today</span>
          </label>
          <button
            onClick={fetchPlan}
            className="bg-ironman-red hover:bg-red-700 text-white text-sm font-semibold px-6 py-2.5 rounded-xl transition-colors"
          >
            Generate Today's Plan
          </button>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12 gap-3">
          <div className="w-5 h-5 border-2 border-ironman-red border-t-transparent rounded-full animate-spin" />
          <span className="text-ironman-muted text-sm">Claude is analyzing your training data…</span>
        </div>
      )}

      {error && (
        <p className="text-red-400 text-sm bg-red-400/10 border border-red-400/30 rounded-xl px-4 py-3">
          {error}
        </p>
      )}

      {plan && !loading && (
        <div>
          <div className="prose prose-invert prose-sm max-w-none
            [&_h2]:text-base [&_h2]:font-bold [&_h2]:text-white [&_h2]:mt-4 [&_h2]:mb-2
            [&_strong]:text-white
            [&_p]:text-gray-300 [&_p]:leading-relaxed
            [&_ul]:text-gray-300 [&_li]:mt-1
            [&_li::marker]:text-ironman-red">
            <ReactMarkdown>{plan}</ReactMarkdown>
          </div>
          <div className="mt-4 flex items-center gap-4">
            <button
              onClick={fetchPlan}
              className="text-xs text-ironman-muted hover:text-white transition-colors underline underline-offset-2"
            >
              Regenerate
            </button>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <div
                onClick={() => setGymToday(g => !g)}
                className={`w-9 h-5 rounded-full transition-colors relative ${gymToday ? "bg-ironman-red" : "bg-ironman-border"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${gymToday ? "translate-x-4" : "translate-x-0.5"}`} />
              </div>
              <span className="text-xs text-ironman-muted">Gym today</span>
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
