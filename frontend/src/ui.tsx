import type { ReactNode } from "react";
import type { Severity } from "./types";

export const SeverityBadge = ({ level }: { level: Severity | string }) => <span className={`badge sev-${level}`}>{level}</span>;
export const StatusBadge = ({ value }: { value: string }) => <span className="badge status">{value.replace("_", " ")}</span>;

export const Card = ({ title, children, actions }: { title?: string; children: ReactNode; actions?: ReactNode }) => (
  <section className="card">
    {(title || actions) && <header className="card-head"><h3>{title}</h3><div>{actions}</div></header>}
    {children}
  </section>
);

export const ErrorBox = ({ error }: { error: string | null }) => (error ? <div className="error" role="alert">{error}</div> : null);
export const Empty = ({ children }: { children: ReactNode }) => <p className="muted empty">{children}</p>;

export const fmtTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "short", timeStyle: "medium" }) : "-";

/** Read "host.name" from a flat ({"host.name": x}) or nested ({host: {name: x}}) event. */
export function dig(doc: Record<string, unknown>, path: string): unknown {
  if (path in doc) return doc[path];
  let cur: unknown = doc;
  for (const part of path.split(".")) {
    if (typeof cur !== "object" || cur === null || !(part in cur)) return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return cur;
}
export const str = (v: unknown) => (v === undefined || v === null ? "" : String(v));
