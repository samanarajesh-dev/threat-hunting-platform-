import { Fragment, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { api } from "../api";
import { useAuth } from "../auth";
import type { CaseListItem, LogEvent, PivotResult, SearchResult } from "../types";
import { Card, Empty, ErrorBox, dig, fmtTime, str } from "../ui";

const RANGES: Record<string, string> = { "Last hour": "now-1h", "Last 24 hours": "now-24h", "Last 7 days": "now-7d", "Last 30 days": "now-30d" };

export default function Hunt() {
  const [params] = useSearchParams();
  const { can } = useAuth();
  const [query, setQuery] = useState(params.get("q") ?? "event.outcome:failure");
  const [range, setRange] = useState("now-24h");
  const [result, setResult] = useState<SearchResult | null>(null);
  const [pivotValue, setPivotValue] = useState(params.get("pivot") ?? "");
  const [pivot, setPivot] = useState<PivotResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [caseId, setCaseId] = useState("");

  async function run(e?: FormEvent) {
    e?.preventDefault();
    setBusy(true); setError(null); setOpen(null);
    try { setResult(await api<SearchResult>("/search/events", { method: "POST", body: { query, time_from: range, size: 200 } })); }
    catch (err) { setError((err as Error).message); } finally { setBusy(false); }
  }
  async function runPivot(e?: FormEvent) {
    e?.preventDefault();
    if (!pivotValue.trim()) return;
    setBusy(true); setError(null);
    try { setPivot(await api<PivotResult>(`/search/pivot?value=${encodeURIComponent(pivotValue.trim())}&time_from=${range}`)); }
    catch (err) { setError((err as Error).message); setPivot(null); } finally { setBusy(false); }
  }
  async function attach(ev: LogEvent) {
    if (!caseId) return;
    try {
      await api(`/cases/${caseId}/evidence`, { method: "POST", body: { kind: "log_event", title: `${str(dig(ev, "event.action"))} on ${str(dig(ev, "host.name"))}`, content: ev } });
      setError(null); alert("Event saved as evidence (hashed, append-only).");
    } catch (err) { setError((err as Error).message); }
  }

  useEffect(() => {
    if (can("analyst")) api<CaseListItem[]>("/cases?status=open").then(setCases).catch(() => undefined);
    if (params.get("pivot")) runPivot(); else run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <h1>Hunt</h1>
      <Card>
        <form className="row" onSubmit={run}>
          <input className="grow mono" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="source.ip:203.0.113.50 AND event.outcome:failure" aria-label="Search query" />
          <select value={range} onChange={(e) => setRange(e.target.value)} aria-label="Time range">
            {Object.entries(RANGES).map(([label, v]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <button disabled={busy}>Search</button>
        </form>
        <form className="row" onSubmit={runPivot}>
          <input className="grow mono" value={pivotValue} onChange={(e) => setPivotValue(e.target.value)} placeholder="Pivot on an indicator: IP, domain, URL or file hash" aria-label="Indicator" />
          <button className="secondary" disabled={busy}>Pivot</button>
        </form>
        <small className="muted">Lucene syntax: <code>host.name:web01</code>, <code>process.command_line:*curl*</code>, <code>NOT user.name:alice</code>. Fields follow the ECS naming used by the platform.</small>
      </Card>
      <ErrorBox error={error} />

      {pivot && (
        <Card title={`Pivot: ${pivot.type} ${pivot.value}`}>
          <p><b>{pivot.total}</b> events · first seen {fmtTime(pivot.first_seen)} · last seen {fmtTime(pivot.last_seen)}</p>
          <div className="grid2">
            <div><h4>Hosts that touched it</h4>{pivot.hosts.length ? <table><tbody>{pivot.hosts.map((h) => <tr key={h.name}><td>{h.name}</td><td className="num">{h.count}</td></tr>)}</tbody></table> : <Empty>None</Empty>}</div>
            <div><h4>What happened</h4>{pivot.actions.length ? <table><tbody>{pivot.actions.map((h) => <tr key={h.name}><td>{h.name}</td><td className="num">{h.count}</td></tr>)}</tbody></table> : <Empty>None</Empty>}</div>
          </div>
        </Card>
      )}

      {result && (
        <Card title={`${result.total.toLocaleString()} events`}>
          <div style={{ height: 90 }}>
            <ResponsiveContainer>
              <BarChart data={result.histogram.map((h) => ({ ...h, label: fmtTime(h.t) }))}>
                <XAxis dataKey="label" hide />
                <Tooltip contentStyle={{ background: "#121826", border: "1px solid #263044" }} />
                <Bar dataKey="count" fill="#e8a63d" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {result.hits.length === 0 ? <Empty>No events match.</Empty> : (
            <div className="scroll">
              <table className="events">
                <thead><tr><th>Time</th><th>Host</th><th>Action</th><th>User</th><th>Source → Destination</th><th>Detail</th></tr></thead>
                <tbody>
                  {result.hits.map((h, i) => (
                    <Fragment key={i}>
                      <tr className="clickable" onClick={() => setOpen(open === i ? null : i)}>
                        <td>{fmtTime(str(h["@timestamp"]))}</td>
                        <td>{str(dig(h, "host.name"))}</td>
                        <td>{str(dig(h, "event.action")) || str(dig(h, "event.category"))}</td>
                        <td>{str(dig(h, "user.name"))}</td>
                        <td className="mono">{str(dig(h, "source.ip"))}{dig(h, "destination.ip") ? ` → ${str(dig(h, "destination.ip"))}:${str(dig(h, "destination.port"))}` : ""}</td>
                        <td className="trunc">{str(dig(h, "process.command_line")) || str(dig(h, "dns.question.name")) || str(h.message)}</td>
                      </tr>
                      {open === i && (
                        <tr><td colSpan={6}>
                          <pre>{JSON.stringify(h, null, 2)}</pre>
                          {can("analyst") && (
                            <div className="row">
                              <select value={caseId} onChange={(e) => setCaseId(e.target.value)} aria-label="Case">
                                <option value="">Save to case…</option>
                                {cases.map((c) => <option key={c.id} value={c.id}>#{c.id} {c.title}</option>)}
                              </select>
                              <button className="secondary" disabled={!caseId} onClick={() => attach(h)}>Attach as evidence</button>
                            </div>
                          )}
                        </td></tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </>
  );
}
