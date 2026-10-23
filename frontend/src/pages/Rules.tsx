import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import type { Rule } from "../types";
import { Card, ErrorBox, SeverityBadge } from "../ui";

export default function Rules() {
  const { can } = useAuth();
  const [rules, setRules] = useState<Rule[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { api<Rule[]>("/rules").then(setRules).catch((e) => setError(e.message)); }, []);

  async function run(lookback?: number) {
    setMsg("Running…"); setError(null);
    try {
      const r = await api<{ alerts_touched: number; incidents: number; errors: Record<string, string> }>(`/detections/run${lookback ? `?lookback_minutes=${lookback}` : ""}`, { method: "POST" });
      setMsg(`Done: ${r.alerts_touched} alert(s) touched, ${r.incidents} incident(s)${Object.keys(r.errors).length ? `, errors in ${Object.keys(r.errors).join(", ")}` : ""}.`);
    } catch (e) { setMsg(null); setError((e as Error).message); }
  }
  return (
    <>
      <h1>Detections</h1>
      <p className="muted">Rules are YAML files in <code>backend/app/detections/rules</code>. They run automatically every minute.</p>
      <ErrorBox error={error} />
      {can("analyst") && (
        <Card title="Run now">
          <div className="row">
            <button onClick={() => run()}>Run rules</button>
            <button className="secondary" onClick={() => run(1440)}>Retro-hunt last 24 h</button>
            <button className="secondary" onClick={() => run(10080)}>Retro-hunt last 7 days</button>
          </div>
          {msg && <p>{msg}</p>}
        </Card>
      )}
      <Card>
        <table>
          <thead><tr><th>ID</th><th>Rule</th><th>Severity</th><th>MITRE ATT&amp;CK</th><th>Window</th></tr></thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}>
                <td className="mono">{r.id}</td>
                <td>{r.title}<br /><small className="muted">{r.description}</small></td>
                <td><SeverityBadge level={r.severity} /></td>
                <td><small>{r.mitre.tactic}<br />{r.mitre.technique} {r.mitre.name}</small></td>
                <td>{r.lookback_minutes} min</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
