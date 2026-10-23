---
description: Run the full verification (backend tests + frontend build) and interpret it
agent: build
---
Real output of the verification script:

!`./scripts/verify.sh`

If it says VERIFY: PASS, summarize the counts in two lines and stop.
If it says VERIFY: FAIL, find the ROOT CAUSE before changing anything: state your hypothesis and how you confirmed it.
Then make the smallest fix and re-run `./scripts/verify.sh`. Never weaken, skip or delete a test to get green.
If a test is genuinely wrong, explain why and wait for my approval.
