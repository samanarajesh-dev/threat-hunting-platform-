---
description: Run the real-stack integration checklist (needs Docker up and a filled-in .env)
agent: plan
---
Real output of the integration checklist (it reads secrets from .env itself; never print or open .env):

!`./scripts/integration.sh`

Do not change any code yet. First list every FAIL with your diagnosis, classified as:
- environment (Docker not running, wrong port, missing .env value),
- configuration (compose, credentials, Filebeat),
- mapping or query (Elasticsearch rejected a field type or a query; name the rule or field),
- code defect.
Then propose the smallest fix for each, in order, and WAIT for my approval. After I approve and you apply a fix, I will re-run /integration.
Update docs/PLAN.md only for steps that actually PASSED in the output above.
