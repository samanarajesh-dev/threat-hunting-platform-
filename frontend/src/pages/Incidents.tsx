import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Incident } from "../types";
import { Card, Empty, ErrorBox, SeverityBadge, fmtTime } from "../ui";

export default function Incidents() {
  const [rows, setRows] = useState<Incident[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Incident[]>("/incidents").then(setRows).catch((e) => setError(e.message)); }, []);
  return (
    <>
      <h1>Incidents</h1>
      <p className="muted">Alerts that share an IP, host or user and happen close together are grouped here automatically: one row is one probable attack.</p>
      <ErrorBox error={error} />
      <Card>
        {rows.length === 0 ? <Empty>No correlated incidents yet.</Empty> : (
          <table>
            <thead><tr><th>Risk</th><th>Severity</th><th>Attack chain</th><th>Key entities</th><th>Last activity</th></tr></thead>
            <tbody>
              {rows.map((i) => (
                <tr key={i.id}>
                  <td className="num"><b>{i.risk_score}</b></td>
                  <td><SeverityBadge level={i.severity} /></td>
                  <td><Link to={`/incidents/${i.id}`}>{i.tactics.join(" → ") || i.title}</Link></td>
                  <td className="mono small">{i.entities.slice(0, 4).join(", ")}</td>
                  <td>{fmtTime(i.last_seen)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </>
  );
}
