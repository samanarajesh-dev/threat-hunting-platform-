"""Detection-rule format (a deliberately small, Sigma-inspired YAML dialect) + compiler.

A rule says: "in the last N minutes, find events matching these conditions, group them by these
fields, and raise an alert for every group that reaches the threshold".
The compiler turns that into ONE Elasticsearch aggregation query, so detection scales with ES,
not with Python."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

TACTIC_ORDER = [
    "Reconnaissance", "Resource Development", "Initial Access", "Execution", "Persistence",
    "Privilege Escalation", "Defense Evasion", "Credential Access", "Discovery",
    "Lateral Movement", "Collection", "Command and Control", "Exfiltration", "Impact",
]

# group-by / extra fields that identify an "entity" used later for correlation
ENTITY_TYPES = {
    "source.ip": "ip", "destination.ip": "ip", "host.name": "host", "user.name": "user",
    "dns.question.name": "domain", "file.hash.sha256": "sha256",
}

OPERATORS = ("equals", "in", "contains", "contains_any", "startswith", "endswith", "exists")


class Condition(BaseModel):
    field: str
    equals: str | int | bool | None = None
    in_: list[str | int] | None = Field(default=None, alias="in")
    contains: str | None = None
    contains_any: list[str] | None = None
    startswith: str | None = None
    endswith: str | None = None
    exists: bool | None = None
    negate: bool = False

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def exactly_one_operator(self):
        used = [op for op in OPERATORS if getattr(self, "in_" if op == "in" else op) is not None]
        if len(used) != 1:
            raise ValueError(f"condition on '{self.field}' needs exactly one operator from {OPERATORS}, got {used}")
        return self


class Mitre(BaseModel):
    tactic: str
    technique: str
    name: str = ""

    @field_validator("tactic")
    @classmethod
    def known_tactic(cls, v):
        if v not in TACTIC_ORDER:
            raise ValueError(f"unknown MITRE tactic '{v}'")
        return v


class Threshold(BaseModel):
    count: int = 1
    distinct: str | None = None  # count distinct values of this field instead of raw events


class Watchlist(BaseModel):
    ioc_type: str
    field: str


class Rule(BaseModel):
    id: str
    title: str
    description: str = ""
    severity: str = "medium"
    enabled: bool = True
    type: str = "match"  # match | watchlist
    lookback_minutes: int = 10
    suppress_minutes: int = 60
    conditions: list[Condition] = []
    any_of: list[Condition] = []
    group_by: list[str] = ["host.name"]
    threshold: Threshold = Threshold()
    extra_entity_fields: list[str] = []
    watchlist: Watchlist | None = None
    mitre: Mitre
    tags: list[str] = []

    @field_validator("severity")
    @classmethod
    def valid_severity(cls, v):
        if v not in ("low", "medium", "high", "critical"):
            raise ValueError("severity must be low|medium|high|critical")
        return v

    @model_validator(mode="after")
    def watchlist_rules_need_watchlist(self):
        if self.type == "watchlist" and not self.watchlist:
            raise ValueError("type: watchlist requires a 'watchlist' block")
        return self


# ---------------------------------------------------------------- compiler
def _escape_wildcard(v: str) -> str:
    return v.replace("\\", "\\\\").replace("*", "\\*").replace("?", "\\?")


def _wildcard(field: str, pattern: str) -> dict:
    return {"wildcard": {field: {"value": pattern, "case_insensitive": True}}}


def compile_condition(c: Condition) -> dict:
    f = c.field
    if c.equals is not None:
        if isinstance(c.equals, str):
            return {"term": {f: {"value": c.equals, "case_insensitive": True}}}
        return {"term": {f: c.equals}}
    if c.in_ is not None:
        return {"terms": {f: c.in_}}
    if c.contains is not None:
        return _wildcard(f, f"*{_escape_wildcard(c.contains)}*")
    if c.contains_any is not None:
        return {"bool": {"should": [_wildcard(f, f"*{_escape_wildcard(v)}*") for v in c.contains_any], "minimum_should_match": 1}}
    if c.startswith is not None:
        return _wildcard(f, f"{_escape_wildcard(c.startswith)}*")
    if c.endswith is not None:
        return _wildcard(f, f"*{_escape_wildcard(c.endswith)}")
    return {"exists": {"field": f}}  # exists


def build_search_body(rule: Rule, watchlist_values: list[str] | None = None, lookback_minutes: int | None = None) -> dict | None:
    """Return the ES request body for a rule, or None if the rule cannot run (e.g. empty watchlist).
    lookback_minutes overrides the rule default -- used for retro-hunting over older data."""
    window = lookback_minutes or rule.lookback_minutes
    filters: list[dict] = [{"range": {"@timestamp": {"gte": f"now-{window}m"}}}]
    must_not: list[dict] = []
    for c in rule.conditions:
        (must_not if c.negate else filters).append(compile_condition(c))
    if rule.any_of:
        filters.append({"bool": {"should": [compile_condition(c) for c in rule.any_of], "minimum_should_match": 1}})
    if rule.type == "watchlist":
        if not watchlist_values:
            return None
        filters.append({"terms": {rule.watchlist.field: watchlist_values}})

    sub_aggs: dict[str, Any] = {
        "first_seen": {"min": {"field": "@timestamp"}},
        "last_seen": {"max": {"field": "@timestamp"}},
        "samples": {"top_hits": {"size": 3, "sort": [{"@timestamp": "desc"}]}},
    }
    if rule.threshold.distinct:
        sub_aggs["distinct"] = {"cardinality": {"field": rule.threshold.distinct}}

    return {
        "size": 0,
        "query": {"bool": {"filter": filters, "must_not": must_not}},
        "aggs": {
            "groups": {
                "composite": {
                    "size": 500,
                    "sources": [{f"g{i}": {"terms": {"field": f}}} for i, f in enumerate(rule.group_by)],
                },
                "aggs": sub_aggs,
            }
        },
    }


# ---------------------------------------------------------------- loading
def load_rules(rules_dir: str | Path) -> list[Rule]:
    rules: list[Rule] = []
    seen: set[str] = set()
    for path in sorted(Path(rules_dir).glob("*.y*ml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        rule = Rule.model_validate(data)  # raises a clear error naming the bad rule
        if rule.id in seen:
            raise ValueError(f"duplicate rule id {rule.id} in {path.name}")
        seen.add(rule.id)
        rules.append(rule)
    return rules
