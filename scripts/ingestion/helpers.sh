#!/usr/bin/env bash
# Helper shell functions for NDJSON ingestion workflows.

# Print recent batches from ingestion_meta.recent_batches
ndjson_batches() {
  if [ -z "${DATABASE_URL:-}" ]; then
    echo "DATABASE_URL required" >&2
    return 1
  fi
  psql "$DATABASE_URL" -c "TABLE ingestion_meta.recent_batches;"
}

# Show manifest + row counts for a specific batch_id
ndjson_batch_summary() {
  if [ -z "$1" ]; then
    echo "usage: ndjson_batch_summary <batch_id>" >&2
    return 1
  fi
  psql "$DATABASE_URL" -v bid="$1" -c "SELECT * FROM ingestion_validation.batch_summary(:'bid');"
}

# Quick view of NDJSON file head
ndjson_head() {
  local file=$1
  [ -z "$file" ] && { echo "usage: ndjson_head <file>" >&2; return 1; }
  head -n 5 "$file" | jq .
}
