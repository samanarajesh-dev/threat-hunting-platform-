# AGENTS.md - Threat Hunting Platform

You are working on a security-operations web application: it ingests logs, detects threats with
YAML rules, correlates alerts into incidents, and lets analysts investigate and report.
Read this file fully before every task. Keep it short; details live in `docs/`.

## Stack (do not change without asking)
- Collection: Filebeat -> ingest pipeline `thp-normalize` -> Elasticsearch 9.x (events only)
- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2, PostgreSQL 17 (alerts, incidents, cases, evidence, users, audit)
- Frontend: React 19, TypeScript (strict), Vite, Recharts, react-router
- Run: Docker Compose. Tests: pytest (backend), `tsc` + `vite build` (frontend)

## Map (where things live)
| Need | Path |
|---|---|
| Detection rules (YAML) | `backend/app/detections/rules/` |
| Rule loader + ES query compiler | `backend/app/services/rules.py` |
| Detection runner / correlation | `backend/app/services/detection.py`, `correlation.py` |
| Threat-intel enrichment | `backend/app/services/enrichment.py` |
| ES index template + ingest pipeline | `backend/app/services/es.py` (JSON copies in `infra/elasticsearch/`) |
| REST API | `backend/app/api/` ; models `backend/app/db/models.py` ; schemas `backend/app/schemas.py` |
| Demo/attack data | `backend/scripts/seed_data.py` |
| Dashboard | `frontend/src/pages/` ; API client `frontend/src/api.ts` |
| Docs | `docs/ARCHITECTURE.md`, `DATA_CONTRACT.md`, `PLAN.md`, `TESTING.md`, `DECISIONS.md`, `PROMPTS.md` |

`docs/BUILD_GUIDE.md` and `docs/OPENCODE_GUIDE.md` are long human-facing tutorials. Do NOT load them by default; open a single section only if a task needs it.

## Source-of-truth order (when things disagree)
1. `docs/DATA_CONTRACT.md` (field names, types, allowed values)
2. The tests
3. The code
4. `docs/BUILD_GUIDE.md` (explanatory only)
If you find a disagreement, STOP and report it; do not silently pick one.

## Commands
```bash
./scripts/verify.sh            # PREFERRED: backend tests + frontend build in one command; ends with "VERIFY: PASS" or "VERIFY: FAIL"
./scripts/integration.sh       # needs Docker stack running + .env: the 6-step real-stack checklist; ends with "INTEGRATION: PASS/FAIL"
docker compose up -d --build   # whole stack (needs .env, see .env.example)
docker compose exec -T backend python -m scripts.seed_data   # demo data + retro-hunt
```
Only the two scripts need to be run to verify work. They read secrets from `.env` themselves: you must never open or print `.env`.
OpenCode users: slash commands live in `.opencode/commands/`, the read-only reviewer in `.opencode/agents/`, config in `opencode.json`.

## Hard rules
1. **Never invent field names, event values, tactics, or severities.** Use only those in `docs/DATA_CONTRACT.md`.
   Need a new one? Follow the "Contract change procedure" in that file, in the same change.
2. **Verify before you claim.** A task is not done until you have RUN `./scripts/verify.sh`
   and pasted its real output. If you could not run something (no Docker, no Elasticsearch), say exactly that.
   Never write "verified" or "works" for anything you did not execute.
3. **Never weaken, delete or skip a test to make it pass.** Fix the code. If a test is wrong, explain why before changing it.
4. **Every new or changed detection rule needs a fixture test**: one event that must fire it, one near-miss that must not
   (pattern in `backend/tests/test_detection_correlation.py`, fake ES in `backend/tests/fake_es.py`).
5. **Every new API route**: add a role check (`require_role`), Pydantic validation, an audit entry for state changes,
   and tests for 401, 403 and the happy path.
6. **Security**: no secrets in code or commits (never touch `.env`); users never supply index names or raw ES query bodies;
   evidence is append-only (no edit/delete endpoints); uploaded files are never executed or trusted; no `eval`/`exec`/shell with user input.
7. **Ask before**: adding a dependency, changing a database table (there are no migrations yet), changing a public API shape,
   or touching Docker/Compose networking. Propose the change and wait.
8. **Small steps.** Work on ONE task from `docs/PLAN.md` at a time. Do not refactor unrelated code.
9. **Keep docs true.** In the same change: tick `docs/PLAN.md`, update `docs/DATA_CONTRACT.md` if fields changed,
   update `docs/TESTING.md` if verification changed. Stale docs are bugs.
10. **Lab and ethics.** Attack simulation is for isolated lab machines only. Never add real malware, exploit code,
    or features that scan or attack third-party systems. Never send internal or sensitive indicators to public threat-intel services.

## Conventions
- Python: type hints everywhere, small functions, FastAPI dependencies for auth/db, no business logic in routers beyond orchestration.
- Time: always timezone-aware UTC; ES timestamps are ISO-8601.
- Events may arrive with FLAT keys (`"host.name"`) or NESTED (`{"host": {"name": ...}}`): read them with `_dig` (Python) / `dig` (TypeScript).
- TypeScript: `strict`, no `any`, API calls only through `frontend/src/api.ts`.
- API prefix `/api/v1`. Commit messages: `type(scope): summary` (feat, fix, test, docs, chore).

## Working protocol for every task
1. Restate the task and list the files you expect to change. Check it against `docs/PLAN.md` and the contract.
2. Plan first for anything touching more than 2 files; wait for approval if it changes a contract, schema or API.
3. Write the failing test first when fixing a bug or adding a rule.
4. Implement, then run `./scripts/verify.sh`.
5. Finish with a **Verification report**: files changed, commands run with real pass/fail counts, what was NOT verified, and doc updates made.

## Definition of done
- `./scripts/verify.sh` prints `VERIFY: PASS` (backend tests including `tests/test_contract.py`, and the frontend build), no new warnings you introduced.
- Docs and `docs/PLAN.md` updated. Verification report written. Nothing claimed that was not run.

## Known limits (do not "fix" silently; discuss first)
500 groups per rule run; detection loop is in-process (single backend replica); no login rate limiting yet;
JWT in sessionStorage; Elasticsearch TLS off in dev compose; tables created with `create_all` (no Alembic yet).
