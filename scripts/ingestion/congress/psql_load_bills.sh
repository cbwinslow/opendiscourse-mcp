#!/usr/bin/env bash
# Load a Congress bills NDJSON batch into Postgres via psql.
#
# Usage:
#   DATABASE_URL=postgres://... CONGRESS_API_KEY=... \
#   bash scripts/ingestion/congress/psql_load_bills.sh /path/to/bill_offset0_p100.ndjson /path/to/bill_offset0_p100.manifest.json
#
# Requirements: psql, sha256sum, jq (optional, only for manifest digest).

set -euo pipefail

FILE_PATH=${1:-}
MANIFEST_PATH=${2:-}
SOURCE_NAME=${SOURCE_NAME:-"congress_bills"}
REPO_REF=${REPO_REF:-""}

if [ -z "$FILE_PATH" ] || [ ! -f "$FILE_PATH" ]; then
  echo "NDJSON file required: psql_load_bills.sh <ndjson_file> [manifest.json]" >&2
  exit 1
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is required in environment." >&2
  exit 1
fi

CHECKSUM=$(sha256sum "$FILE_PATH" | awk '{print "sha256=" $1}')

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
\set file_path '`'"$FILE_PATH"'`'
\set checksum '`'"$CHECKSUM"'`'
\set source_name '`'"$SOURCE_NAME"'`'
\set manifest_path '`'"${MANIFEST_PATH:-}'`'
\set repo_ref '`'"$REPO_REF"'`'

-- Begin batch and expose batch_id to psql variables
SELECT ingestion_meta.begin_batch(:'source_name', :'file_path', :'checksum', NULL, NULLIF(:'manifest_path',''), NULLIF(:'repo_ref','')) AS batch_id \gset

-- Stage NDJSON lines
COPY ingestion_staging.ndjson_lines (batch_id, raw)
FROM PROGRAM format('cat %s', :'file_path')
WITH (FORMAT text);

-- Load into congress_bills
SELECT * FROM ingestion_congress.load_bills_from_staging(:'batch_id');

-- Validation summary
SELECT * FROM ingestion_validation.batch_summary(:'batch_id');
SQL
