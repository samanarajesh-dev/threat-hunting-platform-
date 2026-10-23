import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { CaseDetail, IncidentDetail } from "../types";
import { Card, ErrorBox, SeverityBadge, fmtTime } from "../ui";

export default function IncidentDetailPage() {
  const { id } = useParams();
  const { can } = useAuth();
  const nav = useNavigate();
  const [inc, setInc] = useState<IncidentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<IncidentDetail>(`/incidents/${id}`).then(setInc).catch((e) => setError(e.message)); }, [id]);

  async function openCase() {
    if (!inc) return;
    try {
      const c = await api<CaseDetail>("/cases", { method: "POST", body: { title: `Incident #${inc.id}: ${inc.tactics.join(" → ")}`.slice(0, 250), severity: inc.severity, incident_id: inc.id } });
      nav(`/cases/${c.id}`);
    } catch (e) { setError((e as Error).message); }
  }
  if (!inc) return <><h1>Incident</h1><ErrorBox error={error} /></>;

  return (
    <>
      <h1>Incident #{inc.id} <SeverityBadge level={inc.severity} /></h1>
      <ErrorBox error={error} />
      <Card title="Attack chain" actions={can("analyst") && <button onClick={openCase}>Open investigation case</button>}>
        <div className="chain">{inc.tactics.map((t, i) => <span key={t} className="chip">{i + 1}. {t}</span>)}</div>
        <p>Risk score <b>{inc.risk_score}</b>/100 · {fmtTime(inc.first_seen)} → {fmtTime(inc.last_seen)}</p>
        <p className="mono small">Entities: {inc.entities.join(", ")}</p>
      </Card>
      <Card title="Timeline">
        <ol className="timeline">
          {inc.timeline.map((t) => (
            <li key={t.alert_id}>
              <time>{fmtTime(t.time)}</time>
              <div><SeverityBadge level={t.severity} /> <b>{t.title}</b> <small className="muted">{t.tactic} · {t.technique} · {t.events} events</small>
                <div className="mono small muted">{t.entities.join(", ")}</div></div>
            </li>
          ))}
        </ol>
      </Card>
      <p><Link to="/incidents">← All incidents</Link></p>
    </>
  );
}
