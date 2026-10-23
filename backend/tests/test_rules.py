import pytest
from pydantic import ValidationError

from app.services.rules import Condition, Rule, build_search_body, compile_condition, load_rules

RULES_DIR = "app/detections/rules"


def test_all_shipped_rules_load_and_compile():
    rules = load_rules(RULES_DIR)
    assert len(rules) == 10
    for r in rules:
        wl = ["x"] if r.type == "watchlist" else None
        body = build_search_body(r, wl)
        assert body["size"] == 0
        assert body["aggs"]["groups"]["composite"]["sources"]
        assert body["query"]["bool"]["filter"][0]["range"]["@timestamp"]["gte"] == f"now-{r.lookback_minutes}m"


def test_watchlist_rule_without_values_does_not_run():
    rule = next(r for r in load_rules(RULES_DIR) if r.type == "watchlist")
    assert build_search_body(rule, []) is None
    assert build_search_body(rule, None) is None


def test_lookback_override():
    rule = load_rules(RULES_DIR)[0]
    assert build_search_body(rule, lookback_minutes=180)["query"]["bool"]["filter"][0]["range"]["@timestamp"]["gte"] == "now-180m"


def test_condition_needs_exactly_one_operator():
    with pytest.raises(ValidationError):
        Condition(field="a", equals="x", contains="y")
    with pytest.raises(ValidationError):
        Condition(field="a")


def test_unknown_tactic_and_severity_rejected():
    base = {"id": "X", "title": "t", "mitre": {"tactic": "Execution", "technique": "T1"}}
    Rule.model_validate(base)
    with pytest.raises(ValidationError):
        Rule.model_validate({**base, "mitre": {"tactic": "Made Up", "technique": "T1"}})
    with pytest.raises(ValidationError):
        Rule.model_validate({**base, "severity": "apocalyptic"})


def test_wildcard_characters_in_values_are_escaped():
    q = compile_condition(Condition(field="process.command_line", contains="a*b?c"))
    assert q["wildcard"]["process.command_line"]["value"] == "*a\\*b\\?c*"


def test_negate_goes_to_must_not():
    r = Rule.model_validate({"id": "X", "title": "t", "mitre": {"tactic": "Execution", "technique": "T1"},
                             "conditions": [{"field": "a", "equals": "1"}, {"field": "b", "equals": "2", "negate": True}]})
    body = build_search_body(r)
    assert len(body["query"]["bool"]["must_not"]) == 1


def test_duplicate_rule_ids_rejected(tmp_path):
    for n in ("a.yml", "b.yml"):
        (tmp_path / n).write_text("id: DUP\ntitle: t\nmitre: {tactic: Execution, technique: T1}\n")
    with pytest.raises(ValueError, match="duplicate"):
        load_rules(tmp_path)
