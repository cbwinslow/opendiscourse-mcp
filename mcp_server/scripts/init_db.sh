#!/usr/bin/env bash
# Helper script to initialize the database using the Python db_init.py script.
# Usage: source mcp_server/.env && ./mcp_server/scripts/init_db.sh

set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set. Source mcp_server/.env or export DATABASE_URL first."
  exit 1
fi

python3 mcp_server/db_init.py --all

echo "DB init finished."
