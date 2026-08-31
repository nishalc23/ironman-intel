import { useState } from "react";
import { auth, token } from "../api/client";

export default function SignIn({ onSignedIn }: { onSignedIn: (name: string | null) => void }) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = mode === "login"
        ? await auth.login(email, password)
        : await auth.signup(email, password, displayName || undefined);
      token.set(result.access_token);
      onSignedIn(result.display_name);
    } catch (err) {
      // Login stays deliberately vague: the API returns the same response for
      // a wrong password and an unknown email, and the UI must not undo that.
      // Signup can be specific, because telling someone their password is too
      // short leaks nothing.
      setError(mode === "login"
        ? "Incorrect email or password."
        : err instanceof Error && err.message
        ? err.message
        : "Could not create that account.");
    } finally {
      setBusy(false);
    }
  };

  const field = "w-full px-3 py-2.5 rounded-xl text-sm text-zinc-200 placeholder-zinc-600 " +
    "border border-white/10 focus:border-ironman-red/50 focus:outline-none transition-colors";

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-black tracking-tight text-zinc-100">
            IRONMAN<span className="text-ironman-red">INTEL</span>
          </h1>
          <p className="text-[11px] uppercase tracking-[0.2em] text-zinc-600 mt-2">
            70.3 Training Analytics
          </p>
        </div>

        <form
          onSubmit={submit}
          className="rounded-2xl border border-white/6 p-5 space-y-3"
          style={{ background: "rgba(255,255,255,0.025)" }}
        >
          <div className="flex gap-1 p-1 rounded-xl mb-1" style={{ background: "rgba(0,0,0,0.3)" }}>
            {(["login", "signup"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setError(null); }}
                className={`flex-1 py-1.5 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all
                  ${mode === m ? "text-zinc-100" : "text-zinc-600 hover:text-zinc-400"}`}
                style={{ background: mode === m ? "rgba(255,255,255,0.07)" : "transparent" }}
              >
                {m === "login" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          {mode === "signup" && (
            <input
              className={field}
              placeholder="Name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              style={{ background: "rgba(0,0,0,0.25)" }}
            />
          )}

          <input
            className={field}
            type="email"
            required
            placeholder="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ background: "rgba(0,0,0,0.25)" }}
          />

          <input
            className={field}
            type="password"
            required
            minLength={8}
            placeholder="Password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ background: "rgba(0,0,0,0.25)" }}
          />

          {error && (
            <p className="text-[11px] text-amber-400/90 leading-snug">{error}</p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider
              text-white transition-all disabled:opacity-50 hover:brightness-110"
            style={{ background: "#E8001C" }}
          >
            {busy ? "…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
