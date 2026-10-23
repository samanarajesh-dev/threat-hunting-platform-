---
description: Add or change a data-contract field or source, following the change procedure
agent: build
---
Contract change: $ARGUMENTS

Follow "Contract change procedure" in docs/DATA_CONTRACT.md exactly, all in ONE change:
contract row and vocabulary line, INDEX_TEMPLATE in backend/app/services/es.py (then regenerate infra/elasticsearch/*.json),
ingest pipeline if it is parsed from raw logs, seed data, affected rules, and the frontend.
backend/tests/test_contract.py must pass WITHOUT being weakened. Plan first and wait for my approval, then run `./scripts/verify.sh`
and finish with a Verification report.
