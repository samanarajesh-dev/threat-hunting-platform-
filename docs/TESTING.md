# Testing and verification

"Verified" means: you ran it and saw the output. Anything else is "written".

## Automated (no Docker needed)
```bash
./scripts/verify.sh        # one command: backend tests (expect 56 passed) + frontend build; ends with VERIFY: PASS or VERIFY: FAIL
```
(It wraps `cd backend && python -m pytest -q` and `cd frontend && npm run build`. CI runs the same script: `.github/workflows/verify.yml`.)
| File | Proves |
|---|---|
| `tests/test_rules.py` | Rules load/compile; invalid rules rejected; wildcard escaping; empty watchlist stays silent |
| `tests/test_detection_correlation.py` | Each rule fires exactly on the seeded attack and never on noise; no duplicate alerts; 2 expected incidents; scan not merged |
| `tests/test_enrichment.py` | IOC typing and rejection of garbage; provider combining; cache; rate-limit tolerance; local watchlist wins |
| `tests/test_api.py` | Auth, roles, validation, case lifecycle, evidence SHA-256 matches bytes, upload limits, reports, audit trail |
| `tests/test_contract.py` | **Triangulation**: `DATA_CONTRACT.md` vs index template, rules, ingest pipeline, seed data, entity map, frontend |

`tests/fake_es.py` understands only the query subset our compiler emits. It proves rule LOGIC, not that real Elasticsearch accepts the DSL.

## Integration checklist (needs Docker; run on first real run, and after any ES-related change)
Automated by `./scripts/integration.sh` (prints PASS/FAIL per step; exits non-zero on failure; never prints secrets). The table shows what each step does, so you can also run it by hand.
`scripts/integration.sh`'s control flow was tested against a mock server, NOT a real stack.
| # | Check | Command | Expect |
|---|---|---|---|
| 1 | Services healthy | `docker compose ps` | elasticsearch, postgres, backend running |
| 2 | Template installed | `curl -u elastic:$P localhost:9200/_index_template/thp-events` | `index_patterns: ["thp-events-*"]` |
| 3 | Pipeline works | `POST _ingest/pipeline/thp-normalize/_simulate` with an sshd "Failed password" line | `event.outcome: failure`, `source.ip`, `user.name` set |
| 4 | Seed loads | `docker compose exec backend python -m scripts.seed_data` | ~723 events indexed; `retro-hunt done: 10 alerts, 2 incident(s)` |
| 5 | Counts match | `curl -u elastic:$P 'localhost:9200/thp-events-*/_count'` | equals events indexed |
| 6 | Rules run on real ES | `POST /api/v1/detections/run?lookback_minutes=180` (from `/docs`) | `errors: {}` |

If step 4 or 6 reports a rule error, the message names the rule and the Elasticsearch reason. Usual cause: a field mapped as a different type than the rule assumes.

## Adding tests
- New rule: a fixture event that must fire it and a near-miss that must not (copy the pattern in `test_detection_correlation.py`).
- New field: follow the contract change procedure; `test_contract.py` will tell you what you missed.
- New route: tests for 401, 403 and the happy path.

## Verification report (end of every task)
Files changed | commands run with real pass/fail counts | what was NOT verified | docs updated.

## Recorded measurements
(Add real numbers here: detection-cycle time at N events, etc. Empty until measured.)
