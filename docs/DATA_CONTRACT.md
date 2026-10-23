# Data Contract (source of truth)

Every component (collectors, ingest pipeline, rules, correlation, API, dashboard, seed data) must use
ONLY the fields and values below. This is a subset of the Elastic Common Schema (ECS).
`backend/tests/test_contract.py` cross-checks this file against the index template, the rules, the ingest
pipeline, the seed data, the entity map and the frontend. If a check fails, one of them has drifted: fix the drift, do not delete the check.

## Fields (one row per field; keep this table in sync with `INDEX_TEMPLATE` in `backend/app/services/es.py`)

| Field | ES type | Meaning / example | Used by |
|---|---|---|---|
| `@timestamp` | date | Event time, UTC ISO-8601 | every query |
| `message` | text | Original log line | search, pipeline |
| `event.category` | keyword | Kind of event, see vocabulary | rules |
| `event.action` | keyword | What happened, see vocabulary | rules |
| `event.outcome` | keyword | `success` or `failure` | rules |
| `event.code` | keyword | Source event id, e.g. `10` = Sysmon ProcessAccess | THP-007 |
| `event.dataset` | keyword | Collector dataset name, e.g. `linux.syslog` | filtering |
| `host.name` | keyword | Machine the event came from | grouping, correlation entity |
| `host.ip` | ip | Host addresses | pivot |
| `host.os.type` | keyword | `linux`, `windows` | filtering |
| `user.name` | keyword | Account involved | rules, correlation entity |
| `source.ip` | ip | Origin address | rules, pivot, correlation entity |
| `source.port` | integer | Origin port | display |
| `destination.ip` | ip | Target address | THP-009, pivot, correlation entity |
| `destination.port` | integer | Target port | THP-008 |
| `process.name` | keyword | Executable name | THP-003, THP-007 |
| `process.pid` | long | Process id | display |
| `process.command_line` | wildcard | Full command line | THP-003, THP-004 |
| `process.parent.name` | keyword | Parent executable | future rules |
| `file.hash.md5` | keyword | MD5 of a file | hash pivot |
| `file.hash.sha1` | keyword | SHA-1 of a file | hash pivot |
| `file.hash.sha256` | keyword | SHA-256 of a file | hash pivot, correlation entity |
| `dns.question.name` | keyword | Domain that was resolved | THP-010, pivot, correlation entity |
| `url.full` | wildcard | Full URL | URL pivot |
| `url.domain` | keyword | Domain part of a URL | domain pivot |
| `winlog.event_data.TargetImage` | wildcard | Sysmon target process path | THP-007 |
| `thp.auth_method` | keyword | `password` / `publickey`, set by the pipeline | display |

## Vocabularies (closed sets; keep one line per field)

- `event.category`: `authentication`, `network`, `process`, `iam`, `configuration`
- `event.action`: `ssh_login`, `user_created`, `cron_modified`, `scheduled_task_created`, `connection_allowed`, `connection_denied`, `dns_query`, `process_start`, `process_access`
- `event.outcome`: `success`, `failure`

Other closed sets (defined in code, do not extend casually):
- Severity: `low`, `medium`, `high`, `critical`
- Alert status: `open`, `investigating`, `closed`, `false_positive`
- Case status: `open`, `in_progress`, `closed`
- Roles: `viewer` < `analyst` < `admin`
- MITRE tactics: the 14 values in `TACTIC_ORDER` in `backend/app/services/rules.py`
- Entity keys (correlation): `ip:<v>`, `host:<v>`, `user:<v>`, `domain:<v>`, `sha256:<v>`

## Invariants
- Timestamps are timezone-aware UTC. IP fields hold valid IPs only.
- Events may be stored with flat dotted keys or nested objects; all readers must handle both.
- Documentation-range addresses (RFC 5737: `203.0.113.0/24`, `198.51.100.0/24`, `192.0.2.0/24`) are used for demo attackers.

## Contract change procedure (all steps in ONE change)
1. Add or edit the row here (and the vocabulary line if values change).
2. Update `INDEX_TEMPLATE` in `backend/app/services/es.py`, then regenerate `infra/elasticsearch/*.json`.
3. Update the ingest pipeline if the field is parsed from raw logs.
4. Update affected rules, `scripts/seed_data.py`, and the frontend.
5. Add or update tests, including a fixture for any rule that uses the change.
6. Run `python -m pytest -q` and `npm run build`; both must pass.
