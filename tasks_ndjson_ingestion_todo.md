# NDJSON Ingestion TODO (Structured)

## Item 1: Load staged Congress bills into Postgres
- Microgoals:
  - Enable DB connectivity and ensure `congress_bills` schema matches loader expectations.
  - `\i scripts/ingestion/sql/ndjson_ingestion.sql` in the target DB.
  - Run `psql_load_bills.sh` across all NDJSON batches; record batch_ids.
  - Verify row counts vs manifests and API `count`.
- Completion Criteria:
  - All NDJSON files processed; `ingestion_meta.ndjson_batches.status = 'loaded'`.
  - Total rows ingested >= 422,397 and within 0.1% of manifest totals.
  - No failed batches and no constraint violations.
- Tests:
  - `SELECT COUNT(*) FROM congress_bills;`
  - `SELECT * FROM ingestion_validation.batch_summary(<sample_batch_id>);`
  - Spot-check 5 random records for required fields (bill_id, title, congress).

## Item 2: Add loaders for other Congress entities (members, committees, votes, actions)
- Microgoals:
  - Define per-entity upsert functions in `scripts/ingestion/sql/ndjson_ingestion.sql`.
  - Create NDJSON download scripts mirroring bills (plan + batches).
  - Add psql loader scripts per entity.
  - Update docs/tldr with command examples.
- Completion Criteria:
  - NDJSON + manifests stored under `data/congress/ndjson/<entity>/`.
  - Batch summaries report loaded status with expected counts.
  - Docs include commands for download + load per entity.
- Tests:
  - Row counts per entity match manifests.
  - `ON CONFLICT` paths verified by reloading a small batch (idempotency).

## Item 3: GovInfo and OpenStates NDJSON pipelines
- Microgoals:
  - Extend plan/download scripts for GovInfo packages and OpenStates bills.
  - Add staging/upsert functions for govinfo_documents and openstates_bills.
  - Add validation views for duplicates and required fields.
  - Document storage layout and commands.
- Completion Criteria:
  - NDJSON + manifests exist for both sources.
  - Loader scripts complete without errors; validation views green.
- Tests:
  - Count checks vs API pagination counts.
  - Sample field validation (date parsing, IDs present).

## Item 4: Observability and help system
- Microgoals:
  - Add `docs/workflows/tldr/` entries for download, load, validate, and troubleshoot.
  - Add Bash lookup helpers for per-source counts and recent batches.
  - Consider a `ingestion_validation.health()` view summarizing latest batches per source.
  - Link batches to repo commits using `repo_ref`; capture in manifests.
- Completion Criteria:
  - TLDR pages present and referenced from the main workflow doc.
  - Bash helpers verified against a reachable DB.
  - `ingestion_meta.recent_batches` shows repo_ref where provided.
- Tests:
  - Run each helper command successfully (when DB reachable).
  - Verify repo_ref persists in batch listings.
