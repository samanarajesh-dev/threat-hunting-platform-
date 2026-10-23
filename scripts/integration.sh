#!/usr/bin/env bash
# Real-stack integration checklist (docs/TESTING.md): needs the Docker stack running and a filled-in .env.
# Prints PASS/FAIL per step. Secrets are read from .env by THIS script and are never printed.
# Overrides for testing against a mock: ES_URL, API_URL, SKIP_DOCKER=1, SEED_CMD="..."
set -u
cd "$(dirname "$0")/.." || exit 2
if [ -f .env ]; then set -a; . ./.env; set +a; fi
ES_URL="${ES_URL:-http://localhost:9200}"
API_URL="${API_URL:-http://localhost:8000}"
EPASS="${ELASTIC_PASSWORD:-}"
SEED_CMD="${SEED_CMD:-docker compose exec -T backend python -m scripts.seed_data}"
fails=0

pass() { echo "PASS  $1"; }
fail() { echo "FAIL  $1"; [ -n "${2:-}" ] && echo "      $2"; fails=$((fails+1)); }
jq_py() { python3 -c "import sys,json
d=json.load(sys.stdin)
$1"; }

# 1. services running
if [ "${SKIP_DOCKER:-0}" = "1" ]; then echo "SKIP  1 services running (SKIP_DOCKER=1)"; else
  running=$(docker compose ps --services --status running 2>/dev/null)
  missing=""; for s in elasticsearch postgres backend; do echo "$running" | grep -qx "$s" || missing="$missing $s"; done
  if [ -z "$missing" ]; then pass "1 services running (elasticsearch, postgres, backend)"; else fail "1 services running" "not running:$missing  (try: docker compose up -d --build)"; fi
fi

# 2. index template installed
t=$(curl -fsS -u "elastic:$EPASS" "$ES_URL/_index_template/thp-events" 2>&1)
if echo "$t" | grep -q 'thp-events-\*'; then pass "2 index template 'thp-events' installed"; else fail "2 index template installed" "$(echo "$t" | head -c 200)"; fi

# 3. ingest pipeline normalises an sshd failure
body='{"docs":[{"_source":{"message":"sshd[812]: Failed password for invalid user admin from 203.0.113.50 port 51234 ssh2"}}]}'
s=$(curl -fsS -u "elastic:$EPASS" -H 'Content-Type: application/json' -XPOST "$ES_URL/_ingest/pipeline/thp-normalize/_simulate" -d "$body" 2>&1)
res=$(echo "$s" | jq_py '
src=d["docs"][0]["doc"]["_source"]
def g(p):
    if p in src: return src[p]
    cur=src
    for k in p.split("."):
        if not isinstance(cur,dict) or k not in cur: return None
        cur=cur[k]
    return cur
ok = g("event.outcome")=="failure" and g("event.action")=="ssh_login" and g("user.name")=="admin" and str(g("source.ip"))=="203.0.113.50"
print("OK" if ok else "BAD")' 2>&1)
if [ "$res" = "OK" ]; then pass "3 ingest pipeline normalises an sshd failure"; else fail "3 ingest pipeline normalises an sshd failure" "$(echo "$s" | head -c 300)"; fi

# 4. seed + retro-hunt
out=$(bash -c "$SEED_CMD" 2>&1)
if echo "$out" | grep -q "retro-hunt done: 10 alerts, 2 incident"; then pass "4 seed loaded; retro-hunt produced 10 alerts and 2 incidents"
else fail "4 seed + retro-hunt (expected '10 alerts, 2 incident(s)')" "$(echo "$out" | tail -n 5)"; fi

# 5. events are searchable
c=$(curl -fsS -u "elastic:$EPASS" "$ES_URL/thp-events-*/_count" 2>&1 | jq_py 'print(d.get("count",0))' 2>&1)
if [ "${c:-0}" -ge 700 ] 2>/dev/null; then pass "5 events searchable ($c documents)"; else fail "5 events searchable (expected >= 700)" "count=$c"; fi

# 6. rules run on real Elasticsearch without errors
tok=$(curl -fsS -d "username=${ADMIN_USERNAME:-admin}" --data-urlencode "password=${ADMIN_PASSWORD:-}" "$API_URL/api/v1/auth/login" 2>/dev/null | jq_py 'print(d.get("access_token",""))' 2>/dev/null)
if [ -z "$tok" ]; then fail "6 detections run" "could not log in to the API (check ADMIN_USERNAME / ADMIN_PASSWORD in .env and that the backend is up)"; else
  r=$(curl -fsS -XPOST -H "Authorization: Bearer $tok" "$API_URL/api/v1/detections/run?lookback_minutes=180" 2>&1)
  v=$(echo "$r" | jq_py 'print("OK" if d.get("errors")=={} and d.get("alerts_touched",0)>=10 else "BAD "+str(d.get("errors")))' 2>&1)
  if [ "$v" = "OK" ]; then pass "6 all rules run on real Elasticsearch with no errors"; else fail "6 all rules run with no errors" "$v"; fi
fi

echo "== SUMMARY =="
if [ $fails -eq 0 ]; then echo "INTEGRATION: PASS"; else echo "INTEGRATION: FAIL ($fails step(s) failed)"; fi
exit $((fails>0))
