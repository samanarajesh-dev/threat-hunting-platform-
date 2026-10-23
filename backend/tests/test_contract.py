"""Triangulation: the data contract (docs/DATA_CONTRACT.md) is cross-checked against every place that uses field names.

If one of these fails, two parts of the system disagree about the data. Fix the drift (see the 'Contract change
procedure' in the contract) instead of deleting the check."""
import re
from datetime import datetime, timezone
from pathlib import Path

from app.services.es import INDEX_TEMPLATE, NORMALIZE_PIPELINE, PIVOT_FIELDS
from app.services.rules import ENTITY_TYPES, Rule, load_rules
from scripts.seed_data import generate_events

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_TEXT = (ROOT / "docs" / "DATA_CONTRACT.md").read_text(encoding="utf-8")
FRONTEND_SRC = ROOT / "frontend" / "src"


def template_fields() -> set[str]:
    out: set[str] = set()

    def walk(props: dict, prefix: str) -> None:
        for name, spec in props.items():
            if "properties" in spec:
                walk(spec["properties"], f"{prefix}{name}.")
            else:
                out.add(f"{prefix}{name}")

    walk(INDEX_TEMPLATE["template"]["mappings"]["properties"], "")
    return out


DOCUMENTED = set(re.findall(r"^\| `([^`]+)` \|", CONTRACT_TEXT, re.M))
VOCAB = {m.group(1): set(re.findall(r"`([^`]+)`", m.group(2)))
         for m in re.finditer(r"^- `(event\.\w+)`: (.+)$", CONTRACT_TEXT, re.M)}


def unknown_fields(fields) -> set[str]:
    return {f for f in fields if f not in DOCUMENTED}


def rule_fields(rule: Rule) -> set[str]:
    f = {c.field for c in rule.conditions + rule.any_of} | set(rule.group_by) | set(rule.extra_entity_fields)
    if rule.threshold.distinct:
        f.add(rule.threshold.distinct)
    if rule.watchlist:
        f.add(rule.watchlist.field)
    return f


def test_contract_document_matches_the_index_template_exactly():
    assert DOCUMENTED == template_fields(), (
        f"only in docs: {DOCUMENTED - template_fields()}; only in template: {template_fields() - DOCUMENTED}")


def test_vocabularies_are_documented():
    assert set(VOCAB) == {"event.category", "event.action", "event.outcome"}
    assert {"success", "failure"} == VOCAB["event.outcome"]


def test_every_rule_uses_only_contract_fields_and_values():
    for rule in load_rules(ROOT / "backend" / "app" / "detections" / "rules"):
        assert not unknown_fields(rule_fields(rule)), f"{rule.id} uses unknown fields {unknown_fields(rule_fields(rule))}"
        for c in rule.conditions + rule.any_of:
            if c.field in VOCAB:
                values = [c.equals] if c.equals is not None else (c.in_ or [])
                assert set(map(str, values)) <= VOCAB[c.field], f"{rule.id}: {c.field} has values outside the vocabulary: {values}"


def test_seed_data_uses_only_contract_fields_and_values():
    events = generate_events(datetime.now(timezone.utc))
    keys = {k for e in events for k in e if k != "@timestamp"}
    assert not unknown_fields(keys), f"seed data uses unknown fields {unknown_fields(keys)}"
    for field, allowed in VOCAB.items():
        used = {e[field] for e in events if field in e}
        assert used <= allowed, f"seed data uses {field} values outside the vocabulary: {used - allowed}"


def test_ingest_pipeline_writes_only_contract_fields_and_values():
    grok = next(p["grok"] for p in NORMALIZE_PIPELINE["processors"] if "grok" in p)
    captured = {c for pattern in grok["patterns"] for c in re.findall(r"%\{\w+:([\w.]+)(?::\w+)?\}", pattern)}
    assert captured and not unknown_fields(captured), f"grok captures unknown fields {unknown_fields(captured)}"

    script = next(p["script"] for p in NORMALIZE_PIPELINE["processors"] if "script" in p)["source"]
    puts = re.findall(r"ev\.put\('(\w+)','([^']*)'\)", script)
    assert puts
    for key, value in puts:
        assert f"event.{key}" in DOCUMENTED, f"pipeline sets unknown field event.{key}"
        assert value in VOCAB[f"event.{key}"], f"pipeline sets event.{key}='{value}' outside the vocabulary"


def test_entity_map_and_pivot_fields_are_contract_fields():
    assert not unknown_fields(ENTITY_TYPES), unknown_fields(ENTITY_TYPES)
    assert not unknown_fields({f for fields in PIVOT_FIELDS.values() for f in fields})


def test_frontend_reads_only_contract_fields():
    used = set()
    for path in FRONTEND_SRC.rglob("*.tsx"):
        used |= set(re.findall(r'dig\([^,()]+,\s*"([^"]+)"\)', path.read_text(encoding="utf-8")))
    assert used, "expected the frontend to read event fields through dig()"
    assert not unknown_fields(used), f"frontend reads unknown fields {unknown_fields(used)}"


def test_the_checker_itself_detects_drift():
    """Meta-test: prove these checks can fail, so a green run means something."""
    typo_rule = Rule.model_validate({"id": "X", "title": "t", "mitre": {"tactic": "Execution", "technique": "T1"},
                                     "conditions": [{"field": "hots.name", "equals": "a"}], "group_by": ["host.name"]})
    assert unknown_fields(rule_fields(typo_rule)) == {"hots.name"}
    assert "user_creatd" not in VOCAB["event.action"]
