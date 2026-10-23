---
description: Add a new detection rule with fixture tests
agent: build
---
Add a detection rule for: $ARGUMENTS

1. Show me a realistic example event and the data-contract fields it needs. If a field or value is missing from docs/DATA_CONTRACT.md, STOP and propose the contract change first.
2. Create the YAML rule in backend/app/detections/rules/ (next free THP-0xx id) with a correct MITRE tactic and technique.
3. Add fixture tests: one event that MUST fire it and one near-miss that must NOT (pattern in backend/tests/test_detection_correlation.py, fake ES in backend/tests/fake_es.py).
4. Run `./scripts/verify.sh`, including backend/tests/test_contract.py, and show the real output.
5. Update the rule table in docs/BUILD_GUIDE.md and tick docs/PLAN.md. Finish with a Verification report.
