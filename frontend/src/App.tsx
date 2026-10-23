import { Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Alerts from "./pages/Alerts";
import CaseDetailPage from "./pages/CaseDetail";
import Cases from "./pages/Cases";
import Hunt from "./pages/Hunt";
import IncidentDetailPage from "./pages/IncidentDetail";
import Incidents from "./pages/Incidents";
import Indicators from "./pages/Indicators";
import Landing from "./pages/Landing";
import Overview from "./pages/Overview";
import Rules from "./pages/Rules";

const NAV = [
  ["/", "Overview"], ["/hunt", "Hunt"], ["/indicators", "Indicators"], ["/alerts", "Alerts"],
  ["/incidents", "Incidents"], ["/cases", "Cases"], ["/rules", "Detections"],
] as const;

export default function App() {
  const { user, ready, logout } = useAuth();
  if (!ready) return <p className="muted pad">Loading…</p>;
  if (!user) return <Routes><Route path="*" element={<Landing />} /></Routes>;

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">Threat Hunting<br /><span>Platform</span></div>
        <nav>
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>{label}</NavLink>
          ))}
        </nav>
        <div className="who">
          <div>{user.username}</div>
          <small className="muted">{user.role}</small>
          <button className="link" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/hunt" element={<Hunt />} />
          <Route path="/indicators" element={<Indicators />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/incidents/:id" element={<IncidentDetailPage />} />
          <Route path="/cases" element={<Cases />} />
          <Route path="/cases/:id" element={<CaseDetailPage />} />
          <Route path="/rules" element={<Rules />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
