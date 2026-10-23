# Plan and status (living tracker)

Work ONE unchecked task at a time, top to bottom. Tick a box only after its "Done when" check passes with real output.
`[x]` = done and verified by tests or a real run. `[~]` = written, but NOT yet verified against real services. `[ ]` = not started.

## Current state
- Backend logic, API, detection rules (against a fake ES), correlation, enrichment (mocked HTTP), reports: written and tested (56 tests).
- Frontend: type-checks and builds. Never opened in a browser yet.
- NOT yet run: `docker compose`, real Elasticsearch/Postgres, Filebeat, real threat-intel APIs.

## Phase 0 - Environment
- [~] Repo skeleton, `docker-compose.yml`, `.env.example`, Dockerfiles
- [ ] **Run the stack end to end** (`docker compose up -d --build`; all services healthy; `GET /health` ok)
  Done when: `docker compose ps` shows elasticsearch, postgres, backend running/healthy, and `./scripts/integration.sh` step 1 passes.

## Phase 1 - Ingestion and normalization
- [~] Index template + ingest pipeline `thp-normalize` + Filebeat config
- [ ] Verify the template and pipeline on real ES (`./scripts/integration.sh` steps 2-3)
- [ ] Seed data loads into real ES (step 4-5)
- [ ] Ship real logs from a lab VM with Filebeat; a failed SSH login appears with `event.outcome: failure`

## Phase 2 - Backend core
- [x] Config, models, JWT auth, roles, audit log (tested)
- [~] Search + pivot + stats endpoints (tested only for the "ES down" path; verify against real ES)
- [ ] Login rate limiting (listed under known limits in `AGENTS.md`)

## Phase 3 - Threat intelligence
- [x] Indicator typing, providers, cache, watchlist (tested with mocked HTTP)
- [ ] Verify with real VirusTotal / AbuseIPDB / OTX keys (a lookup returns a real verdict; a repeat is `cached: true`)
- [ ] Guard: never look up private/internal ranges on public services

## Phase 4 - Detection engineering
- [x] 10 rules, compiler, runner, dedupe (logic tested on the seeded attack)
- [~] Rules execute without error on real ES (`POST /detections/run?lookback_minutes=180` returns `errors: {}`)
- [ ] Write 3 new rules with fixtures (ideas: sudo root shell T1548.003, new service installed, DNS to rare TLD)

## Phase 5 - Correlation
- [x] Entity graph, incidents, risk score, idempotent re-run (tested)
- [ ] Tune on real lab data (check for false merges; adjust `NOISY_ENTITIES`)

## Phase 6 - Dashboard
- [x] 9 pages written; strict type-check and build pass
- [ ] Manual walkthrough in a browser: Overview -> Incident -> Case; no console errors
- [ ] Frontend tests (Vitest + Testing Library) for `api.ts` and one page

## Phase 7 - Cases, evidence, reports
- [x] Cases, append-only hashed evidence, findings, PDF/Markdown reports, chain of custody (tested)
- [ ] Verify a PDF from real seeded data looks right

## Phase 8 - Hardening and delivery
- [ ] Security gaps from `AGENTS.md` known limits (login rate limit, HttpOnly cookie, ES TLS, Alembic)
- [ ] Load test: index 1M events, time one detection cycle, record the number in `TESTING.md`
- [ ] Final README, 5-minute demo script, backup demo video

## Stretch (only after Phase 8)
Sigma import (pySigma) | host timeline page | incident graph view | Slack/email alerts | rarity-based anomaly rules | OTX feed -> watchlist | ATT&CK coverage heatmap
