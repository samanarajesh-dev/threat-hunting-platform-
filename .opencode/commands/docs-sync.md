---
description: Make the docs match what is actually true in the repo (end of a work session)
agent: build
---
Recent history:
!`git log --oneline -10`
!`git status --short | head -30`

Update docs/PLAN.md, docs/DATA_CONTRACT.md, docs/TESTING.md and docs/DECISIONS.md to match what is now true.
Mark `[x]` ONLY what has a passing test or a real run you can point to. Use `[~]` for written-but-unverified. List every doc change you made.
