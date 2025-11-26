#!/usr/bin/env bash
# Lightweight Postgres connectivity diagnostic.
# Usage:
#   bash scripts/diagnostics/db_connect_diag.sh
#   DATABASE_URL=postgres://user:pass@host:5432/db bash scripts/diagnostics/db_connect_diag.sh
#
# To load .env automatically:
#   python -m dotenv -f .env run -- bash scripts/diagnostics/db_connect_diag.sh

set -euo pipefail

DATABASE_URL=${DATABASE_URL:-}
HOST_OVERRIDE=${HOST_OVERRIDE:-}
PORT_OVERRIDE=${PORT_OVERRIDE:-}
USER_OVERRIDE=${USER_OVERRIDE:-}
DB_OVERRIDE=${DB_OVERRIDE:-}

mask_url() {
  python - <<'PY'
import os
import urllib.parse as up
url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL: (not set)")
    raise SystemExit
try:
    parsed = up.urlparse(url)
    pwd = parsed.password
    masked_netloc = parsed.netloc
    if pwd:
        masked_netloc = masked_netloc.replace(pwd, "********")
    print(f"DATABASE_URL: {parsed.scheme}://{masked_netloc}{parsed.path}")
except Exception as e:
    print(f"DATABASE_URL: (parse error: {e})")
PY
}

echo "=== Environment snapshot ==="
mask_url
echo "HOST_OVERRIDE=${HOST_OVERRIDE:-<none>}"
echo "PORT_OVERRIDE=${PORT_OVERRIDE:-<none>}"
echo "USER_OVERRIDE=${USER_OVERRIDE:-<none>}"
echo "DB_OVERRIDE=${DB_OVERRIDE:-<none>}"

echo
echo "=== Binaries ==="
command -v psql >/dev/null && psql --version || echo "psql: not found"
command -v pg_isready >/dev/null && pg_isready --version || echo "pg_isready: not found"

echo
echo "=== Local postgres processes (pgrep) ==="
pgrep -fa postgres || echo "no postgres processes found"

echo
echo "=== Listening on port 5432 (ss) ==="
if command -v ss >/dev/null; then
  ss -ltn sport = :5432 || true
else
  echo "ss not available"
fi

echo
echo "=== pg_isready checks ==="
if command -v pg_isready >/dev/null; then
  if [ -n "$DATABASE_URL" ]; then
    pg_isready -d "$DATABASE_URL" || true
  fi
  pg_isready -h "${HOST_OVERRIDE:-localhost}" -p "${PORT_OVERRIDE:-5432}" || true
else
  echo "pg_isready not available"
fi

echo
echo "=== psql simple probe ==="
if [ -n "$DATABASE_URL" ]; then
  if ! psql "$DATABASE_URL" -c "SELECT current_user, current_database(), inet_server_addr(), inet_server_port();" -tA -v ON_ERROR_STOP=1; then
    echo "psql probe with DATABASE_URL failed" >&2
  fi
else
  echo "DATABASE_URL not set; skipping direct psql probe"
fi

echo
echo "=== psql localhost fallback (may prompt if auth required) ==="
HOST_FALLBACK=${HOST_OVERRIDE:-localhost}
PORT_FALLBACK=${PORT_OVERRIDE:-5432}
USER_FALLBACK=${USER_OVERRIDE:-opendiscourse}
DB_FALLBACK=${DB_OVERRIDE:-opendiscourse}
psql "host=${HOST_FALLBACK} port=${PORT_FALLBACK} user=${USER_FALLBACK} dbname=${DB_FALLBACK}" -c "SELECT current_user, current_database();" -tA || echo "localhost fallback probe failed"
