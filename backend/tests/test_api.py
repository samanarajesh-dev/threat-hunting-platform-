"""API tests: auth, RBAC, cases, evidence integrity, reports. (Elasticsearch is intentionally unreachable.)"""
import hashlib
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.models import Alert
from app.db.session import SessionLocal
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # runs lifespan: creates tables, bootstraps admin, loads rules
        yield c


def login(client, user="admin", password="Adm1n-test-password"):
    r = client.post("/api/v1/auth/login", data={"username": user, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin(client):
    return login(client)


@pytest.fixture(scope="module")
def analyst(client, admin):
    client.post("/api/v1/auth/users", headers=admin, json={"username": "ana", "password": "Analyst-pass-123", "role": "analyst"})
    return login(client, "ana", "Analyst-pass-123")


@pytest.fixture(scope="module")
def viewer(client, admin):
    client.post("/api/v1/auth/users", headers=admin, json={"username": "vic", "password": "Viewer-pass-1234", "role": "viewer"})
    return login(client, "vic", "Viewer-pass-1234")


def test_health_and_unauthenticated_access_is_rejected(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/v1/alerts").status_code == 401
    assert client.get("/api/v1/alerts", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_bad_login(client):
    assert client.post("/api/v1/auth/login", data={"username": "admin", "password": "wrong"}).status_code == 401
    assert client.post("/api/v1/auth/login", data={"username": "ghost", "password": "wrong"}).status_code == 401


def test_weak_password_and_duplicate_user_rejected(client, admin):
    assert client.post("/api/v1/auth/users", headers=admin, json={"username": "weak", "password": "short"}).status_code == 422
    assert client.post("/api/v1/auth/users", headers=admin, json={"username": "admin", "password": "Another-long-pass-1"}).status_code == 409


def test_role_based_access_control(client, admin, analyst, viewer):
    assert client.get("/api/v1/auth/users", headers=analyst).status_code == 403
    assert client.get("/api/v1/auth/users", headers=admin).status_code == 200
    assert client.get("/api/v1/alerts", headers=viewer).status_code == 200
    assert client.post("/api/v1/cases", headers=viewer, json={"title": "nope"}).status_code == 403
    assert client.get("/api/v1/audit", headers=analyst).status_code == 403


def test_rules_endpoint_lists_shipped_rules(client, viewer):
    rules = client.get("/api/v1/rules", headers=viewer).json()
    assert len(rules) == 10 and rules[0]["id"] == "THP-001"


def test_search_degrades_cleanly_when_elasticsearch_is_down(client, viewer):
    r = client.post("/api/v1/search/events", headers=viewer, json={"query": "host.name:web01"})
    assert r.status_code == 502
    stats = client.get("/api/v1/stats/overview", headers=viewer)
    assert stats.status_code == 200 and stats.json()["error"] == "Elasticsearch unavailable"


def test_search_input_validation(client, viewer):
    assert client.post("/api/v1/search/events", headers=viewer, json={"time_from": "yesterday; DROP"}).status_code == 422
    assert client.post("/api/v1/search/events", headers=viewer, json={"size": 100000}).status_code == 422
    assert client.get("/api/v1/search/pivot", headers=viewer, params={"value": "not an ioc"}).status_code == 422


def test_ioc_lookup_validation_and_watchlist_flow(client, analyst):
    assert client.get("/api/v1/ioc/lookup", headers=analyst, params={"value": "???"}).status_code == 422
    r = client.post("/api/v1/watchlist", headers=analyst, json={"value": "198.51.100.77", "note": "c2"})
    assert r.status_code == 201 and r.json()["ioc_type"] == "ip"
    assert client.post("/api/v1/watchlist", headers=analyst, json={"value": "198.51.100.77"}).status_code == 409
    out = client.get("/api/v1/ioc/lookup", headers=analyst, params={"value": "198.51.100.77"}).json()
    assert out["verdict"] == "malicious"


def _make_alert() -> int:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        a = Alert(rule_id="THP-001", title="Brute force", severity="medium", mitre_tactic="Credential Access", mitre_technique="T1110.001",
                  entities=["ip:203.0.113.50"], event_count=45, dedupe_key="x", first_seen=now, last_seen=now)
        db.add(a); db.commit()
        return a.id


def test_case_lifecycle_evidence_integrity_and_report(client, analyst, viewer, tmp_path):
    alert_id = _make_alert()
    r = client.post("/api/v1/cases", headers=analyst, json={"title": "SSH intrusion on web01", "severity": "high", "alert_ids": [alert_id]})
    assert r.status_code == 201
    case = r.json()
    assert len(case["alerts"]) == 1 and case["owner"]["username"] == "ana"
    cid = case["id"]

    note = client.post(f"/api/v1/cases/{cid}/evidence", headers=analyst, json={"kind": "note", "title": "Observation", "text": "Root login followed brute force"})
    assert note.status_code == 201 and len(note.json()["sha256"]) == 64

    payload = b"%PDF-fake evidence bytes"
    up = client.post(f"/api/v1/cases/{cid}/evidence/file", headers=analyst, data={"title": "auth.log excerpt"},
                     files={"file": ("../../etc/passwd", payload, "text/plain")})
    assert up.status_code == 201
    assert up.json()["sha256"] == hashlib.sha256(payload).hexdigest()  # integrity hash is of the real bytes
    dl = client.get(f"/api/v1/cases/{cid}/evidence/{up.json()['id']}/download", headers=viewer)
    assert dl.status_code == 200 and dl.content == payload

    f = client.post(f"/api/v1/cases/{cid}/findings", headers=analyst,
                    json={"title": "Credentials guessed", "description": "Root password was weak", "severity": "high", "confidence": "high", "mitre_technique": "T1110.001"})
    assert f.status_code == 201
    assert client.post(f"/api/v1/cases/{cid}/findings", headers=analyst, json={"title": "bad technique", "mitre_technique": "nope"}).status_code == 422

    assert client.patch(f"/api/v1/cases/{cid}", headers=analyst, json={"status": "in_progress"}).json()["status"] == "in_progress"

    pdf = client.get(f"/api/v1/cases/{cid}/report", headers=viewer)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF") and pdf.headers["content-type"] == "application/pdf"
    md = client.get(f"/api/v1/cases/{cid}/report", headers=viewer, params={"format": "md"})
    assert "SSH intrusion on web01" in md.text and "Credentials guessed" in md.text
    assert client.get(f"/api/v1/cases/{cid}/report", headers=viewer, params={"format": "exe"}).status_code == 422

    actions = [e["action"] for e in client.get(f"/api/v1/cases/{cid}/timeline", headers=viewer).json()]
    assert actions[0] == "case_created" and "evidence_added" in actions and "report_generated" in actions


def test_oversized_evidence_upload_is_rejected(client, analyst, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "max_evidence_bytes", 100)
    cid = client.post("/api/v1/cases", headers=analyst, json={"title": "Size limit case"}).json()["id"]
    r = client.post(f"/api/v1/cases/{cid}/evidence/file", headers=analyst, data={"title": "big"}, files={"file": ("a.bin", b"x" * 500)})
    assert r.status_code == 413


def test_alert_status_change_is_audited(client, analyst, admin):
    aid = _make_alert()
    assert client.patch(f"/api/v1/alerts/{aid}", headers=analyst, json={"status": "false_positive"}).json()["status"] == "false_positive"
    assert client.patch(f"/api/v1/alerts/{aid}", headers=analyst, json={"status": "bogus"}).status_code == 422
    log = client.get("/api/v1/audit", headers=admin).json()
    assert any(e["action"] == "alert_status" and e["object_id"] == aid for e in log)
