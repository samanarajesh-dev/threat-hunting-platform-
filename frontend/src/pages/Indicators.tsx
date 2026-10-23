import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { IocResult, WatchEntry } from "../types";
import { Card, Empty, ErrorBox, fmtTime } from "../ui";

export default function Indicators() {
  const { can } = useAuth();
  const [value, setValue] = useState("");
  const [result, setResult] = useState<IocResult | null>(null);
  const [watch, setWatch] = useState<WatchEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const loadWatch = () => api<WatchEntry[]>("/watchlist").then(setWatch).catch((e) => setError(e.message));
  useEffect(() => { loadWatch(); }, []);

  async function lookup(e?: FormEvent, refresh = false) {
    e?.preventDefault();
    setBusy(true); setError(null);
    try { setResult(await api<IocResult>(`/ioc/lookup?value=${encodeURIComponent(value.trim())}&refresh=${refresh}`)); }
    catch (err) { setError((err as Error).message); setResult(null); } finally { setBusy(false); }
  }
  async function addWatch() {
    try { await api("/watchlist", { method: "POST", body: { value: result?.value ?? value, source: "analyst", note: "Added from indicator lookup" } }); loadWatch(); }
    catch (err) { setError((err as Error).message); }
  }
  async function removeWatch(id: number) {
    await api(`/watchlist/${id}`, { method: "DELETE" }); loadWatch();
  }

  return (
    <>
      <h1>Indicators</h1>
      <Card>
        <form className="row" onSubmit={lookup}>
          <input className="grow mono" value={value} onChange={(e) => setValue(e.target.value)} placeholder="IP address, domain, URL, or MD5 / SHA-1 / SHA-256 hash" aria-label="Indicator" required />
          <button disabled={busy || !can("analyst")}>{busy ? "Checking…" : "Look up"}</button>
        </form>
        <small className="muted">Checks every configured threat-intel provider plus your local watchlist. Results are cached for 24 h to protect free-tier quotas.</small>
      </Card>
      <ErrorBox error={error} />

      {result && (
        <Card title={`${result.type.toUpperCase()}  ${result.value}`} actions={<span className={`badge verdict-${result.verdict}`}>{result.verdict}</span>}>
          {result.providers_configured.length === 0 && <p className="muted">No threat-intel API keys configured: only the local watchlist was checked. Add keys in <code>.env</code> to enable VirusTotal, AbuseIPDB and OTX.</p>}
          <table>
            <thead><tr><th>Provider</th><th>Verdict</th><th>Score</th><th>Detail</th></tr></thead>
            <tbody>
              {result.results.map((r) => (
                <tr key={r.provider}><td>{r.provider}</td><td><span className={`badge verdict-${r.verdict}`}>{r.verdict}</span></td><td className="num">{r.score ?? "-"}</td><td className="mono small">{JSON.stringify(r.detail)}</td></tr>
              ))}
            </tbody>
          </table>
          {Object.entries(result.errors).map(([p, e]) => <p key={p} className="warn">{p}: {e}</p>)}
          <div className="row">
            <Link className="button secondary" to={`/hunt?pivot=${encodeURIComponent(result.value)}`}>Hunt for it in the logs</Link>
            {can("analyst") && <button className="secondary" onClick={addWatch}>Add to watchlist</button>}
            {can("analyst") && <button className="secondary" onClick={() => lookup(undefined, true)}>Refresh (skip cache)</button>}
            {result.cached && <small className="muted">served from cache</small>}
          </div>
        </Card>
      )}

      <Card title="Watchlist (the detection engine hunts for these continuously)">
        {watch.filter((w) => w.active).length === 0 ? <Empty>Empty.</Empty> : (
          <table>
            <thead><tr><th>Type</th><th>Indicator</th><th>Source</th><th>Note</th><th /></tr></thead>
            <tbody>
              {watch.filter((w) => w.active).map((w) => (
                <tr key={w.id}><td>{w.ioc_type}</td><td className="mono">{w.value}</td><td>{w.source}</td><td>{w.note}</td>
                  <td>{can("analyst") && <button className="link" onClick={() => removeWatch(w.id)}>remove</button>}</td></tr>
              ))}
            </tbody>
          </table>
        )}
        <small className="muted">{fmtTime(new Date().toISOString())}</small>
      </Card>
    </>
  );
}
