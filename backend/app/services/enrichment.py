"""Threat-intelligence enrichment: classify an indicator, ask the providers, cache the answer.

Design rules
  * Every provider is optional. No API key => provider is skipped, never an error.
  * One failing provider never breaks the lookup (timeouts, 429 rate limits, bad JSON ...).
  * Answers are cached in Postgres so a free-tier quota is not burned on repeat questions.
  * Providers all return the same shape, so the UI and the detection engine do not care who answered."""
from __future__ import annotations

import base64
import ipaddress
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import IocCache, WatchlistEntry

log = logging.getLogger("thp.enrichment")

_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$", re.I)
VERDICT_RANK = {"unknown": 0, "clean": 1, "suspicious": 2, "malicious": 3}


class InvalidIndicator(ValueError):
    pass


def detect_ioc_type(raw: str) -> tuple[str, str]:
    """Return (type, normalised_value). Raises InvalidIndicator for anything we do not recognise."""
    v = (raw or "").strip()
    if not v or len(v) > 2048:
        raise InvalidIndicator("empty or too long")
    v = v.replace("[.]", ".").replace("hxxp", "http")  # un-defang common copy/paste forms
    try:
        return "ip", str(ipaddress.ip_address(v))
    except ValueError:
        pass
    if re.fullmatch(r"[a-fA-F0-9]{64}", v):
        return "sha256", v.lower()
    if re.fullmatch(r"[a-fA-F0-9]{40}", v):
        return "sha1", v.lower()
    if re.fullmatch(r"[a-fA-F0-9]{32}", v):
        return "md5", v.lower()
    if re.match(r"^https?://", v, re.I):
        return "url", v
    # A real domain never ends in an all-numeric label (that would be a malformed IP like 999.999.1.1).
    if _DOMAIN_RE.match(v) and not v.rstrip(".").rsplit(".", 1)[-1].isdigit():
        return "domain", v.lower().rstrip(".")
    raise InvalidIndicator(f"'{raw[:60]}' is not an IP, domain, URL or file hash")


def _result(provider: str, verdict: str, score: int | None, detail: dict) -> dict:
    return {"provider": provider, "verdict": verdict, "score": score, "detail": detail}


# ------------------------------------------------------------------ providers
def virustotal(client: httpx.Client, ioc_type: str, value: str, key: str) -> dict:
    paths = {"ip": f"ip_addresses/{value}", "domain": f"domains/{value}",
             "md5": f"files/{value}", "sha1": f"files/{value}", "sha256": f"files/{value}"}
    if ioc_type == "url":
        paths["url"] = "urls/" + base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
    r = client.get(f"https://www.virustotal.com/api/v3/{paths[ioc_type]}", headers={"x-apikey": key})
    if r.status_code == 404:
        return _result("virustotal", "unknown", None, {"note": "not seen by VirusTotal"})
    r.raise_for_status()
    attrs = r.json()["data"]["attributes"]
    stats = attrs.get("last_analysis_stats", {})
    mal, sus = stats.get("malicious", 0), stats.get("suspicious", 0)
    total = sum(stats.values()) or 1
    verdict = "malicious" if mal >= 3 else "suspicious" if (mal or sus) else "clean"
    return _result("virustotal", verdict, round(100 * (mal + sus) / total), {"stats": stats, "reputation": attrs.get("reputation")})


def abuseipdb(client: httpx.Client, ioc_type: str, value: str, key: str) -> dict:
    if ioc_type != "ip":
        raise NotImplementedError
    r = client.get("https://api.abuseipdb.com/api/v2/check", params={"ipAddress": value, "maxAgeInDays": 90},
                   headers={"Key": key, "Accept": "application/json"})
    r.raise_for_status()
    d = r.json()["data"]
    score = d.get("abuseConfidenceScore", 0)
    verdict = "malicious" if score >= 75 else "suspicious" if score >= 25 else "clean"
    return _result("abuseipdb", verdict, score, {"reports": d.get("totalReports"), "country": d.get("countryCode"), "isp": d.get("isp")})


def otx(client: httpx.Client, ioc_type: str, value: str, key: str) -> dict:
    kind = {"ip": "IPv4" if ":" not in value else "IPv6", "domain": "domain", "url": "url",
            "md5": "file", "sha1": "file", "sha256": "file"}[ioc_type]
    r = client.get(f"https://otx.alienvault.com/api/v1/indicators/{kind}/{value}/general", headers={"X-OTX-API-KEY": key})
    if r.status_code == 404:
        return _result("otx", "unknown", None, {"note": "not in OTX"})
    r.raise_for_status()
    pulses = r.json().get("pulse_info", {}).get("count", 0)
    verdict = "malicious" if pulses >= 5 else "suspicious" if pulses else "clean"
    return _result("otx", verdict, min(100, pulses * 10), {"pulses": pulses})


def local_watchlist(db: Session, ioc_type: str, value: str) -> dict | None:
    row = db.scalars(select(WatchlistEntry).where(WatchlistEntry.ioc_type == ioc_type, WatchlistEntry.value == value,
                                                  WatchlistEntry.active.is_(True))).first()
    if not row:
        return None
    return _result("local-watchlist", "malicious", 100, {"source": row.source, "note": row.note})


def _providers() -> list[tuple[str, Callable, str | None]]:
    s = get_settings()
    return [("virustotal", virustotal, s.vt_api_key), ("abuseipdb", abuseipdb, s.abuseipdb_api_key), ("otx", otx, s.otx_api_key)]


# ------------------------------------------------------------------ public API
def lookup(db: Session, raw_value: str, *, client: httpx.Client | None = None, use_cache: bool = True) -> dict:
    ioc_type, value = detect_ioc_type(raw_value)
    ttl = timedelta(hours=get_settings().ioc_cache_ttl_hours)
    now = datetime.now(timezone.utc)

    cached = db.scalars(select(IocCache).where(IocCache.ioc_type == ioc_type, IocCache.value == value)).first()
    if use_cache and cached and now - cached.fetched_at < ttl:
        out = dict(cached.result)
        out["cached"] = True
    else:
        results: list[dict] = []
        errors: dict[str, str] = {}
        own_client = client is None
        client = client or httpx.Client(timeout=8.0)
        try:
            for name, fn, key in _providers():
                if not key:
                    continue
                try:
                    results.append(fn(client, ioc_type, value, key))
                except NotImplementedError:
                    continue  # provider does not support this indicator type
                except httpx.HTTPStatusError as exc:
                    errors[name] = "rate limited" if exc.response.status_code == 429 else f"HTTP {exc.response.status_code}"
                except Exception as exc:  # network, JSON ... never fail the whole lookup
                    errors[name] = type(exc).__name__
        finally:
            if own_client:
                client.close()
        out = {"type": ioc_type, "value": value, "results": results, "errors": errors, "cached": False,
               "providers_configured": [n for n, _, k in _providers() if k]}
        if results:  # only cache real answers; a pure-error lookup should be retried
            if cached:
                cached.result, cached.fetched_at = out, now
            else:
                db.add(IocCache(ioc_type=ioc_type, value=value, result=out, fetched_at=now))
            db.flush()

    # Local watchlist is always checked live (it is free and analysts expect instant changes).
    local = local_watchlist(db, ioc_type, value)
    results = list(out.get("results", []))
    if local:
        results.insert(0, local)
    verdict = max((r["verdict"] for r in results), key=lambda v: VERDICT_RANK[v], default="unknown")
    return {**out, "results": results, "verdict": verdict}
