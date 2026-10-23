"""Correlation engine: connect alerts that share entities (IP / host / user ...) and happen close in time.

Why: one alert is a symptom, a *chain* of alerts on the same entity is an attack story.
Approach: build a graph (alert = node, shared entity + time proximity = edge), take connected
components, and turn every component of 2+ alerts into an Incident."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Alert, Incident
from app.services.rules import TACTIC_ORDER

SEVERITY_WEIGHT = {"low": 10, "medium": 25, "high": 50, "critical": 80}
SEVERITY_ORDER = ["low", "medium", "high", "critical"]
# Entities so common that sharing them proves nothing (would glue unrelated alerts together).
NOISY_ENTITIES = {"user:root", "user:administrator", "user:system", "user:-", "ip:127.0.0.1", "ip:::1"}


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _connected(a: Alert, b: Alert, window: timedelta) -> bool:
    shared = (set(a.entities) & set(b.entities)) - NOISY_ENTITIES
    if not shared:
        return False
    gap = max(a.first_seen, b.first_seen) - min(a.last_seen, b.last_seen)
    return gap <= window


def risk_score(alerts: list[Alert]) -> int:
    base = sum(SEVERITY_WEIGHT.get(a.severity, 10) for a in alerts)
    tactics = {a.mitre_tactic for a in alerts if a.mitre_tactic}
    multiplier = 1 + 0.15 * max(len(tactics) - 1, 0)  # more kill-chain stages => more worrying
    return int(min(100, round(base * multiplier)))


def ordered_tactics(alerts: list[Alert]) -> list[str]:
    present = {a.mitre_tactic for a in alerts if a.mitre_tactic}
    return [t for t in TACTIC_ORDER if t in present]


def incident_severity(alerts: list[Alert]) -> str:
    top = max((SEVERITY_ORDER.index(a.severity) for a in alerts if a.severity in SEVERITY_ORDER), default=1)
    if len(ordered_tactics(alerts)) >= 3:  # spans 3+ kill-chain stages: escalate one level
        top = min(top + 1, len(SEVERITY_ORDER) - 1)
    return SEVERITY_ORDER[top]


def correlate(db: Session, window_minutes: int = 60, max_age_hours: int = 24, now: datetime | None = None) -> list[Incident]:
    now = now or datetime.now(timezone.utc)
    window = timedelta(minutes=window_minutes)
    alerts = list(db.scalars(
        select(Alert).where(Alert.status.in_(("open", "investigating")), Alert.last_seen >= now - timedelta(hours=max_age_hours))
        .order_by(Alert.first_seen)
    ))
    uf = _UnionFind(len(alerts))
    for i in range(len(alerts)):
        for j in range(i + 1, len(alerts)):
            if _connected(alerts[i], alerts[j], window):
                uf.union(i, j)

    clusters: dict[int, list[Alert]] = {}
    for idx, alert in enumerate(alerts):
        clusters.setdefault(uf.find(idx), []).append(alert)

    incidents: list[Incident] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        existing_ids = sorted({a.incident_id for a in members if a.incident_id})
        incident = db.get(Incident, existing_ids[0]) if existing_ids else None
        if incident is None:
            incident = Incident(title="pending")
            db.add(incident)
        tactics = ordered_tactics(members)
        entity_counts: dict[str, int] = {}
        for a in members:
            for e in a.entities:
                if e not in NOISY_ENTITIES:
                    entity_counts[e] = entity_counts.get(e, 0) + 1
        shared = sorted(entity_counts, key=lambda e: (-entity_counts[e], e))[:8]

        incident.title = f"Multi-stage activity ({len(members)} alerts): " + (" → ".join(tactics) if tactics else "unclassified")
        incident.severity = incident_severity(members)
        incident.risk_score = risk_score(members)
        incident.tactics = tactics
        incident.entities = shared
        incident.first_seen = min(a.first_seen for a in members)
        incident.last_seen = max(a.last_seen for a in members)
        db.flush()
        for a in members:
            a.incident_id = incident.id
        incidents.append(incident)
    db.commit()
    return incidents


def incident_timeline(incident: Incident) -> list[dict]:
    return [
        {"time": a.first_seen.isoformat(), "alert_id": a.id, "title": a.title, "severity": a.severity,
         "tactic": a.mitre_tactic, "technique": a.mitre_technique, "events": a.event_count, "entities": a.entities}
        for a in sorted(incident.alerts, key=lambda x: x.first_seen)
    ]
