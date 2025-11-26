#!/usr/bin/env bash
# Run NDJSON bill downloads in sequence based on a plan file.
# Usage: CONGRESS_API_KEY=... bash scripts/ingestion/congress/run_bill_batches.sh
# Or:   python -m dotenv -f .env run -- bash scripts/ingestion/congress/run_bill_batches.sh

set -euo pipefail

PLAN_FILE=${PLAN_FILE:-data/congress/plan/bill_plan.txt}
DONE_FILE=${DONE_FILE:-data/congress/plan/bill_plan.completed}
OUT_DIR=${OUT_DIR:-data/congress/ndjson/bills}
FROM_DATE=${FROM_DATE:-2025-01-01}
LIMIT=${LIMIT:-50}
SLEEP_SECS=${SLEEP_SECS:-0.6}
PAGES_DEFAULT=${PAGES_DEFAULT:-20}

if [ -z "${CONGRESS_API_KEY:-}" ]; then
  echo "CONGRESS_API_KEY is required in the environment." >&2
  exit 1
fi

if [ ! -f "$PLAN_FILE" ]; then
  echo "Plan file not found: $PLAN_FILE" >&2
  exit 1
fi

mkdir -p "$(dirname "$DONE_FILE")" "$OUT_DIR"
touch "$DONE_FILE"

while IFS= read -r line; do
  [ -z "$line" ] && continue
  [[ "$line" =~ ^# ]] && continue

  # Expected format: offset=123 pages=20
  offset=$(echo "$line" | awk '{print $1}' | cut -d= -f2)
  pages=$(echo "$line" | awk '{print $2}' | cut -d= -f2)
  pages=${pages:-$PAGES_DEFAULT}

  key="${offset}:${pages}"
  if grep -q "$key" "$DONE_FILE"; then
    echo "⏭️  Skipping completed job $key"
    continue
  fi

  echo "🚀 Running job offset=$offset pages=$pages"
  if python scripts/ingestion/congress/download_bills_ndjson.py \
    --from-date "$FROM_DATE" \
    --offset "$offset" \
    --pages "$pages" \
    --limit "$LIMIT" \
    --sleep "$SLEEP_SECS" \
    --output-dir "$OUT_DIR"; then
    echo "$key $(date -u +%FT%TZ)" >> "$DONE_FILE"
    echo "✅ Completed job $key"
  else
    echo "❌ Failed job $key" >&2
    exit 1
  fi
done < "$PLAN_FILE"
