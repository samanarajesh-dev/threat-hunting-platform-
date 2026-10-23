---
description: Propose a commit message for the current changes
agent: build
---
Current changes:
!`git status --short`
!`git diff --stat | tail -20`

First confirm `./scripts/verify.sh` passed on this exact change; if you have not run it since the last edit, run it now.
Then propose ONE commit message in the form `type(scope): summary` (feat, fix, test, docs, chore) plus a short body.
Never include secrets or `.env`. Stage only the files that belong to this change, then ask me before running `git commit`. Never push.
