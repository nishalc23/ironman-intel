#!/usr/bin/env bash
#
# Start Ironman Intel locally: API on :8000, frontend on :5173.
#
# Runs against a local SQLite file rather than Postgres, so there is no Docker
# and no database to provision. Ctrl-C stops both.

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

# --- first-run setup ------------------------------------------------------

if [ ! -d .venv ]; then
  echo "Creating the Python environment (first run only)…"
  python3.12 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r services/api/requirements.txt \
                           -r services/ingestion/requirements.txt \
                           pytest httpx
fi

if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend packages (first run only)…"
  npm --prefix frontend install
fi

if [ ! -f .env.local ]; then
  cat > .env.local <<'ENVEOF'
DATABASE_URL=sqlite:///./local.sqlite
JWT_SECRET=local-dev-secret-change-in-production
GARMIN_ENC_KEY=local-dev-encryption-key
ENVEOF
  echo "Wrote .env.local with local defaults."
fi

# --- environment ----------------------------------------------------------

# .env is loaded first because it still carries the deployed Postgres URL.
# .env.local is loaded last so its SQLite setting wins; sourcing them the
# other way round pointed the local API at a database that no longer exists.
set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
# shellcheck disable=SC1091
. ./.env.local
set +a

# --- run ------------------------------------------------------------------

cleanup() { echo; echo "Stopping…"; kill 0 2>/dev/null || true; }
trap cleanup EXIT INT TERM

"$ROOT/.venv/bin/python" -m uvicorn services.api.main:app \
  --host 127.0.0.1 --port 8000 --reload &

npm --prefix frontend run dev &

sleep 4
echo
echo "  Ironman Intel is running"
echo "  App   http://localhost:5173"
echo "  API   http://127.0.0.1:8000/docs"
echo
echo "  Ctrl-C to stop."
echo

wait
