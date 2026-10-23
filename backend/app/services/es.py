"""Thin Elasticsearch wrapper: client factory, index template, and the read-only queries the API needs."""
from __future__ import annotations

import logging
from functools import lru_cache

from elasticsearch import Elasticsearch

from app.core.config import get_settings

log = logging.getLogger("thp.es")

# Fields searched when pivoting on an indicator, by type.
PIVOT_FIELDS = {
    "ip": ["source.ip", "destination.ip", "host.ip"],
    "domain": ["dns.question.name", "url.domain"],
    "url": ["url.full"],
    "md5": ["file.hash.md5"], "sha1": ["file.hash.sha1"], "sha256": ["file.hash.sha256"],
}

# The index template is the schema contract between the collectors and everything downstream.
INDEX_TEMPLATE = {
    "index_patterns": ["thp-events-*"],
    "priority": 300,
    "template": {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "dynamic": True,
            "properties": {
                "@timestamp": {"type": "date"},
                "message": {"type": "text"},
                "event": {"properties": {k: {"type": "keyword"} for k in ("category", "action", "outcome", "code", "dataset")}},
                "host": {"properties": {"name": {"type": "keyword"}, "ip": {"type": "ip"}, "os": {"properties": {"type": {"type": "keyword"}}}}},
                "user": {"properties": {"name": {"type": "keyword"}}},
                "source": {"properties": {"ip": {"type": "ip"}, "port": {"type": "integer"}}},
                "destination": {"properties": {"ip": {"type": "ip"}, "port": {"type": "integer"}}},
                "process": {"properties": {
                    "name": {"type": "keyword"}, "pid": {"type": "long"},
                    "command_line": {"type": "wildcard"},
                    "parent": {"properties": {"name": {"type": "keyword"}}},
                }},
                "file": {"properties": {"hash": {"properties": {k: {"type": "keyword"} for k in ("md5", "sha1", "sha256")}}}},
                "dns": {"properties": {"question": {"properties": {"name": {"type": "keyword"}}}}},
                "url": {"properties": {"full": {"type": "wildcard"}, "domain": {"type": "keyword"}}},
                "winlog": {"properties": {"event_data": {"properties": {"TargetImage": {"type": "wildcard"}}}}},
                "thp": {"properties": {"auth_method": {"type": "keyword"}}},
            },
        },
    },
}


# Normalisation: turns raw syslog lines into the THP field contract (event.category/outcome/action, user.name, source.ip ...).
# Test it WITHOUT touching real data:  POST _ingest/pipeline/thp-normalize/_simulate  (see docs/BUILD_GUIDE.md).
NORMALIZE_PIPELINE = {
    "description": "THP: normalise sshd / useradd / crontab syslog lines to the THP field contract",
    "processors": [
        {"grok": {"field": "message", "ignore_missing": True, "ignore_failure": True, "patterns": [
            "Failed password for (invalid user )?%{USERNAME:user.name} from %{IP:source.ip} port %{NUMBER:source.port:int}",
            "Accepted %{WORD:thp.auth_method} for %{USERNAME:user.name} from %{IP:source.ip} port %{NUMBER:source.port:int}",
            "new user: name=%{USERNAME:user.name}",
            "\\(%{USERNAME:user.name}\\) BEGIN EDIT",
        ]}},
        {"script": {"description": "set event.* from the message type", "source": (
            "if (ctx.message == null) { return; } "
            "String m = ctx.message; "
            "Map ev = (ctx.event instanceof Map) ? ctx.event : new HashMap(); "
            "if (m.contains('Failed password')) { ev.put('category','authentication'); ev.put('outcome','failure'); ev.put('action','ssh_login'); } "
            "else if (m.contains('Accepted password') || m.contains('Accepted publickey')) { ev.put('category','authentication'); ev.put('outcome','success'); ev.put('action','ssh_login'); } "
            "else if (m.contains('new user: name=')) { ev.put('category','iam'); ev.put('action','user_created'); } "
            "else if (m.contains('BEGIN EDIT')) { ev.put('category','configuration'); ev.put('action','cron_modified'); } "
            "ctx.event = ev;")}},
    ],
}


@lru_cache
def get_es() -> Elasticsearch:
    s = get_settings()
    kwargs = {"verify_certs": s.es_verify_certs, "request_timeout": 20}
    if s.es_username:
        kwargs["basic_auth"] = (s.es_username, s.es_password or "")
    return Elasticsearch(s.es_url, **kwargs)


def ensure_index_template(es: Elasticsearch) -> None:
    es.indices.put_index_template(name="thp-events", **INDEX_TEMPLATE)
    es.ingest.put_pipeline(id="thp-normalize", **NORMALIZE_PIPELINE)


def _time_filter(time_from: str, time_to: str) -> dict:
    return {"range": {"@timestamp": {"gte": time_from, "lte": time_to}}}


def search_events(es: Elasticsearch, *, query: str, time_from: str = "now-24h", time_to: str = "now",
                  size: int = 100, offset: int = 0) -> dict:
    """Free-text / field search (Lucene syntax, e.g.  source.ip:203.0.113.50 AND event.outcome:failure)."""
    size = max(1, min(size, 500))
    must = [{"query_string": {"query": query, "default_operator": "AND", "allow_leading_wildcard": False,
                              "analyze_wildcard": False, "lenient": True}}] if query.strip() else [{"match_all": {}}]
    res = es.search(
        index=get_settings().events_index,
        query={"bool": {"must": must, "filter": [_time_filter(time_from, time_to)]}},
        sort=[{"@timestamp": "desc"}], size=size, from_=offset, track_total_hits=True,
        aggs={"over_time": {"auto_date_histogram": {"field": "@timestamp", "buckets": 40}}},
        timeout="15s",
    )
    return {
        "total": res["hits"]["total"]["value"],
        "hits": [{"id": h["_id"], "index": h["_index"], **h["_source"]} for h in res["hits"]["hits"]],
        "histogram": [{"t": b["key_as_string"], "count": b["doc_count"]} for b in res["aggregations"]["over_time"]["buckets"]],
    }


def pivot_indicator(es: Elasticsearch, *, ioc_type: str, value: str, time_from: str = "now-7d", size: int = 50) -> dict:
    """Everything we have ever seen about one indicator: which hosts touched it, when, and how often."""
    fields = PIVOT_FIELDS.get(ioc_type)
    if not fields:
        raise ValueError(f"cannot pivot on indicator type '{ioc_type}'")
    should = [{"term": {f: value}} for f in fields] if ioc_type != "url" else [{"term": {"url.full": value}}]
    res = es.search(
        index=get_settings().events_index,
        query={"bool": {"filter": [{"bool": {"should": should, "minimum_should_match": 1}},
                                   {"range": {"@timestamp": {"gte": time_from}}}]}},
        sort=[{"@timestamp": "desc"}], size=min(size, 200), track_total_hits=True,
        aggs={"hosts": {"terms": {"field": "host.name", "size": 20}},
              "actions": {"terms": {"field": "event.action", "size": 20}},
              "first": {"min": {"field": "@timestamp"}}, "last": {"max": {"field": "@timestamp"}}},
        timeout="15s",
    )
    a = res["aggregations"]
    return {
        "total": res["hits"]["total"]["value"],
        "first_seen": a["first"].get("value_as_string"), "last_seen": a["last"].get("value_as_string"),
        "hosts": [{"name": b["key"], "count": b["doc_count"]} for b in a["hosts"]["buckets"]],
        "actions": [{"name": b["key"], "count": b["doc_count"]} for b in a["actions"]["buckets"]],
        "hits": [{"id": h["_id"], "index": h["_index"], **h["_source"]} for h in res["hits"]["hits"]],
    }


def overview(es: Elasticsearch) -> dict:
    res = es.search(
        index=get_settings().events_index, size=0, track_total_hits=True,
        query={"range": {"@timestamp": {"gte": "now-24h"}}},
        aggs={
            "per_hour": {"date_histogram": {"field": "@timestamp", "fixed_interval": "1h", "min_doc_count": 0,
                                             "extended_bounds": {"min": "now-24h", "max": "now"}}},
            "top_sources": {"terms": {"field": "source.ip", "size": 8}},
            "top_hosts": {"terms": {"field": "host.name", "size": 8}},
            "failed_logins": {"filter": {"bool": {"filter": [{"term": {"event.category": "authentication"}}, {"term": {"event.outcome": "failure"}}]}}},
        },
    )
    a = res["aggregations"]
    return {
        "events_24h": res["hits"]["total"]["value"],
        "failed_logins_24h": a["failed_logins"]["doc_count"],
        "per_hour": [{"t": b["key_as_string"], "count": b["doc_count"]} for b in a["per_hour"]["buckets"]],
        "top_sources": [{"name": b["key"], "count": b["doc_count"]} for b in a["top_sources"]["buckets"]],
        "top_hosts": [{"name": b["key"], "count": b["doc_count"]} for b in a["top_hosts"]["buckets"]],
    }
