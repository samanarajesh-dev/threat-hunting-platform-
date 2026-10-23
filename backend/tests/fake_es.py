"""A tiny in-memory stand-in for Elasticsearch.

It understands exactly the query subset our rule compiler emits (bool/term/terms/wildcard/exists/range
+ a composite aggregation with min/max/top_hits/cardinality). That lets us test *rule logic* against the
seeded attack scenario without a running cluster. It does NOT prove ES accepts the DSL -- the
integration step in the guide (run against a real ES) covers that."""
import re
from datetime import datetime, timedelta, timezone


def get(doc, field):
    if field in doc:
        return doc[field]
    cur = doc
    for part in field.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _wild_to_re(pattern: str, ci: bool):
    out, i = "", 0
    while i < len(pattern):
        c = pattern[i]
        if c == "\\" and i + 1 < len(pattern):
            out += re.escape(pattern[i + 1]); i += 2; continue
        out += ".*" if c == "*" else "." if c == "?" else re.escape(c)
        i += 1
    return re.compile("^" + out + "$", re.I if ci else 0)


class FakeES:
    def __init__(self, events, now):
        self.events, self.now = events, now

    def _ts(self, doc):
        return datetime.fromisoformat(doc["@timestamp"])

    def _match(self, doc, clause) -> bool:
        (kind, body), = clause.items()
        if kind == "range":
            gte = body["@timestamp"]["gte"]
            m = re.fullmatch(r"now-(\d+)m", gte)
            return self._ts(doc) >= self.now - timedelta(minutes=int(m.group(1)))
        if kind == "term":
            (field, spec), = body.items()
            val, ci = (spec["value"], spec.get("case_insensitive")) if isinstance(spec, dict) else (spec, False)
            got = get(doc, field)
            if got is None:
                return False
            return str(got).lower() == str(val).lower() if ci else str(got) == str(val)
        if kind == "terms":
            (field, vals), = body.items()
            got = get(doc, field)
            return got is not None and str(got) in {str(v) for v in vals}
        if kind == "wildcard":
            (field, spec), = body.items()
            got = get(doc, field)
            return got is not None and bool(_wild_to_re(spec["value"], spec.get("case_insensitive", False)).match(str(got)))
        if kind == "exists":
            return get(doc, body["field"]) is not None
        if kind == "bool":
            if not all(self._match(doc, c) for c in body.get("filter", []) + body.get("must", [])):
                return False
            if any(self._match(doc, c) for c in body.get("must_not", [])):
                return False
            should = body.get("should", [])
            return not should or any(self._match(doc, c) for c in should)
        raise NotImplementedError(kind)

    def search(self, index=None, timeout=None, size=0, query=None, aggs=None, **_):
        docs = [d for d in self.events if self._match(d, query)]
        comp = aggs["groups"]["composite"]
        fields = [list(s.values())[0]["terms"]["field"] for s in comp["sources"]]
        groups: dict[tuple, list] = {}
        for d in docs:
            key = tuple(get(d, f) for f in fields)
            if any(k is None for k in key):
                continue
            groups.setdefault(key, []).append(d)
        buckets = []
        for key, members in groups.items():
            members.sort(key=self._ts, reverse=True)
            ms = lambda d: self._ts(d).timestamp() * 1000  # noqa: E731
            b = {"key": {f"g{i}": k for i, k in enumerate(key)}, "doc_count": len(members),
                 "first_seen": {"value": min(ms(d) for d in members)}, "last_seen": {"value": max(ms(d) for d in members)},
                 "samples": {"hits": {"hits": [{"_source": d} for d in members[:3]]}}}
            sub = aggs["groups"]["aggs"]
            if "distinct" in sub:
                b["distinct"] = {"value": len({get(d, sub["distinct"]["cardinality"]["field"]) for d in members})}
            buckets.append(b)
        return {"aggregations": {"groups": {"buckets": buckets}}}
