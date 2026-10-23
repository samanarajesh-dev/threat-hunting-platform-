#!/usr/bin/env bash
# ONE command that verifies the whole project: backend tests + frontend type-check/build.
# Prints a final line "VERIFY: PASS" or "VERIFY: FAIL" so humans and AI agents can quote real results.
set -u
cd "$(dirname "$0")/.." || exit 2
status=0

echo "== backend tests =="
cd backend || exit 2
if [ ! -d .venv ]; then
  echo "(creating virtualenv and installing dependencies, first run only)"
  python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements-dev.txt
else
  . .venv/bin/activate
fi
bout=$(python -m pytest -q 2>&1); brc=$?
if [ $brc -eq 0 ]; then echo "$bout" | tail -n 3; else echo "$bout" | tail -n 60; status=1; fi
bline=$(echo "$bout" | grep -E "[0-9]+ (passed|failed|error)" | tail -n 1)
cd ..

echo "== frontend build =="
cd frontend || exit 2
[ -d node_modules ] || { echo "(npm install, first run only)"; npm install --no-audit --no-fund >/dev/null 2>&1; }
fout=$(npm run build 2>&1); frc=$?
if [ $frc -eq 0 ]; then echo "$fout" | grep -E "built in|modules transformed" | tail -n 2; else echo "$fout" | tail -n 40; status=1; fi
cd ..

echo "== SUMMARY =="
echo "backend:  ${bline:-no result} (exit $brc)"
echo "frontend: $([ $frc -eq 0 ] && echo 'build OK' || echo 'build FAILED') (exit $frc)"
if [ $status -eq 0 ]; then echo "VERIFY: PASS"; else echo "VERIFY: FAIL"; fi
exit $status
