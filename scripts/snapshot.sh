#!/usr/bin/env bash
#
# Refresh the data behind the public demo.
#
# Starts the local API against SQLite, saves each dashboard endpoint's response
# into frontend/src/demo/snapshot/, then stops the API. Commit and push the
# result and the Pages workflow republishes with the new numbers.
#
# Usage: ./scripts/snapshot.sh

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
OUT="$ROOT/frontend/src/demo/snapshot"

set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
# shellcheck disable=SC1091
. ./.env.local
set +a

"$ROOT/.venv/bin/python" -m uvicorn services.api.main:app \
  --host 127.0.0.1 --port 8011 --log-level warning &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT

# Wait for the API to answer rather than sleeping a fixed guess.
for _ in $(seq 1 30); do
  curl -sf http://127.0.0.1:8011/health >/dev/null && break
  sleep 0.5
done

# Read as athlete 1. The token is signed with the local dev secret and lives
# only for the length of this script.
TOKEN=$("$ROOT/.venv/bin/python" - <<'PY'
import os, jwt
from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc)
print(jwt.encode(
    {"sub": "1", "iat": now, "exp": now + timedelta(minutes=5)},
    os.environ["JWT_SECRET"], algorithm="HS256",
))
PY
)

mkdir -p "$OUT"
fetch() {
  local name=$1 path=$2
  curl -sf -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8011/api/$path" \
    | "$ROOT/.venv/bin/python" -m json.tool > "$OUT/$name.json"
  echo "  $name.json  $(wc -c < "$OUT/$name.json" | tr -d ' ') bytes"
}

echo "Writing snapshot to frontend/src/demo/snapshot/"
fetch metrics    "metrics/?days=180"
fetch activities "activities/?limit=60"
fetch sleep      "sleep/"
fetch week       "week/"

echo
echo "Done. Commit and push to republish:"
echo "  git add frontend/src/demo/snapshot && git commit -m 'Refresh demo snapshot' && git push"
