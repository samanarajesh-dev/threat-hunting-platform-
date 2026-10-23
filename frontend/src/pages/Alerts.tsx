import { Fragment, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { Alert, CaseDetail } from "../types";
import { Card, Empty, ErrorBox, SeverityBadge, fmtTime } from "../ui";

export default function Alerts() {
  const { can } = useAuth();
  const nav = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [status, setStatus] = useState("open");
  const [severity, setSeverity] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    const q = new URLSearchParams(); if (status) q.set("status", status); if (severity) q.set("severity", severity);
    api<Alert[]>(`/alerts?${q}`).then(setAlerts).catch((e) => setError(e.message));
  };
  useEffect(load, [status, severity]);  // eslint-disable-line react-hooks/exhaustive-deps

  async function setAlertStatus(id: number, s: string) {
    try { await api(`/alerts/${id}`, { method: "PATCH", body: { status: s } }); load(); } catch (e) { setError((e as Error).message); }
  }
  async function toCase(a: Alert) {
    try {
      const c = await api<CaseDetail>("/cases", { method: "POST", body: { title: a.title, description: a.description, severity: a.severity, alert_ids: [a.id] } });
      nav(`/cases/${c.id}`);
    } catch (e) { setError((e as Error).message); }
  }

  return (
    <>
      <h1>Alerts</h1>
      <Card>
        <div className="row">
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status filter">
            <option value="">All statuses</option><option value="open">Open</option><option value="investigating">Investigating</option><option value="closed">Closed</option><option value="false_positive">False positive</option>
          </select>
          <select value={severity} onChange={(e) => setSeverity(e.target.value)} aria-label="Severity filter">
            <option value="">All severities</option><option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
          </select>
        </div>
      </Card>
      <ErrorBox error={error} />
      <Card>
        {alerts.length === 0 ? <Empty>No alerts match.</Empty> : (
          <table>
            <thead><tr><th>Severity</th><th>Alert</th><th>MITRE</th><th>Entities</th><th>Events</th><th>First seen</th><th>Status</th></tr></thead>
            <tbody>
              {alerts.map((a) => (
                <Fragment key={a.id}>
                  <tr className="clickable" onClick={() => setOpen(open === a.id ? null : a.id)}>
                    <td><SeverityBadge level={a.severity} /></td>
                    <td>{a.title}{a.incident_id && <> <Link to={`/incidents/${a.incident_id}`} onClick={(e) => e.stopPropagation()} className="tag">incident #{a.incident_id}</Link></>}</td>
                    <td><small>{a.mitre_tactic}<br />{a.mitre_technique}</small></td>
                    <td className="mono small">{a.entities.join(", ")}</td>
                    <td className="num">{a.event_count}</td>
                    <td>{fmtTime(a.first_seen)}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      {can("analyst") ? (
                        <select value={a.status} onChange={(e) => setAlertStatus(a.id, e.target.value)} aria-label="Alert status">
                          <option value="open">open</option><option value="investigating">investigating</option><option value="closed">closed</option><option value="false_positive">false positive</option>
                        </select>
                      ) : a.status}
                    </td>
                  </tr>
                  {open === a.id && (
                    <tr><td colSpan={7}>
                      <p>{a.description}</p>
                      <h4>Sample events</h4>
                      <pre>{JSON.stringify(a.sample_events, null, 2)}</pre>
                      {can("analyst") && <button className="secondary" onClick={() => toCase(a)}>Open case from this alert</button>}
                    </td></tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
