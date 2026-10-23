# Architecture

```
Linux / Windows / Sysmon / Firewall / Apps
   -> Collection (Filebeat, Winlogbeat, syslog)
   -> Ingest pipeline `thp-normalize` (parse + map to the data contract)
   -> Elasticsearch  index pattern `thp-events-*`   (raw events only)
        |-> Detection engine: YAML rules -> ES aggregation queries (every 60 s, or on demand)
        |        -> Alerts (PostgreSQL)  -> Correlation -> Incidents (PostgreSQL)
        |-> FastAPI backend: search, indicator pivot, stats
   FastAPI <-> PostgreSQL: users, alerts, incidents, cases, evidence, findings, watchlist, ioc cache, audit
   FastAPI <-> Threat intel (VirusTotal, AbuseIPDB, OTX), cached 24 h
   React dashboard -> API -> investigation, cases, PDF/Markdown reports
```

## Data flow
1. Collectors ship log lines; the ingest pipeline sets contract fields (`event.*`, `user.name`, `source.ip` ...).
2. The detection loop (`main.py`, thread) calls `detection.run_all` then `correlation.correlate`.
3. A rule is compiled by `rules.build_search_body` into ONE ES request: filters + composite aggregation on `group_by`.
   Python keeps only buckets that reach the threshold and writes/updates alerts (dedupe by rule + group within `suppress_minutes`).
4. Correlation connects alerts that share an entity (not noisy) and are within the time window; each connected group of 2+ alerts becomes an incident
   with ordered kill-chain tactics, escalated severity (3+ stages) and a 0-100 risk score.
5. Analysts search/pivot, look up indicators, open cases from alerts or incidents, attach hashed evidence, record findings, export reports.

## Boundaries (keep them)
- Elasticsearch = events only. PostgreSQL = everything relational. Never store raw events in Postgres or cases in ES.
- Routers orchestrate; logic lives in `services/`. The frontend talks only to `/api/v1` through `frontend/src/api.ts`.
- Rules are data (YAML), not code. Adding a detection must not require editing Python.

## Security model
JWT (HS256, expiring) + roles viewer < analyst < admin on every route; bcrypt passwords; audit log for logins, searches, status changes, evidence and report actions;
append-only evidence with SHA-256; uploads stored under random names and served as downloads; ES queries bounded (fixed index, size cap, validated time range).
