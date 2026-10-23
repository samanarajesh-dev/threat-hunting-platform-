"""End-to-end logic test: seeded attack scenario -> detection -> correlation -> incidents."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.db.models import Alert, Incident, WatchlistEntry
from app.services import correlation, detection
from app.services.rules import load_rules
from scripts.seed_data import ATTACKER_SSH, C2_DOMAIN, C2_IP, SCANNER, generate_events
from tests.fake_es import FakeES


@pytest.fixture()
def world(db):
    now = datetime.now(timezone.utc)
    es = FakeES(generate_events(now), now)
    db.add_all([WatchlistEntry(ioc_type="ip", value=C2_IP), WatchlistEntry(ioc_type="domain", value=C2_DOMAIN)])
    db.commit()
    return es, db, load_rules("app/detections/rules"), now


def test_seed_data_shape():
    ev = generate_events(datetime.now(timezone.utc))
    assert len(ev) > 700
    assert all("@timestamp" in e for e in ev)
    assert sum(1 for e in ev if e.get("source.ip") == ATTACKER_SSH and e.get("event.outcome") == "failure") == 45


def test_every_rule_fires_exactly_on_the_attack_and_not_on_background_noise(world):
    es, db, rules, now = world
    summary = detection.run_all(es, db, rules, lookback_minutes=180)
    assert summary["errors"] == {}
    alerts = db.scalars(select(Alert)).all()
    assert sorted(a.rule_id for a in alerts) == [f"THP-{i:03d}" for i in range(1, 11)]  # one alert per rule, no false positives

    by_rule = {a.rule_id: a for a in alerts}
    assert by_rule["THP-001"].group_values == {"source.ip": ATTACKER_SSH, "host.name": "web01"}
    assert by_rule["THP-001"].event_count == 45
    assert by_rule["THP-008"].group_values == {"source.ip": SCANNER}
    assert by_rule["THP-009"].group_values == {"host.name": "web01", "destination.ip": C2_IP}
    assert "host:web01" in by_rule["THP-004"].entities


def test_rerunning_detection_does_not_duplicate_alerts(world):
    es, db, rules, now = world
    detection.run_all(es, db, rules, lookback_minutes=180)
    n = len(db.scalars(select(Alert)).all())
    detection.run_all(es, db, rules, lookback_minutes=180)
    assert len(db.scalars(select(Alert)).all()) == n


def test_watchlist_rules_are_silent_with_empty_watchlist(db):
    now = datetime.now(timezone.utc)
    es = FakeES(generate_events(now), now)
    detection.run_all(es, db, load_rules("app/detections/rules"), lookback_minutes=180)
    ids = {a.rule_id for a in db.scalars(select(Alert))}
    assert "THP-009" not in ids and "THP-010" not in ids


def test_correlation_builds_one_attack_story_per_compromised_host(world):
    es, db, rules, now = world
    detection.run_all(es, db, rules, lookback_minutes=180)
    incidents = correlation.correlate(db, window_minutes=60, now=now)
    assert len(incidents) == 2  # Linux intrusion + Windows credential theft; the lone port scan stays an alert

    linux = max(incidents, key=lambda i: len(i.alerts))
    assert sorted(a.rule_id for a in linux.alerts) == ["THP-001", "THP-002", "THP-004", "THP-005", "THP-006", "THP-009", "THP-010"]
    assert linux.tactics == ["Initial Access", "Execution", "Persistence", "Credential Access", "Command and Control"]
    assert linux.severity == "critical"
    assert linux.risk_score == 100
    assert "host:web01" in linux.entities and f"ip:{ATTACKER_SSH}" in linux.entities
    assert "user:root" not in linux.entities  # noisy entity filtered

    windows = min(incidents, key=lambda i: len(i.alerts))
    assert sorted(a.rule_id for a in windows.alerts) == ["THP-003", "THP-007"]

    scan = next(a for a in db.scalars(select(Alert)) if a.rule_id == "THP-008")
    assert scan.incident_id is None


def test_correlation_is_idempotent_and_reuses_incident(world):
    es, db, rules, now = world
    detection.run_all(es, db, rules, lookback_minutes=180)
    correlation.correlate(db, 60, now=now)
    first_ids = {i.id for i in db.scalars(select(Incident))}
    correlation.correlate(db, 60, now=now)
    assert {i.id for i in db.scalars(select(Incident))} == first_ids


def test_alerts_far_apart_in_time_are_not_correlated(db):
    from datetime import timedelta
    t = datetime.now(timezone.utc)
    mk = lambda rid, tactic, start: Alert(rule_id=rid, title=rid, severity="high", mitre_tactic=tactic, entities=["host:h1"],  # noqa: E731
                                          event_count=1, dedupe_key=rid, first_seen=start, last_seen=start)
    db.add_all([mk("A", "Execution", t - timedelta(hours=10)), mk("B", "Persistence", t)])
    db.commit()
    assert correlation.correlate(db, window_minutes=60, now=t) == []


def test_risk_score_grows_with_kill_chain_breadth():
    mk = lambda tactic: Alert(severity="medium", mitre_tactic=tactic)  # noqa: E731
    same_stage = correlation.risk_score([mk("Execution"), mk("Execution")])
    multi_stage = correlation.risk_score([mk("Execution"), mk("Persistence")])
    assert multi_stage > same_stage
