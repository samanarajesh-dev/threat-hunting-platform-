# Building the Threat Hunting Platform with OpenCode: End-to-End Guide

How to take this repository from "starter code" to a finished, verified platform using OpenCode (an open-source terminal AI coding agent), one small, checked step at a time.

**Who this is for:** you, driving an AI agent. The agent writes code; you decide, review and verify.

---

## 0. Read this first

### What is verified, and what is not

| Item | Status |
|---|---|
| Config and file formats (`opencode.json`, command and agent Markdown files, permission syntax, `AGENTS.md` loading) | Written against OpenCode's published docs (pages dated mid-October 2026). Files validated for syntax. **Not yet run inside a real OpenCode session** |
| `scripts/verify.sh` (backend tests + frontend build) | **Run for real:** 56 tests pass, build OK |
| `scripts/integration.sh` (6-step real-stack check) | Control flow tested against a mock server (healthy, broken, no stack). **Never run against real Docker/Elasticsearch** |
| Backend logic, API, rules, correlation, enrichment | 56 automated tests pass |
| Docker stack, real Elasticsearch, Filebeat, browser UI | **Not run yet.** Phase 0 below does this |

OpenCode changes quickly. Its docs currently describe two config generations (a "v2" uses different key names). This pack targets the documented stable format (`permission`, `agent`, `command`). If OpenCode complains about a key, run `opencode debug config` and compare with the schema at `https://opencode.ai/config.json`.

### The idea in one paragraph

AI agents drift when they work from one-off prompts: they forget decisions, guess field names and claim success without running anything. This pack gives OpenCode persistent memory (`AGENTS.md` plus the data contract and plan), one-command verification (`scripts/verify.sh`), tight permissions, ready-made slash commands, and an independent read-only reviewer. Then you feed it one small task at a time.

---

## 1. How OpenCode works (the five concepts you need)

| Concept | What it means for this project |
|---|---|
| **Agents** | Built-in `plan` (analyses, does not edit) and `build` (edits and runs commands). Custom agents live in `.opencode/agents/`. We add `auditor`, a **read-only subagent** used for review |
| **Rules** | OpenCode reads `AGENTS.md` from the project root into every session. It does **not** auto-follow file references inside it, so the data contract and plan are loaded through the `instructions` list in `opencode.json` instead |
| **Commands** | Markdown files in `.opencode/commands/`. The file name becomes the slash command (`/task`, `/verify` ...). `$ARGUMENTS` is what you type after the command; a line like `!` + backticked shell command injects its output; `@file` includes a file |
| **Permissions** | `opencode.json` decides per action whether to `allow`, `ask` or `deny`. Patterns use `*` wildcards; the **last matching rule wins** |
| **Sessions and undo** | Each conversation is a session (`/new`, `/sessions`). `/undo` and `/redo` revert the last message **and its file changes**, and rely on Git, so the project **must be a Git repository** |

`GEMINI.md` (from the Antigravity pack) is simply ignored by OpenCode. Everything else in the repo is shared by both tools.

---

## 2. Install and connect

1. **Install OpenCode** using the method shown at `https://opencode.ai` (a one-line installer script is the common route). On Windows, use WSL (OpenCode has a Windows/WSL page in its docs) and work inside the Linux filesystem.
2. Check it runs: `opencode --version`.
3. Start it once inside any folder and run **`/connect`** to add your model provider and API key.
4. Run **`/models`** to pick a model.

**Choosing a model:** this project edits several files at once and must keep a data contract consistent, so use a strong coding model for `/task`, `/rule`, `/field` and `/debug`. Small or weak local models tend to lose track across files. A command can override the model in its frontmatter (`model: provider/model-name`), which lets you give cheap commands such as `/verify` a cheaper model.

**Cost control:** keep sessions short, one task per session, run `/new` between tasks, and `/compact` if a session gets long.

---

## 3. Prepare your machine

| Need | Check |
|---|---|
| Docker with Compose v2, at least 4 GB RAM for Docker | `docker compose version` |
| Python 3.12 | `python3 --version` |
| Node 22 | `node --version` |
| Git | `git --version` |
| Elasticsearch kernel setting (Linux) | `sudo sysctl -w vm.max_map_count=262144` (Windows/WSL2 and macOS: see `docs/BUILD_GUIDE.md`, Troubleshooting) |

---

## 4. Set up the project

```bash
unzip threat-hunting-platform.zip && cd threat-hunting-platform
git init && git add -A && git commit -m "chore: import starter project"     # /undo needs a Git repo
cp .env.example .env                                                       # edit it yourself (see below)
```

Edit `.env` **in your own editor**, not through the agent:

- `ELASTIC_PASSWORD`, `POSTGRES_PASSWORD`: letters and digits only (special characters break the database URL).
- `JWT_SECRET`: output of `openssl rand -hex 32`.
- `ADMIN_PASSWORD`: your first login password.
- Threat-intel keys (`VT_API_KEY`, `ABUSEIPDB_API_KEY`, `OTX_API_KEY`) are optional.

Start OpenCode and confirm it loaded the project config:

```bash
opencode              # starts the TUI in this folder
opencode debug config # shows the resolved configuration (run in another terminal)
```

**`.env` is protected:** `opencode.json` denies the agent reading or editing `.env` files, and denies any shell command that mentions `.env` (for example `cat .env`, `grep x .env`, `git add .env`), except `.env.example`. The two scripts read `.env` themselves and never print secrets, so the agent can verify things without ever seeing a password.

---

## 5. What is in the pack

| File | Purpose |
|---|---|
| `AGENTS.md` | Project rules: stack, commands, 10 hard rules, working protocol, definition of done (about 6,200 characters) |
| `opencode.json` | Always-loaded docs (`DATA_CONTRACT.md`, `PLAN.md`), permissions, default agent `plan`, sharing disabled |
| `.opencode/commands/*.md` | 10 slash commands (table below) |
| `.opencode/agents/auditor.md` | Read-only reviewer subagent |
| `scripts/verify.sh` | One command: backend tests + frontend build, ends with `VERIFY: PASS` or `VERIFY: FAIL` |
| `scripts/integration.sh` | One command: the 6-step real-stack checklist, ends with `INTEGRATION: PASS` or `FAIL` |
| `docs/DATA_CONTRACT.md` | Source of truth for field names and values, with the change procedure |
| `docs/PLAN.md` | Living tracker of what is done, written-but-unverified, and not started |
| `docs/TESTING.md`, `ARCHITECTURE.md`, `DECISIONS.md` | Verification guide, system boundaries, reasons for choices |
| `backend/tests/test_contract.py` | Automated cross-check: contract vs template, rules, pipeline, seed data, frontend |
| `.github/workflows/verify.yml` | Runs `verify.sh` on every push (no AI involved) |

### The slash commands

| Command | Agent | Use it to |
|---|---|---|
| `/kickoff` | plan | Orient at the start of a session: status, risks, next tasks. No edits |
| `/task <PLAN item>` | build | Do ONE task with the full protocol (plan, test first, verify, update docs, report) |
| `/verify` | build | Run `verify.sh` and interpret it; root-cause any failure |
| `/integration` | plan | Run the real-stack checklist, classify failures, propose fixes, wait for approval |
| `/review <focus>` | auditor (subtask) | Independent triangulation review in a separate context |
| `/rule <behaviour>` | build | Add a detection rule with a must-fire and a must-not-fire test |
| `/field <change>` | build | Change the data contract the correct way |
| `/debug <problem>` | build | Hypothesis, failing regression test, minimal fix |
| `/docs-sync` | build | Make the docs match reality at the end of a session |
| `/commit` | build | Propose a commit message and stage the right files (never pushes) |

---

## 6. The working loop

Repeat this for every task. One task per session.

```
/new                       fresh session (clean context)
/kickoff                   only at the start of a work day, or when you feel lost
/task <one PLAN.md item>   agent plans; you read the plan; approve or correct it
    ... agent edits ...
git diff                   YOU read the diff (type:  !git diff --stat   inside OpenCode)
/verify                    must end in VERIFY: PASS
/review <what changed>     independent auditor; fix anything critical or high
/docs-sync                 only if the agent did not already update PLAN.md
/commit                    review the message, confirm the commit
```

Rules of thumb:

- **Plan first.** If the plan touches the contract, a database table or an API, read it carefully before approving. These are the expensive mistakes.
- **No claim without output.** If the agent says "tests pass" and there is no pasted `VERIFY: PASS`, run `/verify` yourself.
- **Small steps.** If a task needs more than about five files, split it.
- **Undo is cheap.** `/undo` reverts the last message and its file changes. Commit often so you always have a safe point.

---

## 7. Build it phase by phase

Tick items in `docs/PLAN.md` only when their "done when" check passes. Each phase lists what to type, then what **you** check yourself.

### Phase 0: First real run (Week 1)

Open a second terminal for Docker (you run it; the agent should not start your stack unattended):

```bash
sudo sysctl -w vm.max_map_count=262144
docker compose up -d --build
docker compose ps
```

In OpenCode:

```
/kickoff
/integration
```

If steps fail, read the agent's diagnosis, approve fixes one at a time, apply, and type `/integration` again until it prints `INTEGRATION: PASS`.

**You verify:** open `http://localhost:3000`, sign in as `admin`, and see 2 incidents and 10 alerts on the Overview page. Then `/docs-sync` and `/commit`.

### Phase 1: Ingestion and normalization (Weeks 2 to 3)

```
/task Phase 1: create infra/filebeat/lab-vm.yml, a standalone Filebeat config for an Ubuntu VM that ships /var/log/auth.log to my Elasticsearch through the thp-normalize pipeline, and document how to validate it with "filebeat test config" and "filebeat test output"
```

**You verify (manual lab work):** install Filebeat on your lab VM, make a wrong SSH password attempt, and find the event on the Hunt page with `event.outcome: failure` and the right `source.ip`. Then run `sudo useradd testuser` and edit a crontab, and confirm both appear.

### Phase 2: Backend core (Week 3)

```
/task Phase 2: verify the search, pivot and stats endpoints against real Elasticsearch with the seeded data. List every defect first, then fix each with a regression test
/task Phase 2: add login rate limiting, 5 failed attempts per username per 15 minutes returns HTTP 429, with tests for lockout, reset after the window, and that valid users are not affected
```

**You verify:** on `/docs`, search for `host.name:web01` and pivot on `198.51.100.77`; five bad passwords then a good one returns 429.

### Phase 3: Threat intelligence (Week 4)

```
/task Phase 3: never send private, loopback, link-local or reserved IP addresses to public threat-intel providers. Return verdict "internal" with an explanatory message, show it in the Indicators page, add tests
```

**You verify:** add your free API keys to `.env`, restart the backend (`docker compose up -d --build backend`), look up a public IP, see a real verdict, then look it up again and see "served from cache". Check each provider's current free-tier limits first.

### Phase 4: Detection engineering (Week 5)

```
/rule sudo used to open an interactive root shell (T1548.003)
/field add the event.action value "service_created" and map Linux systemd unit installs to it in the normalization pipeline
/rule new systemd service installed (T1543.002)
```

The second command deliberately exercises the contract change procedure. Watch `test_contract.py`: it should fail if the agent forgets to update the template or documentation.

**You verify:** generate each behaviour on your lab VM and confirm the alert appears. Record it in a detection coverage table (attack, rule, fired?, time to alert).

### Phase 5: Correlation (Weeks 5 to 6)

```
/task Phase 5: run a full attack from the lab, then inspect the incidents for false merges or missed links. Adjust NOISY_ENTITIES or the window only with a test that captures the case
/review correlation logic and its tests
```

**You verify:** one attack equals one incident; an unrelated alert on another host stays separate.

### Phase 6: Dashboard (Week 6)

```
/task Phase 6: add Vitest and Testing Library, with tests for frontend/src/api.ts (token handling, 401 redirect) and the Alerts page (status change, error state)
```

The agent will ask before installing dependencies (`npm install` is set to `ask`); approve it.

**You verify (the agent cannot do this for you):** in a browser, go Overview, then an incident, then open a case, add a finding and a file, and download the PDF. Check the browser console for errors.

### Phase 7: Cases, evidence, reports (Week 7)

```
/task Phase 7: add a case timeline view that merges the audit trail with linked alert times, with tests
```

**You verify:** open the PDF from a real seeded case; check the layout, the SHA-256 table and that no text is cut off.

### Phase 8: Hardening and delivery (Week 8)

One task per session, plan first:

```
/task Phase 8: replace sessionStorage JWT with an HttpOnly, SameSite cookie and add CSRF protection (plan first, this touches backend and frontend)
/task Phase 8: enable TLS on Elasticsearch in docker-compose and make the Python client verify certificates
/task Phase 8: add Alembic migrations and an initial migration matching the current models
/task Phase 8: write a load test that indexes 1,000,000 events and times one detection cycle; record the numbers in docs/TESTING.md
/review the whole repository, focus on security and unverified claims
/docs-sync
```

**You verify:** run a full dress rehearsal of the 5-minute demo from `docs/BUILD_GUIDE.md`, record a backup video, and answer the reviewer questions in `docs/BUILD_GUIDE.md` section 10 out loud.

---

## 8. Keeping the agent honest: the triangulation toolkit

Three independent layers, because any one can fail.

| Layer | What | Where |
|---|---|---|
| **Automated** | `test_contract.py` compares the contract against the index template, every rule, the ingest pipeline, the seed data, the entity map and the frontend. `verify.sh` runs it every time | `backend/tests/` |
| **Independent AI** | `/review` runs the read-only `auditor` in a separate context, so it does not defend work from your session. It cross-checks contract, code, tests and plan, and flags unsupported `[x]` ticks and tests that cannot fail | `.opencode/agents/auditor.md` |
| **You** | Read every plan and diff; do the manual checks listed per phase | this guide |

**Habit worth building: break it on purpose.** After a change, deliberately introduce one typo (a misspelled field in a rule, a deleted contract row) and confirm `./scripts/verify.sh` goes red. A check you have never seen fail may not be checking anything.

**When the agent repeats a mistake:** add one short line to `AGENTS.md` (keep it under 12,000 characters), commit it, and start a new session. That is how the project's memory improves.

---

## 9. Controlling the agent safely

### What `opencode.json` does

| Setting | Effect |
|---|---|
| `"default_agent": "plan"` | Sessions start in the read-only agent; commands that edit say `agent: build` |
| `"instructions": [DATA_CONTRACT, PLAN]` | The contract and plan are always in context |
| `read` / `edit` deny `*.env`, `*.env.*`; `bash` denies any command mentioning `.env` | The agent cannot read, change, or commit secrets (`.env.example` is allowed) |
| `edit` deny `evidence/*` | Uploaded evidence files are never touched |
| `bash` default `ask` | Unknown commands prompt you |
| `bash` allow | `git status/diff/log/add`, the two scripts, pytest, `npm run build`, `docker compose ps/logs` |
| `bash` deny | `git push`, `git reset --hard`, `git clean`, `rm -rf`, `sudo`, `docker compose down -v`, `docker compose config` (prints secrets) |
| `"share": "disabled"` | Session sharing off (sessions can contain code and logs) |

When a prompt appears you can approve `once`, `always` (for the rest of that session) or `reject`.

### Know the limits

- **Permissions are guardrails, not a sandbox.** A clever shell command can still do unexpected things. For strong isolation, run OpenCode in a VM or dev container.
- **`opencode --auto`** auto-approves anything not explicitly denied. Explicit `deny` rules still apply, but do not use auto mode on this project until you trust the workflow, and never with the Docker stack holding data you care about.
- **Review new dependencies.** The agent proposes `npm install` and `pip install`; check the package name for typos and that you actually need it.
- **Lab ethics.** Attack simulation only against machines you own. The rules in `AGENTS.md` forbid the agent from adding offensive tooling.

### When things go wrong in a session

| Symptom | Do this |
|---|---|
| Agent invents a field or value | Point at `docs/DATA_CONTRACT.md`; if truly needed, use `/field`. Run `/verify`: `test_contract.py` should catch it |
| Agent edits a test to make it pass | `/undo`. Re-run the task and remind it: fix the code, never weaken tests (rule 3) |
| Agent loops on the same failing call | OpenCode has a repeat-call guard (`doom_loop`); stop, `/new`, restate the task smaller |
| Context is long and answers degrade | `/compact`, or better `/new` and re-run `/kickoff` |
| Scope creep (touches unrelated files) | `/undo`, then re-run `/task` with a smaller item |
| Agent says "done" with no output | Run `/verify` yourself; treat the claim as false until `VERIFY: PASS` is shown |

---

## 10. Automation and CI

- **CI without AI:** `.github/workflows/verify.yml` runs `./scripts/verify.sh` on every push. Push the repo to GitHub and the check appears automatically (unverified here: not yet run on GitHub).
- **Headless runs:** OpenCode can run a single prompt non-interactively with `opencode run "<prompt>"`. Keep this for read-only questions (for example "list the unchecked Phase 4 tasks in docs/PLAN.md") until you fully trust your permissions.

---

## 11. Optional advanced exercise: rebuild from the specs

If your mentor wants the platform written "from scratch" by the agent:

1. Copy the repo. Keep `docs/`, `AGENTS.md`, `opencode.json`, `.opencode/`, `scripts/`, `backend/tests/` and `frontend/package.json`.
2. Delete the implementation: `backend/app/` (keep the YAML rules) and `frontend/src/`.
3. Ask the agent, phase by phase, to implement code until `./scripts/verify.sh` passes, using the tests and the contract as the specification.
4. Expect it to need the frontend rewritten against `docs/ARCHITECTURE.md` since there are no frontend tests yet (add them in Phase 6 first).

This works because the tests are an executable specification. It is slower than extending the starter code, so do it only if required.

---

## 12. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `opencode: command not found` | Open a new shell after installing, or add the install directory to `PATH`. On Windows use WSL |
| Slash commands do not appear | They must be in `.opencode/commands/*.md` (plural). Restart OpenCode in the project root |
| Agent ignores `AGENTS.md` | Start a new session; confirm the file is at the repo root; run `opencode debug config` |
| `/undo` does nothing | The folder is not a Git repo: run `git init` and commit |
| Constant permission prompts | Add an `allow` pattern for that command in `opencode.json`. Remember: the last matching rule wins, and `"grep *"` allows arguments while `"grep"` alone does not |
| A script command is still asked about | Chained commands (`cd x && y`) are parsed into parts. Prefer the single scripts `./scripts/verify.sh` and `./scripts/integration.sh` |
| `opencode.json` key rejected | Your OpenCode may use the newer schema. Compare with `https://opencode.ai/config.json` and `opencode debug config` |
| `./scripts/verify.sh: Permission denied` | `chmod +x scripts/*.sh` |
| A harmless command is denied | The `.env` guard matches anything containing `.env` (even `process.env` in a grep). Run it yourself with `!` or rephrase it |
| `integration.sh` step 1 fails | Services are not running: `docker compose up -d --build`, wait for Elasticsearch to become healthy |
| `integration.sh` step 6 cannot log in | `ADMIN_PASSWORD` must have been set the first time the backend started; otherwise create a user through the API or reset the database volume (your decision, not the agent's) |
| Model errors or rate limits | Check `/models`, your provider's limits, or switch model for cheap commands |

---

## 13. Cheat sheet

| I want to | Type |
|---|---|
| Start a clean session | `/new` |
| Orient myself | `/kickoff` |
| Work one task | `/task <exact PLAN.md item>` |
| Check everything | `/verify` |
| Test against the real stack | `/integration` |
| Independent review | `/review <focus>` |
| Add a detection | `/rule <behaviour (MITRE id)>` |
| Change the data model of events | `/field <change>` |
| Fix something broken | `/debug <exact error>` |
| Sync the docs | `/docs-sync` |
| Commit | `/commit` |
| Run a shell command inside OpenCode | `!git diff --stat` |
| Include a file in a message | `@docs/PLAN.md` |
| Undo the last agent message and its edits | `/undo` (then `/redo` to restore) |
| Shrink a long session | `/compact` |
| Add a provider / pick a model | `/connect`, `/models` |
