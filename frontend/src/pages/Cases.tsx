import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { CaseDetail, CaseListItem, Severity } from "../types";
import { Card, Empty, ErrorBox, SeverityBadge, StatusBadge, fmtTime } from "../ui";

export default function Cases() {
  const { can } = useAuth();
  const nav = useNavigate();
  const [rows, setRows] = useState<CaseListItem[]>([]);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState<Severity>("medium");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<CaseListItem[]>("/cases").then(setRows).catch((e) => setError(e.message)); }, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    try { const c = await api<CaseDetail>("/cases", { method: "POST", body: { title, severity } }); nav(`/cases/${c.id}`); }
    catch (err) { setError((err as Error).message); }
  }
  return (
    <>
      <h1>Cases</h1>
      <ErrorBox error={error} />
      {can("analyst") && (
        <Card title="New case">
          <form className="row" onSubmit={create}>
            <input className="grow" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Case title" minLength={3} required />
            <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity)} aria-label="Severity">
              <option>low</option><option>medium</option><option>high</option><option>critical</option>
            </select>
            <button>Create</button>
          </form>
        </Card>
      )}
      <Card>
        {rows.length === 0 ? <Empty>No cases yet.</Empty> : (
          <table>
            <thead><tr><th>#</th><th>Title</th><th>Severity</th><th>Status</th><th>Updated</th></tr></thead>
            <tbody>{rows.map((c) => (
              <tr key={c.id}><td>{c.id}</td><td><Link to={`/cases/${c.id}`}>{c.title}</Link></td><td><SeverityBadge level={c.severity} /></td><td><StatusBadge value={c.status} /></td><td>{fmtTime(c.updated_at)}</td></tr>
            ))}</tbody>
          </table>
        )}
      </Card>
    </>
  );
}
