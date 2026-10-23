# Decisions log

Add a new entry whenever you choose between real alternatives. Format: Decision, Why, Trade-off, Revisit when.

| # | Decision | Why | Trade-off | Revisit when |
|---|---|---|---|---|
| 1 | Elasticsearch (not OpenSearch) | Beats work natively; ready-made Sysmon/syslog parsers | Vendor licence terms; swap needs a different shipper | OpenSearch required by a stakeholder |
| 2 | Alerts and incidents in PostgreSQL | Low volume, relational (cases, users, audit) | A second datastore to run | Alert volume exceeds ~1M rows |
| 3 | Rules are YAML compiled to ES aggregations | Scales with ES; analysts add rules without code | Limited expressiveness; sequences handled by correlation | Need true sequence/rarity detection (consider Sigma import) |
| 4 | In-process detection loop (thread) | Simplest thing that works for one developer | Only one backend replica may run | Scaling beyond one replica (move to a worker) |
| 5 | JWT in sessionStorage | Simple, no CSRF handling | Readable by XSS | Hardening phase (move to HttpOnly cookie) |
| 6 | `create_all` instead of migrations | Fast iteration early | Schema changes are manual | Before any real deployment (add Alembic) |
| 7 | Composite aggregation, page size 500 | One query per rule | Max 500 groups per run | A rule legitimately needs more groups |
| 8 | Fake ES in tests | Fast, no cluster needed | Does not prove ES accepts the DSL | Always pair with the real-ES checklist in TESTING.md |
| 9 | Correlation ignores noisy entities (`user:root`, ...) | Prevents gluing unrelated alerts | May miss a real shared-root story | Tuning phase |
