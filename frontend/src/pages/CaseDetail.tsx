import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, download } from "../api";
import { useAuth } from "../auth";
import type { CaseDetail, Severity, TimelineEvent } from "../types";
import { Card, Empty, ErrorBox, SeverityBadge, fmtTime } from "../ui";

export default function CaseDetailPage() {
  const { id } = useParams();
  const { can } = useAuth();
  const [c, setCase] = useState<CaseDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [note, setNote] = useState({ title: "", text: "" });
  const [ioc, setIoc] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [fileTitle, setFileTitle] = useState("");
  const [finding, setFinding] = useState({ title: "", description: "", severity: "medium" as Severity, confidence: "medium", mitre_technique: "" });

  const load = useCallback(() => {
    api<CaseDetail>(`/cases/${id}`).then(setCase).catch((e) => setError(e.message));
    api<TimelineEvent[]>(`/cases/${id}/timeline`).then(setTimeline).catch(() => undefined);
  }, [id]);
  useEffect(load, [load]);

  const act = async (fn: () => Promise<unknown>) => { setError(null); try { await fn(); load(); } catch (e) { setError((e as Error).message); } };

  const addNote = (e: FormEvent) => { e.preventDefault(); act(async () => { await api(`/cases/${id}/evidence`, { method: "POST", body: { kind: "note", title: note.title, text: note.text } }); setNote({ title: "", text: "" }); }); };
  const addIoc = (e: FormEvent) => { e.preventDefault(); act(async () => { await api(`/cases/${id}/evidence`, { method: "POST", body: { kind: "ioc", title: `IOC ${ioc}`, content: { value: ioc.trim() } } }); setIoc(""); }); };
  const addFile = (e: FormEvent) => {
    e.preventDefault(); if (!file) return;
    act(async () => { const f = new FormData(); f.append("title", fileTitle || file.name); f.append("file", file); await api(`/cases/${id}/evidence/file`, { method: "POST", form: f }); setFile(null); setFileTitle(""); });
  };
  const addFinding = (e: FormEvent) => {
    e.preventDefault();
    act(async () => { await api(`/cases/${id}/findings`, { method: "POST", body: { ...finding, mitre_technique: finding.mitre_technique || null } }); setFinding({ ...finding, title: "", description: "", mitre_technique: "" }); });
  };

  if (!c) return <><h1>Case</h1><ErrorBox error={error} /></>;
  return (
    <>
      <h1>Case #{c.id}: {c.title}</h1>
      <ErrorBox error={error} />
      <Card
        title="Overview"
        actions={<div className="row">
          <button className="secondary" onClick={() => download(`/cases/${c.id}/report?format=pdf`, `case-${c.id}-report.pdf`)}>PDF report</button>
          <button className="secondary" onClick={() => download(`/cases/${c.id}/report?format=md`, `case-${c.id}-report.md`)}>Markdown</button>
        </div>}
      >
        <div className="row">
          <SeverityBadge level={c.severity} />
          {can("analyst") ? (
            <select value={c.status} onChange={(e) => act(() => api(`/cases/${c.id}`, { method: "PATCH", body: { status: e.target.value } }))} aria-label="Case status">
              <option value="open">open</option><option value="in_progress">in progress</option><option value="closed">closed</option>
            </select>
          ) : <span className="badge status">{c.status}</span>}
          <small className="muted">Owner {c.owner?.username ?? "-"} · opened {fmtTime(c.created_at)}</small>
          {c.incident_id && <Link to={`/incidents/${c.incident_id}`}>Incident #{c.incident_id}</Link>}
        </div>
        <p>{c.description || <span className="muted">No summary yet.</span>}</p>
      </Card>

      <Card title={`Linked alerts (${c.alerts.length})`}>
        {c.alerts.length === 0 ? <Empty>None.</Empty> : (
          <table><tbody>{c.alerts.map((a) => (
            <tr key={a.id}><td><SeverityBadge level={a.severity} /></td><td>{a.title}</td><td><small>{a.mitre_tactic} {a.mitre_technique}</small></td><td className="mono small">{a.entities.join(", ")}</td></tr>
          ))}</tbody></table>
        )}
      </Card>

      <Card title={`Findings (${c.findings.length})`}>
        {c.findings.map((f) => (
          <div key={f.id} className="finding"><SeverityBadge level={f.severity} /> <b>{f.title}</b> <small className="muted">{f.confidence} confidence {f.mitre_technique && `· ${f.mitre_technique}`}</small><p>{f.description}</p></div>
        ))}
        {c.findings.length === 0 && <Empty>No findings recorded yet.</Empty>}
        {can("analyst") && (
          <form className="stack" onSubmit={addFinding}>
            <div className="row">
              <input className="grow" value={finding.title} onChange={(e) => setFinding({ ...finding, title: e.target.value })} placeholder="Finding title" minLength={3} required />
              <select value={finding.severity} onChange={(e) => setFinding({ ...finding, severity: e.target.value as Severity })} aria-label="Severity"><option>low</option><option>medium</option><option>high</option><option>critical</option></select>
              <select value={finding.confidence} onChange={(e) => setFinding({ ...finding, confidence: e.target.value })} aria-label="Confidence"><option>low</option><option>medium</option><option>high</option></select>
              <input value={finding.mitre_technique} onChange={(e) => setFinding({ ...finding, mitre_technique: e.target.value })} placeholder="T1110.001" pattern="T\d{4}(\.\d{3})?" style={{ width: 110 }} />
            </div>
            <textarea value={finding.description} onChange={(e) => setFinding({ ...finding, description: e.target.value })} placeholder="What did you find, and why does it matter?" rows={3} />
            <button className="secondary">Add finding</button>
          </form>
        )}
      </Card>

      <Card title={`Evidence (${c.evidence.length})`}>
        <p className="muted small">Evidence is append-only. Each item carries a SHA-256 so anyone can verify it was not altered after collection.</p>
        {c.evidence.length === 0 ? <Empty>No evidence attached.</Empty> : (
          <table>
            <thead><tr><th>#</th><th>Type</th><th>Title</th><th>SHA-256</th><th>Added</th><th /></tr></thead>
            <tbody>{c.evidence.map((e) => (
              <tr key={e.id}><td>{e.id}</td><td>{e.kind}</td><td>{e.title}</td><td className="mono small" title={e.sha256}>{e.sha256.slice(0, 16)}…</td><td>{fmtTime(e.added_at)}</td>
                <td>{e.filename && <button className="link" onClick={() => download(`/cases/${c.id}/evidence/${e.id}/download`, e.filename ?? "evidence.bin")}>download</button>}</td></tr>
            ))}</tbody>
          </table>
        )}
        {can("analyst") && (
          <div className="grid3">
            <form className="stack" onSubmit={addNote}>
              <h4>Add note</h4>
              <input value={note.title} onChange={(e) => setNote({ ...note, title: e.target.value })} placeholder="Title" required />
              <textarea value={note.text} onChange={(e) => setNote({ ...note, text: e.target.value })} rows={3} placeholder="Observation" required />
              <button className="secondary">Save note</button>
            </form>
            <form className="stack" onSubmit={addIoc}>
              <h4>Add indicator</h4>
              <input className="mono" value={ioc} onChange={(e) => setIoc(e.target.value)} placeholder="IP / domain / hash" required />
              <button className="secondary">Save indicator</button>
            </form>
            <form className="stack" onSubmit={addFile}>
              <h4>Upload file (max 10 MB)</h4>
              <input value={fileTitle} onChange={(e) => setFileTitle(e.target.value)} placeholder="Title (optional)" />
              <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
              <button className="secondary">Upload</button>
            </form>
          </div>
        )}
      </Card>

      <Card title="Chain of custody">
        {timeline.length === 0 ? <Empty>No activity.</Empty> : (
          <ol className="timeline">{timeline.map((t, i) => (
            <li key={i}><time>{fmtTime(t.ts)}</time><div><b>{t.user}</b> {t.action.replace("_", " ")} <small className="mono muted">{t.detail ? JSON.stringify(t.detail) : ""}</small></div></li>
          ))}</ol>
        )}
      </Card>
    </>
  );
}
