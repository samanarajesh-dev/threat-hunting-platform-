import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";
import type { Incident, Overview as OverviewData } from "../types";
import { Card, Empty, ErrorBox, SeverityBadge, fmtTime } from "../ui";

export default function Overview() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = () => {
      api<OverviewData>("/stats/overview").then(setData).catch((e) => setError(e.message));
      api<Incident[]>("/incidents").then(setIncidents).catch(() => undefined);
    };
    load();
    const t = setInterval(load, 30000);  // keep the SOC wall-screen fresh
    return () => clearInterval(t);
  }, []);

  if (!data) return <><h1>Overview</h1><ErrorBox error={error} /><p className="muted">Loading…</p></>;
  const sev = data.alerts_by_severity;
  return (
    <>
      <h1>Overview</h1>
      <ErrorBox error={data.error ?? error} />
      <div className="stats">
        <div className="stat"><b>{data.open_incidents}</b><span>Open incidents</span></div>
        {(["critical", "high", "medium", "low"] as const).map((s) => (
          <div key={s} className={`stat sev-border-${s}`}><b>{sev[s]}</b><span>{s} alerts</span></div>
        ))}
        <div className="stat"><b>{data.events_24h ?? "-"}</b><span>Events (24 h)</span></div>
        <div className="stat"><b>{data.failed_logins_24h ?? "-"}</b><span>Failed logins (24 h)</span></div>
      </div>

      <div className="grid2">
        <Card title="Events per hour (last 24 h)">
          <div style={{ height: 220 }}>
            <ResponsiveContainer>
              <AreaChart data={data.per_hour.map((p) => ({ ...p, label: new Date(p.t).getHours() + ":00" }))}>
                <CartesianGrid stroke="#263044" strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke="#8d98af" fontSize={11} />
                <YAxis stroke="#8d98af" fontSize={11} />
                <Tooltip contentStyle={{ background: "#121826", border: "1px solid #263044" }} />
                <Area dataKey="count" stroke="#e8a63d" fill="#e8a63d33" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="Highest-risk incidents">
          {incidents.length === 0 ? <Empty>No correlated incidents yet.</Empty> : (
            <table><tbody>
              {incidents.slice(0, 5).map((i) => (
                <tr key={i.id}>
                  <td><SeverityBadge level={i.severity} /></td>
                  <td><Link to={`/incidents/${i.id}`}>{i.title}</Link><br /><small className="muted">{fmtTime(i.last_seen)}</small></td>
                  <td className="num">{i.risk_score}</td>
                </tr>
              ))}
            </tbody></table>
          )}
        </Card>
        <Card title="Top source IPs"><Rank rows={data.top_sources} link="/hunt?q=source.ip:" /></Card>
        <Card title="Busiest hosts"><Rank rows={data.top_hosts} link="/hunt?q=host.name:" /></Card>
      </div>
    </>
  );
}

function Rank({ rows, link }: { rows: { name: string; count: number }[]; link: string }) {
  if (rows.length === 0) return <Empty>No data.</Empty>;
  return <table><tbody>{rows.map((r) => <tr key={r.name}><td><Link to={`${link}${encodeURIComponent(r.name)}`}>{r.name}</Link></td><td className="num">{r.count}</td></tr>)}</tbody></table>;
}
