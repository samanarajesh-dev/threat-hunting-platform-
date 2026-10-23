---
description: Root-cause a failure, fix it minimally, add a regression test
agent: build
---
Problem: $ARGUMENTS

1. Do not change code yet. State your hypothesis and confirm it with a command or by reading the relevant code. Show the evidence.
2. Write a failing regression test that reproduces it.
3. Make the smallest fix. Do not refactor unrelated code. Never weaken an existing test.
4. Run `./scripts/verify.sh` and show the real output.
5. Add a one-line lesson to AGENTS.md ONLY if this mistake could plausibly repeat, and keep that file under 12,000 characters.
