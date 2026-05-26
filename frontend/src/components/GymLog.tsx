import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { GymWorkout } from "../api/client";

interface SetRow { reps: string; weight: string; }
interface ExRow  { name: string; sets: SetRow[]; }

function emptyEx(): ExRow {
  return { name: "", sets: [{ reps: "", weight: "" }] };
}

interface Props {
  recentWorkouts: GymWorkout[];
  onSaved: () => void;
}

export default function GymLog({ recentWorkouts, onSaved }: Props) {
  const [open, setOpen] = useState(false);
  const [duration, setDuration] = useState("");
  const [notes, setNotes] = useState("");
  const [exercises, setExercises] = useState<ExRow[]>([emptyEx()]);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [exerciseNames, setExerciseNames] = useState<string[]>([]);

  useEffect(() => {
    api.getExerciseNames().then(setExerciseNames).catch(() => {});
  }, []);

  function updateExName(i: number, val: string) {
    setExercises((ex) => ex.map((e, idx) => idx === i ? { ...e, name: val } : e));
  }
  function updateSet(ei: number, si: number, field: "reps" | "weight", val: string) {
    setExercises((ex) =>
      ex.map((e, idx) =>
        idx !== ei ? e : {
          ...e,
          sets: e.sets.map((s, sidx) => sidx === si ? { ...s, [field]: val } : s),
        }
      )
    );
  }
  function addSet(ei: number) {
    setExercises((ex) =>
      ex.map((e, idx) => idx === ei ? { ...e, sets: [...e.sets, { reps: "", weight: "" }] } : e)
    );
  }
  function addExercise() {
    setExercises((ex) => [...ex, emptyEx()]);
  }

  async function save() {
    setSaving(true);
    try {
      await api.logGymWorkout({
        date: new Date().toISOString().slice(0, 10),
        duration_minutes: duration ? parseInt(duration) : null,
        notes: notes || null,
        exercises: exercises
          .filter((e) => e.name.trim())
          .map((e) => ({
            name: e.name,
            sets: e.sets
              .filter((s) => s.reps)
              .map((s) => ({
                reps: parseInt(s.reps),
                weight_kg: s.weight ? parseFloat(s.weight) : null,
              })),
          })),
      });
      setSuccess(true);
      setOpen(false);
      setExercises([emptyEx()]);
      setDuration("");
      setNotes("");
      onSaved();
      setTimeout(() => setSuccess(false), 3000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-ironman-muted uppercase tracking-wider">
          Gym Log
        </h2>
        {success && (
          <span className="text-green-400 text-xs font-medium">Saved!</span>
        )}
        <button
          onClick={() => setOpen((o) => !o)}
          className="text-xs bg-[#2A2A2A] hover:bg-[#333] px-3 py-1.5 rounded-lg transition-colors"
        >
          {open ? "Cancel" : "+ Log Session"}
        </button>
      </div>

      {open && (
        <div className="space-y-4 mb-4">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs text-ironman-muted mb-1 block">Duration (min)</label>
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                placeholder="60"
                className="w-full bg-[#111] border border-[#2A2A2A] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-ironman-red"
              />
            </div>
            <div className="flex-1">
              <label className="text-xs text-ironman-muted mb-1 block">Notes</label>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. felt strong on squats"
                className="w-full bg-[#111] border border-[#2A2A2A] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-ironman-red"
              />
            </div>
          </div>

          {exercises.map((ex, ei) => (
            <div key={ei} className="bg-[#111] border border-[#2A2A2A] rounded-xl p-3 space-y-2">
              <input
                list="exercises-list"
                value={ex.name}
                onChange={(e) => updateExName(ei, e.target.value)}
                placeholder="Exercise name"
                className="w-full bg-transparent border-b border-[#2A2A2A] pb-2 text-sm focus:outline-none focus:border-ironman-red"
              />
              <datalist id="exercises-list">
                {exerciseNames.map((s) => <option key={s} value={s} />)}
              </datalist>
              <div className="space-y-1">
                {ex.sets.map((s, si) => (
                  <div key={si} className="flex gap-2 items-center">
                    <span className="text-xs text-ironman-muted w-6">{si + 1}</span>
                    <input
                      type="number"
                      value={s.reps}
                      onChange={(e) => updateSet(ei, si, "reps", e.target.value)}
                      placeholder="reps"
                      className="w-20 bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-ironman-red"
                    />
                    <input
                      type="number"
                      value={s.weight}
                      onChange={(e) => updateSet(ei, si, "weight", e.target.value)}
                      placeholder="kg"
                      className="w-20 bg-[#1A1A1A] border border-[#2A2A2A] rounded-lg px-2 py-1 text-sm focus:outline-none focus:border-ironman-red"
                    />
                  </div>
                ))}
                <button
                  onClick={() => addSet(ei)}
                  className="text-xs text-ironman-muted hover:text-white transition-colors mt-1"
                >
                  + add set
                </button>
              </div>
            </div>
          ))}

          <button
            onClick={addExercise}
            className="text-xs text-ironman-muted hover:text-white transition-colors w-full text-center py-2 border border-dashed border-[#2A2A2A] rounded-xl"
          >
            + Add Exercise
          </button>

          <button
            onClick={save}
            disabled={saving}
            className="w-full bg-ironman-red hover:bg-red-700 disabled:opacity-50 text-white text-sm font-semibold py-2.5 rounded-xl transition-colors"
          >
            {saving ? "Saving…" : "Save Workout"}
          </button>
        </div>
      )}

      <div className="space-y-2 max-h-52 overflow-y-auto">
        {recentWorkouts.length === 0 && !open && (
          <p className="text-ironman-muted text-sm">No gym sessions logged yet.</p>
        )}
        {recentWorkouts.map((w) => (
          <div key={w.id} className="bg-[#111] border border-[#2A2A2A] rounded-xl px-4 py-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">
                🏋️ {new Date(w.date).toLocaleDateString("en-US", { month: "short", day: "numeric", weekday: "short" })}
              </p>
              <p className="text-xs text-ironman-muted">
                {w.duration_minutes ? `${w.duration_minutes}min` : ""}
              </p>
            </div>
            <p className="text-xs text-ironman-muted mt-1">
              {w.exercises.map((e) => e.name).join(" · ") || "No exercises"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
