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
  low: "Form: Good", moderate: "Accumulating Fatigue", high: "Overtraining Risk",
};

// Fixed split pairings — Upper→Run, Lower→Bike, Rest→Swim
const SPLITS = [
  { key: "upper", emoji: "💪", label: "Upper",  sub: "chest · back · arms", cardio: "run",  cardioLabel: "+ Run 🏃" },
  { key: "lower", emoji: "🦵", label: "Lower",  sub: "legs · glutes · core", cardio: "bike", cardioLabel: "+ Bike 🚴" },
  { key: "rest",  emoji: "😴", label: "Rest",   sub: "no gym",               cardio: "swim", cardioLabel: "+ Swim 🏊" },
] as const;

export default function TrainingPlan({ riskLevel }: Props) {
  const [gymSplit, setGymSplit] = useState<"upper" | "lower" | "rest" | null>(null);
  const [plan, setPlan] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate(split: "upper" | "lower" | "rest") {
    const pairing = SPLITS.find(s => s.key === split)!;
    setLoading(true);
    setPlan(null);
    setError(null);
    try {
      const hasGym = split !== "rest";
      const data = await api.getTodayPlan(hasGym, pairing.cardio, hasGym ? split : undefined);
      setPlan(data.plan);
    } catch {
      setError("Could not generate plan — make sure the API is running.");
    } finally {
      setLoading(false);
    }
  }

  function handleSplitClick(s: "upper" | "lower" | "rest") {
    setGymSplit(s);
    setPlan(null);
    setError(null);
    generate(s);
  }

  function reset() {
    setGymSplit(null);
    setPlan(null);
    setError(null);
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">
          Today's Training Plan
        </h2>
        <span className={`text-xs font-medium px-3 py-1 rounded-full border ${RISK_COLORS[riskLevel]}`}>
          {RISK_LABELS[riskLevel]}
        </span>
      </div>

      {/* Split buttons */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {SPLITS.map(s => (
          <button
            key={s.key}
            onClick={() => handleSplitClick(s.key)}
            disabled={loading}
            className={`flex flex-col items-center gap-1.5 py-4 rounded-xl border text-sm font-semibold transition-all disabled:opacity-50
              ${gymSplit === s.key
                ? "border-ironman-red bg-ironman-red/10 text-white"
                : "border-ironman-border bg-[#1A1A1A] text-ironman-muted hover:border-white/40 hover:text-white"
              }`}
          >
            <span className="text-xl">{s.emoji}</span>
            <span>{s.label}</span>
            <span className="text-[10px] font-normal opacity-60">{s.sub}</span>
            <span className="text-[10px] font-medium text-ironman-red">{s.cardioLabel}</span>
          </button>
        ))}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-8 gap-3">
          <div className="w-5 h-5 border-2 border-ironman-red border-t-transparent rounded-full animate-spin" />
          <span className="text-ironman-muted text-sm">Claude is writing your plan…</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-red-400 text-sm bg-red-400/10 border border-red-400/30 rounded-xl px-4 py-3">
          {error}
        </p>
      )}

      {/* Plan */}
      {plan && !loading && (
        <>
          <div className="border-t border-ironman-border pt-4 prose prose-invert prose-sm max-w-none
            [&_strong]:text-white
            [&_p]:text-gray-300 [&_p]:leading-relaxed
            [&_ul]:text-gray-300 [&_li]:mt-1
            [&_li::marker]:text-ironman-red">
            <ReactMarkdown>{plan}</ReactMarkdown>
          </div>
          <div className="mt-3 flex gap-3">
            <button
              onClick={() => gymSplit && generate(gymSplit)}
              className="text-xs text-ironman-muted hover:text-white transition-colors underline underline-offset-2"
            >
              Regenerate
            </button>
            <button
              onClick={reset}
              className="text-xs text-ironman-muted hover:text-white transition-colors underline underline-offset-2"
            >
              ← Change
            </button>
          </div>
        </>
      )}

      {!gymSplit && (
        <p className="text-ironman-muted text-xs text-center py-1">
          Pick your day — cardio is already paired.
        </p>
      )}
    </div>
  );
}
