# GEMINI.md - Antigravity-specific behaviour

Follow `AGENTS.md` in this folder first; it holds the project rules. This file only adds how to work well inside Antigravity.
If anything here conflicts with `AGENTS.md`, ask me instead of guessing.

- **Plan before acting** on any task that touches more than 2 files, changes an API, a schema or a contract.
  Show the plan and wait for my approval.
- **Verification is mandatory.** Use the terminal to run the commands listed in `AGENTS.md`. Attach the real output
  (test counts, build result) to your final Verification report. If a command cannot run, state why.
- **UI changes:** after changing `frontend/`, also check the page in the integrated browser if available
  (login as an analyst, open the page, confirm it renders and the console has no errors). Report what you saw.
- **Terminal safety:** never run destructive commands (`rm -rf`, `docker compose down -v`, dropping databases) without asking.
  Never print, read or commit `.env`.
- **Context discipline:** read only the files you need. Prefer `docs/DATA_CONTRACT.md` and `docs/PLAN.md` over exploring the repo.
- **Tell me when you are unsure** instead of inventing an answer. A wrong guess costs more than a question.
- Use `docs/PROMPTS.md` for the standard task, review and debugging prompts I will give you.
