# Threat Hunting Platform

Collect security logs, hunt for threats, correlate alerts into attack stories, and document investigations with tamper-evident evidence.

```
Linux / Windows / Sysmon / Firewall / Apps
        -> Filebeat -> ingest pipeline (normalize) -> Elasticsearch
        -> detection engine (YAML rules) -> alerts -> correlation -> incidents
        -> FastAPI <-> PostgreSQL (cases, evidence, users, audit)  <-> threat-intel APIs
        -> React dashboard -> investigation + PDF reports
```

## Run it

```bash
cp .env.example .env            # edit passwords; JWT_SECRET=$(openssl rand -hex 32)
sudo sysctl -w vm.max_map_count=262144     # Linux (see docs/BUILD_GUIDE.md for Windows/Mac)
docker compose up -d --build
docker compose exec backend python -m scripts.seed_data
```

- Dashboard: http://localhost:3000 (user `admin`, password = `ADMIN_PASSWORD` in `.env`)
- API docs: http://localhost:8000/docs

## Verify it (no Docker needed)

```bash
./scripts/verify.sh        # 56 backend tests + strict frontend type-check and build; ends with VERIFY: PASS
./scripts/integration.sh   # needs the Docker stack running: 6-step real-stack check (not yet run against a real stack)
```

## Layout

| Path | What |
|---|---|
| `backend/app/detections/rules/` | Detection rules (YAML), start here |
| `backend/app/services/` | rules compiler, detection, correlation, enrichment, reports, Elasticsearch |
| `backend/app/api/` | REST endpoints |
| `backend/tests/` | 56 tests (+ `fake_es.py`, a tiny Elasticsearch stand-in) |
| `backend/scripts/seed_data.py` | Demo data: baseline traffic + a multi-stage attack |
| `frontend/src/pages/` | Dashboard pages |
| `infra/` | Filebeat config, index template, ingest pipeline |
| `docs/BUILD_GUIDE.md` | **Full build guide: read this first** |
| `docs/OPENCODE_GUIDE.md` | **End-to-end guide for building it with OpenCode** |
| `AGENTS.md`, `GEMINI.md`, `docs/*.md` | AI-agent context pack (shared by Antigravity and OpenCode) |
| `opencode.json`, `.opencode/` | OpenCode config, 10 slash commands, read-only `auditor` agent |
| `scripts/` | `verify.sh`, `integration.sh` |

## Status

Backend logic, API and frontend build are tested. The Docker stack, real Elasticsearch queries and Filebeat have **not** been run end to end yet: follow the integration checklist in `docs/BUILD_GUIDE.md` section 7.2 on your first run.

For authorized, lab use only. Attack and monitor only systems you own or have written permission to test.

## Building with Antigravity (AI agent)

Open this folder as the workspace. `AGENTS.md` (project rules) and `GEMINI.md` (Antigravity behaviour) are picked up automatically.
Paste the prompts from `docs/PROMPTS.md`, one small task at a time. `docs/DATA_CONTRACT.md` is the source of truth for field names;
`backend/tests/test_contract.py` cross-checks it against the rules, ingest pipeline, seed data and frontend.

## Building with OpenCode (AI agent)

Run `opencode` in this folder (it must be a Git repository). `AGENTS.md` loads automatically; `opencode.json` also loads the data contract and plan,
sets safe permissions (agent cannot read `.env`, push, or delete recursively) and `.opencode/commands/` adds `/kickoff`, `/task`, `/verify`,
`/integration`, `/review`, `/rule`, `/field`, `/debug`, `/docs-sync`, `/commit`. Full walkthrough, phase by phase: `docs/OPENCODE_GUIDE.md`.
