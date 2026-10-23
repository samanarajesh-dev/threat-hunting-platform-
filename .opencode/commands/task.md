---
description: Do ONE task from docs/PLAN.md using the full working protocol
agent: build
---
Task: $ARGUMENTS

Follow the working protocol and hard rules in AGENTS.md:
1. Quote the matching item(s) in docs/PLAN.md. If nothing matches, stop and ask me.
2. List the files you expect to change. If more than 2 files, or it touches the data contract, a database table or an API shape, show the plan and WAIT for my approval before editing.
3. For a bug or a new rule, write the failing test first.
4. Implement the smallest change that works.
5. Run `./scripts/verify.sh` and show its real output.
6. Update docs/PLAN.md, docs/DATA_CONTRACT.md and docs/TESTING.md if they are affected.
7. Finish with a Verification report: files changed, real pass/fail counts, what was NOT verified, docs updated.
Never claim something works unless you ran it.
