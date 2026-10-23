export type Severity = "low" | "medium" | "high" | "critical";
export interface User { id: number; username: string; role: "viewer" | "analyst" | "admin"; is_active: boolean }
export interface Alert {
  id: number; rule_id: string; title: string; description: string; severity: Severity; status: string;
  mitre_tactic: string | null; mitre_technique: string | null; group_values: Record<string, unknown>;
  entities: string[]; event_count: number; sample_events: Record<string, unknown>[];
  first_seen: string; last_seen: string; incident_id: number | null;
}
export interface Incident {
  id: number; title: string; severity: Severity; risk_score: number; status: string;
  tactics: string[]; entities: string[]; first_seen: string | null; last_seen: string | null;
}
export interface TimelineItem { time: string; alert_id: number; title: string; severity: Severity; tactic: string | null; technique: string | null; events: number; entities: string[] }
export interface IncidentDetail extends Incident { timeline: TimelineItem[]; alerts: Alert[] }
export interface Overview {
  alerts_by_severity: Record<Severity, number>; open_incidents: number;
  events_24h: number | null; failed_logins_24h: number | null;
  per_hour: { t: string; count: number }[]; top_sources: { name: string; count: number }[]; top_hosts: { name: string; count: number }[];
  error?: string;
}
export type LogEvent = Record<string, unknown> & { id?: string; "@timestamp"?: string };
export interface SearchResult { total: number; hits: LogEvent[]; histogram: { t: string; count: number }[] }
export interface PivotResult {
  type: string; value: string; total: number; first_seen: string | null; last_seen: string | null;
  hosts: { name: string; count: number }[]; actions: { name: string; count: number }[]; hits: LogEvent[];
}
export interface IocResult {
  type: string; value: string; verdict: string; cached: boolean; providers_configured: string[];
  results: { provider: string; verdict: string; score: number | null; detail: Record<string, unknown> }[];
  errors: Record<string, string>;
}
export interface WatchEntry { id: number; ioc_type: string; value: string; source: string; note: string; active: boolean }
export interface CaseListItem { id: number; title: string; status: string; severity: Severity; created_at: string; updated_at: string }
export interface Evidence { id: number; kind: string; title: string; content: Record<string, unknown> | null; filename: string | null; sha256: string; size_bytes: number; added_at: string }
export interface Finding { id: number; title: string; description: string; severity: Severity; confidence: string; mitre_technique: string | null; created_at: string }
export interface CaseDetail extends CaseListItem { description: string; incident_id: number | null; owner: User | null; alerts: Alert[]; evidence: Evidence[]; findings: Finding[] }
export interface TimelineEvent { ts: string; user: string; action: string; detail: Record<string, unknown> | null }
export interface Rule { id: string; title: string; description: string; severity: Severity; mitre: { tactic: string; technique: string; name: string }; lookback_minutes: number; type: string; enabled: boolean }
