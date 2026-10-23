import httpx
import pytest

from app.core.config import get_settings
from app.db.models import WatchlistEntry
from app.services import enrichment
from app.services.enrichment import InvalidIndicator, detect_ioc_type


@pytest.mark.parametrize("raw,expected", [
    ("8.8.8.8", ("ip", "8.8.8.8")),
    ("2001:db8::1", ("ip", "2001:db8::1")),
    ("Evil-Site.COM", ("domain", "evil-site.com")),
    ("evil[.]com", ("domain", "evil.com")),
    ("hxxp://evil.com/a", ("url", "http://evil.com/a")),
    ("d41d8cd98f00b204e9800998ecf8427e", ("md5", "d41d8cd98f00b204e9800998ecf8427e")),
    ("da39a3ee5e6b4b0d3255bfef95601890afd80709", ("sha1", "da39a3ee5e6b4b0d3255bfef95601890afd80709")),
    ("E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855", ("sha256", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")),
])
def test_detect_ioc_type(raw, expected):
    assert detect_ioc_type(raw) == expected


@pytest.mark.parametrize("bad", ["", "   ", "not an indicator", "999.999.1.1", "a" * 3000, "-bad-.com"])
def test_detect_ioc_type_rejects_garbage(bad):
    with pytest.raises(InvalidIndicator):
        detect_ioc_type(bad)


@pytest.fixture()
def keys(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vt_api_key", "vt-key")
    monkeypatch.setattr(s, "abuseipdb_api_key", "ab-key")
    monkeypatch.setattr(s, "otx_api_key", None)


def _client(handler, calls):
    def wrapped(request):
        calls.append(str(request.url))
        return handler(request)
    return httpx.Client(transport=httpx.MockTransport(wrapped))


def _vt_malicious():
    return httpx.Response(200, json={"data": {"attributes": {"last_analysis_stats": {"malicious": 12, "suspicious": 1, "harmless": 60, "undetected": 20}, "reputation": -40}}})


def test_no_keys_means_local_only_and_unknown(db, monkeypatch):
    s = get_settings()
    for k in ("vt_api_key", "abuseipdb_api_key", "otx_api_key"):
        monkeypatch.setattr(s, k, None)
    out = enrichment.lookup(db, "9.9.9.9")
    assert out["verdict"] == "unknown" and out["providers_configured"] == []


def test_providers_are_combined_and_worst_verdict_wins(db, keys):
    def handler(req):
        if "virustotal" in str(req.url):
            return _vt_malicious()
        return httpx.Response(200, json={"data": {"abuseConfidenceScore": 10, "totalReports": 1, "countryCode": "XX", "isp": "x"}})
    calls = []
    out = enrichment.lookup(db, "203.0.113.9", client=_client(handler, calls))
    assert out["verdict"] == "malicious"
    assert {r["provider"] for r in out["results"]} == {"virustotal", "abuseipdb"}
    assert len(calls) == 2


def test_second_lookup_is_served_from_cache(db, keys):
    calls = []
    client = _client(lambda r: _vt_malicious() if "virustotal" in str(r.url) else httpx.Response(200, json={"data": {"abuseConfidenceScore": 0}}), calls)
    enrichment.lookup(db, "203.0.113.9", client=client)
    n = len(calls)
    again = enrichment.lookup(db, "203.0.113.9", client=client)
    assert again["cached"] is True and len(calls) == n
    enrichment.lookup(db, "203.0.113.9", client=client, use_cache=False)
    assert len(calls) > n


def test_rate_limited_provider_does_not_break_lookup(db, keys):
    def handler(req):
        return httpx.Response(429) if "virustotal" in str(req.url) else httpx.Response(200, json={"data": {"abuseConfidenceScore": 90, "totalReports": 50}})
    out = enrichment.lookup(db, "203.0.113.10", client=_client(handler, []))
    assert out["errors"] == {"virustotal": "rate limited"}
    assert out["verdict"] == "malicious"


def test_pure_failure_is_not_cached(db, keys):
    out = enrichment.lookup(db, "203.0.113.11", client=_client(lambda r: httpx.Response(500), []))
    assert out["results"] == [] and len(out["errors"]) == 2
    from app.db.models import IocCache
    assert db.query(IocCache).count() == 0


def test_abuseipdb_skipped_for_non_ip_and_url_id_is_urlsafe_base64(db, keys):
    calls = []
    enrichment.lookup(db, "http://evil.example/a?b=c", client=_client(lambda r: httpx.Response(404), calls))
    assert len(calls) == 1 and "/urls/" in calls[0] and "=" not in calls[0].split("/urls/")[1]


def test_local_watchlist_is_always_malicious_and_checked_live(db, monkeypatch):
    s = get_settings()
    for k in ("vt_api_key", "abuseipdb_api_key", "otx_api_key"):
        monkeypatch.setattr(s, k, None)
    db.add(WatchlistEntry(ioc_type="domain", value="c2.evil.example", source="seed"))
    db.commit()
    out = enrichment.lookup(db, "C2.Evil.Example")
    assert out["verdict"] == "malicious" and out["results"][0]["provider"] == "local-watchlist"
