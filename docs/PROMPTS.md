# Prompts for Antigravity

Open the repository folder as the workspace so `AGENTS.md` and `GEMINI.md` load automatically. Prefer planning mode and review the
plan before the agent edits files. Paste these as they are; replace the `<...>` parts. One prompt = one task.

## 1. Kickoff (first message in a new workspace)
```
Read AGENTS.md, then docs/DATA_CONTRACT.md, docs/PLAN.md and docs/TESTING.md (do not open docs/BUILD_GUIDE.md).
Do not change any file yet. Then tell me:
1. What this project does, in 5 sentences.
2. The state of each phase from PLAN.md (done / written-not-verified / not started).
3. The first three unchecked tasks you would do, and what could go wrong in each.
4. Anything in the docs that contradicts the code or the tests.
```

## 2. First real run (Phase 0 and 1 integration)
```
Goal: run the stack for real and complete the "Integration checklist" in docs/TESTING.md, steps 1-6.
Use the terminal. For each step run the command, show the real output, and say PASS or FAIL.
Do not change code until you have a full list of failures. Then propose fixes, wait for my approval, apply them,
re-run, and update docs/PLAN.md. Never print or edit .env.
```

## 3. Standard task
```
Task: <one unchecked item from docs/PLAN.md>.
Follow the working protocol in AGENTS.md. Plan first and wait for approval if you touch more than 2 files.
Write the failing test first. Finish with a Verification report (files changed, real test/build results,
what was NOT verified, docs updated).
```

## 4. New detection rule
```
Add a detection rule for <behaviour> (MITRE <tactic>/<technique>). First show me a real example event and which contract fields
it needs. If a field or value is missing from docs/DATA_CONTRACT.md, stop and propose the contract change. Then: YAML rule,
fixture test (must-fire event + near-miss), run pytest, and update the rule table in docs.
```

## 5. New field or data source
```
Onboard <source>. Follow "Contract change procedure" in docs/DATA_CONTRACT.md exactly, in one change: contract row, index template
(regenerate infra JSON), pipeline mapping, seed data, affected rules and frontend. test_contract.py must pass without being weakened.
```

## 6. Triangulation review (use before every merge, ideally in a fresh conversation)
```
Act as a skeptical reviewer. Do not edit files. Cross-check these four sources against each other and list every disagreement:
docs/DATA_CONTRACT.md, the code (rules, pipeline, seed data, API, frontend), the tests, and docs/PLAN.md.
Also list: claims in PLAN.md that no test or real run supports, tests that could never fail, and any security rule in AGENTS.md that
the latest change violated. Rank findings by severity and quote file and line for each.
```

## 7. Debug a failure
```
<paste the exact error or failing test output>
Find the root cause before changing code. State your hypothesis, how you confirmed it (show the command and output),
then make the smallest fix. Add a regression test. Do not weaken any existing test.
```

## 8. Keep the docs true (end of a work session)
```
Update docs/PLAN.md, docs/DATA_CONTRACT.md, docs/TESTING.md and docs/DECISIONS.md to match what is now actually true in the repo.
Only mark [x] what has a passing test or a real run you showed me. List every change you made to the docs.
```

## Habits that make the agent reliable
- Give it one small task, not "build the platform". Review the plan, then the diff.
- Ask for the Verification report every time, and distrust any claim without pasted output.
- Run the Triangulation review (prompt 6) in a NEW conversation so it does not defend its own earlier work.
- When the agent repeats a mistake, add a one-line rule to `AGENTS.md` (keep the file under 12,000 characters).
