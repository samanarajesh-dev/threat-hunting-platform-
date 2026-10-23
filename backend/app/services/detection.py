"""Detection engine: run every enabled rule against Elasticsearch and turn matching groups into alerts."""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Alert, WatchlistEntry
from app.services.rules import ENTITY_TYPES, Rule, build_search_body

log = logging.getLogger("thp.detection")


def _dig(doc: dict, dotted: str):
    """Read 'host.name' from either a flat {'host.name': ..} or nested {'host': {'name': ..}} document."""
    if dotted in doc:
        return doc[dotted]
    cur = doc
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def entities_for(rule: Rule, group_values: dict, samples: list[dict]) -> list[str]:
    out: list[str] = []
    for field, value in group_values.items():
        if field in ENTITY_TYPES and value not in (None, ""):
            out.append(f"{ENTITY_TYPES[field]}:{value}")
    for field in rule.extra_entity_fields:
        for doc in samples:
            v = _dig(doc, field)
            if v and field in ENTITY_TYPES:
                out.append(f"{ENTITY_TYPES[field]}:{v}")
                break
    return sorted(set(out))


def _ms_to_dt(ms) -> datetime:
    return datetime.fromtimestamp(float(ms) / 1000.0, tz=timezone.utc)


def _dedupe_key(rule: Rule, group_values: dict) -> str:
    raw = "|".join(f"{k}={group_values[k]}" for k in sorted(group_values))
    return f"{rule.id}|{hashlib.sha1(raw.encode()).hexdigest()[:16]}"


def watchlist_values(db: Session, ioc_type: str) -> list[str]:
    rows = db.scalars(select(WatchlistEntry.value).where(WatchlistEntry.ioc_type == ioc_type, WatchlistEntry.active.is_(True))).all()
    return list(rows)


def run_rule(es, db: Session, rule: Rule, now: datetime | None = None, lookback_minutes: int | None = None) -> list[Alert]:
    now = now or datetime.now(timezone.utc)
    wl = watchlist_values(db, rule.watchlist.ioc_type) if rule.type == "watchlist" else None
    body = build_search_body(rule, wl, lookback_minutes)
    if body is None:
        return []

    res = es.search(index=get_settings().events_index, timeout="20s", **body)
    buckets = res.get("aggregations", {}).get("groups", {}).get("buckets", [])
    touched: list[Alert] = []

    for b in buckets:
        value = b["distinct"]["value"] if rule.threshold.distinct else b["doc_count"]
        if value < rule.threshold.count:
            continue
        group_values = {field: b["key"][f"g{i}"] for i, field in enumerate(rule.group_by)}
        samples = [h["_source"] for h in b["samples"]["hits"]["hits"]]
        first_seen = _ms_to_dt(b["first_seen"]["value"])
        last_seen = _ms_to_dt(b["last_seen"]["value"])
        key = _dedupe_key(rule, group_values)

        existing = db.scalars(
            select(Alert).where(
                Alert.dedupe_key == key,
                Alert.status.in_(("open", "investigating")),
                Alert.last_seen >= now - timedelta(minutes=rule.suppress_minutes),
            )
        ).first()
        if existing:  # same activity still going on: update, do not spam new alerts
            existing.event_count = max(existing.event_count, b["doc_count"])
            existing.last_seen = max(existing.last_seen, last_seen)
            existing.sample_events = samples
            touched.append(existing)
            continue

        alert = Alert(
            rule_id=rule.id, title=rule.title, description=rule.description, severity=rule.severity,
            mitre_tactic=rule.mitre.tactic, mitre_technique=rule.mitre.technique,
            group_values=group_values, entities=entities_for(rule, group_values, samples),
            event_count=b["doc_count"], sample_events=samples, dedupe_key=key,
            first_seen=first_seen, last_seen=last_seen,
        )
        db.add(alert)
        touched.append(alert)
    db.flush()
    return touched


def run_all(es, db: Session, rules: list[Rule], lookback_minutes: int | None = None) -> dict:
    created_or_updated = 0
    errors: dict[str, str] = {}
    for rule in rules:
        if not rule.enabled:
            continue
        try:
            created_or_updated += len(run_rule(es, db, rule, lookback_minutes=lookback_minutes))
        except Exception as exc:  # one broken rule must never stop the others
            log.exception("rule %s failed", rule.id)
            errors[rule.id] = str(exc)[:300]
    db.commit()
    return {"alerts_touched": created_or_updated, "errors": errors}
