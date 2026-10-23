---
description: Triangulation review by the read-only auditor, in a separate context (use before every merge)
agent: auditor
subtask: true
---
Review the current state of the repository. Focus: $ARGUMENTS

Changes in progress:
!`git status --short | head -30`
!`git diff --stat | tail -15`

Cross-check docs/DATA_CONTRACT.md, the code, the tests and docs/PLAN.md against each other, as described in your instructions.
Return the ranked findings and the "Not verified:" list. Do not edit files.
