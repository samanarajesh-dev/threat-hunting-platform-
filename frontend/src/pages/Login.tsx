import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";
import { ErrorBox } from "../ui";

export default function Login() {
  const { login } = useAuth();
  const [username, setU] = useState("");
  const [password, setP] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await login(username, password); } catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  return (
    <div className="login">
      <form className="card" onSubmit={submit}>
        <h2>Threat Hunting Platform</h2>
        <p className="muted">Sign in to continue</p>
        <label>Username<input value={username} onChange={(e) => setU(e.target.value)} autoComplete="username" autoFocus required /></label>
        <label>Password<input type="password" value={password} onChange={(e) => setP(e.target.value)} autoComplete="current-password" required /></label>
        <ErrorBox error={error} />
        <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
}
