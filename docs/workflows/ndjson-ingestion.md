# NDJSON Ingestion + Load Workflow

This guide describes how to stage large NDJSON exports (Congress.gov bills) and load them into Postgres with validation hooks, plus a lightweight help/tldr structure and shell helpers for manual/automated lookups.

## Filesystem Layout
- `data/congress/plan/` — plan + completed logs (`bill_plan.txt`, `bill_plan.completed`)
- `data/congress/ndjson/bills/` — NDJSON payloads and per-batch manifests (`bill_offset*_p*.ndjson`, `.manifest.json`)
- `scripts/ingestion/congress/` — download + load scripts
- `scripts/ingestion/sql/ndjson_ingestion.sql` — Postgres schemas/functions/views
- `docs/workflows/` — this document; place future man/tldr pages under `docs/workflows/tldr/`

## End-to-End Flow
1) **Generate plan**  
   ```
   python -m dotenv -f .env run -- \
     python scripts/ingestion/congress/generate_bill_plan.py \
       --from-date 2025-01-01 --limit 250 --pages-per-job 100
   ```
   Output: `data/congress/plan/bill_plan.txt`

2) **Download NDJSON batches (sequential, resumable)**  
   ```
   python -m dotenv -f .env run -- \
     env LIMIT=250 FROM_DATE=2025-01-01 SLEEP_SECS=0.6 \
     bash scripts/ingestion/congress/run_bill_batches.sh
   ```
   Completed batches are appended to `bill_plan.completed`; reruns skip finished offsets.

3) **Load NDJSON into Postgres (once DB reachable)**  
   - One-off load:
     ```
     python -m dotenv -f .env run -- \
       DATABASE_URL=$DATABASE_URL \
       bash scripts/ingestion/congress/psql_load_bills.sh \
       data/congress/ndjson/bills/bill_offset0_p100.ndjson \
       data/congress/ndjson/bills/bill_offset0_p100.manifest.json
     ```
   - Bulk load loop (example):
     ```
     for f in data/congress/ndjson/bills/bill_offset*_p100.ndjson; do
       bash scripts/ingestion/congress/psql_load_bills.sh "$f" "${f%.ndjson}.manifest.json"
     done
     ```

## Postgres Objects (ndjson_ingestion.sql)
- Schemas: `ingestion_meta`, `ingestion_staging`, `ingestion_congress`, `ingestion_validation`
- Tables:
  - `ingestion_meta.ndjson_batches` — batch metadata/status, file paths, checksums, repo refs
  - `ingestion_staging.ndjson_lines` (hash partitioned) — raw JSON lines per batch
- Functions:
  - `ingestion_meta.begin_batch(...)` / `ingestion_meta.complete_batch(...)`
  - `ingestion_congress.load_bills_from_staging(batch_id)` — upserts into `congress_bills`
  - `ingestion_validation.batch_summary(batch_id)` — row counts/status checks
- Views:
  - `ingestion_meta.recent_batches` — quick batch listing

## Validation & Monitoring
- After each load: `SELECT * FROM ingestion_validation.batch_summary('<batch_id>');`
- Quick listing: `TABLE ingestion_meta.recent_batches;`
- Manifests per NDJSON include counts and status.
- Hash-partitioned staging enables parallel COPY; psql COPY is already streaming.

## Help / TLDR Structure
- Add short task-focused notes under `docs/workflows/tldr/` (e.g., `tldr/load-bills.md`, `tldr/check-batch.md`).
- Keep command snippets minimal and reference the primary workflow document.

## Git/Repo Linking
- The batch table includes `manifest_path` and `repo_ref` fields; when loading, pass `REPO_REF` (e.g., `opendiscourse@<commit>`) to tie ingested batches back to a git state.
- Keep NDJSON + manifests under versioned directories; manifests capture checksums to detect drift.

## Bash Helpers
- `scripts/ingestion/helpers.sh` provides:
  - `ndjson_batches` — list recent batches (requires `DATABASE_URL`)
  - `ndjson_batch_summary <batch_id>` — validation summary
  - `ndjson_head <file>` — peek at NDJSON contents (uses jq)

## Parallelization Notes
- Download step: jobs are sequential per plan; run multiple `run_bill_batches.sh` instances on disjoint plan slices if needed.
- Load step: staging table is partitioned; use multiple `psql_load_bills.sh` invocations in parallel batches (distinct files/batch_ids) to fan out work, ensuring DB connection pool size accommodates concurrency.

## Next Steps
- Add loaders for other Congress entities (members, votes, committees, actions) and for GovInfo/OpenStates using the same staging + upsert pattern.
- Extend validation to compute duplicate detection and constraint checks per entity.
- When DB is reachable, benchmark parallel load (number of concurrent COPY jobs vs. I/O).
