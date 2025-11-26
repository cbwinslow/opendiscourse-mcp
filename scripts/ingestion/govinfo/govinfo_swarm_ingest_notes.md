# Govinfo Swarm Ingestion – Design Notes & Summary

## 1. High-Level Goal

Build a **multi-agent, swarm-style ingestion pipeline** that:

- Pulls bulk data from **govinfo.gov** (starting with the `/published` endpoint for collections like `BILLS`).
- Stores raw and normalized metadata in a **normalized PostgreSQL schema**.
- Uses **LLM agents via OpenRouter** to enrich and normalize metadata (topics, policy domains, citations, etc.).
- Is self-validating: agents check their own work, retry on anomalies, and defer to humans when needed.

---

## 2. PostgreSQL Schema Overview (govinfo-centric)

> The actual DDL lives in the Python script as an embedded migration (`MIGRATION_SQL`). This section documents the important tables and design choices.

### 2.1 Core govinfo tables

- **`govinfo_collections`**
  - Columns: `code` (PK, e.g. `BILLS`), `name`, `description`, timestamps.
  - Purpose: catalog govinfo collections we ingest.

- **`govinfo_packages`**
  - Columns:
    - `id` (PK, BIGSERIAL)
    - `package_id` (UNIQUE, e.g. `BILLS-116hr1565ih`)
    - `collection_code` (FK-style, text - e.g. `BILLS`)
    - `doc_class` (e.g. `hr`)
    - `title`
    - `congress` (integer)
    - `date_issued` (DATE)
    - `last_modified` (TIMESTAMPTZ)
    - `package_link` (URL to `.../packages/{id}/summary`)
    - `raw_json` (JSONB – raw payload from govinfo)
    - `normalized_json` (JSONB – LLM-enriched metadata)
    - `embedding` (optional `vector(1536)` for pgvector)
    - timestamps
  - Indexes:
    - `idx_govinfo_packages_collection_date` on `(collection_code, date_issued)`
    - `idx_govinfo_packages_congress` on `(congress)`
    - `idx_govinfo_packages_title_trgm` on `title` (trigram index for search)
    - `idx_govinfo_packages_normalized_json` on `normalized_json` (GIN)

- **`govinfo_published_ingest_state`**
  - Tracks where we are in the `/published` pagination for each `(collection, date range)`.
  - Columns: `collection_code`, `date_start`, `date_end`, `offset_mark`, `last_run_at`, `completed`.
  - `UNIQUE (collection_code, date_start, date_end)`.

- **`govinfo_ingest_log`**
  - Simple run-level log for ETL jobs.
  - Columns: `collection_code`, `run_started_at`, `run_completed_at`, `status`, `message`.

### 2.2 Normalization philosophy

- **Raw vs normalized:**
  - Raw govinfo payload is stored intact in `raw_json`.
  - LLM-produced or algorithmically derived metadata is stored in `normalized_json`.
- **Idempotency:**
  - `package_id` is UNIQUE; repeated ingests for the same package will update metadata but not duplicate rows.
- **Future expansion:**
  - The current embedded migration is a streamlined subset. It can later be extended to the larger ~20-table design (sections, citations, mentions, file variants, etc.).

---

## 3. `govinfo_swarm_ingest.py` – Script Overview

This script is a **single, consolidated entrypoint** that contains:

1. **Embedded migration SQL (`MIGRATION_SQL`)**
   - Creates core govinfo tables and indexes.
   - Tries to create `vector` extension (pgvector) if available (ignores failure).

2. **Configuration dataclasses**
   - `DBConfig` – host/port/db/user/password
   - `IngestConfig` – start/end dates, collections, `max_packages`, flags (`use_llm_normalizer`, `dry_run`).
   - `SwarmTask` – generic task unit (`kind`, `payload`).
   - `SwarmContext` – shared context (`DBConfig`, HTTP session, OpenRouter client, `IngestConfig`).

3. **Database helpers**
   - `get_db_connection(cfg)` – psycopg2 connection (no autocommit; script controls transactions).
   - `run_migrations(db_cfg)` – runs embedded migration SQL, fully idempotent.
   - `upsert_package(conn, pkg, collection_code)` – `INSERT ... ON CONFLICT (package_id) DO UPDATE` semantically idempotent upsert.
   - `update_normalized_json(conn, package_id, normalized)` – updates `normalized_json` for a package.

4. **Govinfo API helpers**
   - Base URL: `https://api.govinfo.gov`.
   - `build_published_url(collection, start_date, end_date, offset_mark, page_size, api_key)`.
   - `fetch_published_page(...) -> (packages, next_offset_mark)`.
   - `fetch_package_summary(session, package_link, api_key)` – fetches summary JSON for a package (hook for deeper metadata later).

5. **OpenRouter / LLM normalizer**
   - `build_openrouter_client()` – returns OpenRouter client if SDK + API key are present, otherwise `None`.
   - `llm_normalize_package(client, package)` – sends a compact JSON blob (title, docClass, congress, collection, date) and asks the LLM to respond with *only JSON* including:
     - `topics` (list of strings)
     - `policy_domain` (string)
     - `ideology_estimate` (one of `left`, `center-left`, `center`, `center-right`, `right`, `unclear`)
     - `primary_branch` (e.g., `legislative`, `executive`)
     - `summary` (1–2 sentence description)
   - Robust error handling: catches exceptions, logs, and returns `None` on failure without crashing the pipeline.

6. **Swarm agents**

   - `BaseAgent` – interface (`can_handle`, `handle`).

   - `GovinfoPublishedAgent`
     - Handles `fetch_published_page` tasks.
     - Calls `fetch_published_page` and emits:
       - `upsert_packages` task with the list of packages.
       - Another `fetch_published_page` task if `next_offset_mark` is present.

   - `GovinfoUpsertAgent`
     - Handles `upsert_packages` tasks.
     - For each package:
       - Checks `max_packages` (if set) to enforce an overall cap.
       - If `dry_run` is enabled, only logs.
       - Otherwise calls `upsert_package` to write to DB.
       - If `use_llm_normalizer` is enabled and an OpenRouter client exists, emits `normalize_with_llm` tasks.

   - `LLMNormalizerAgent`
     - Handles `normalize_with_llm` tasks.
     - Calls `llm_normalize_package` to get enrichment.
     - Writes result to `normalized_json` via `update_normalized_json` (unless `dry_run`).

   - `SwarmCoordinator`
     - Maintains a FIFO task queue.
     - For each task, finds the first agent whose `can_handle` returns `True` and calls `handle`.
     - Appends any new tasks spawned by agents back into the queue.
     - Logs when no agent can handle a given task.

7. **Ingestion orchestration**

   - `run_ingestion(db_cfg, ingest_cfg, api_key)`
     - Creates HTTP session.
     - Builds OpenRouter client (if `use_llm_normalizer=True`).
     - Constructs `SwarmContext` and agents list.
     - Seeds initial tasks: for each collection, a `fetch_published_page` task with `offset_mark='*'`.
     - Runs `SwarmCoordinator.run(initial_tasks)`.

8. **CLI / main()**

   - Arguments:
     - `--init-db` – run embedded migrations.
     - `--ingest` – perform ingestion.
     - `--start-date`, `--end-date` – required when `--ingest`.
     - `--collections` – comma-separated list (`BILLS` default).
     - `--max-packages` – optional cap across the run.
     - `--use-llm-normalizer` – toggle OpenRouter enrichment.
     - `--dry-run` – simulate without DB writes.
     - DB flags: `--pg-host`, `--pg-port`, `--pg-db`, `--pg-user`, `--pg-password` (defaulting to standard PG env vars).
     - `--govinfo-api-key` or `GOVINFO_API_KEY` env var.
     - `--verbose` – debug logging.

   - Flow:
     - Build `DBConfig` and (if ingesting) `IngestConfig`.
     - Optionally run migrations.
     - Run ingestion if requested.

---

## 4. Self-Validating Algorithm – Design

We want a **self-checking, self-correcting ingestion loop** where agents:

- Verify their own output against invariants and external references.
- Decide whether to **accept**, **retry**, **adjust & retry**, **defer to human**, or **escalate**.

### 4.1 Validation stages

For each package (or batch of packages) we can define validation steps:

1. **Schema & type invariants**
   - `package_id` is non-empty and unique.
   - `date_issued` parses as a valid date.
   - If `congress` is present, it’s an integer within a plausible range (e.g., `1–120`).
   - `raw_json` is non-null.

2. **External vs internal consistency**
   - Total packages ingested for `(collection, date range)` should be close or equal to `data['count']` from govinfo (if available).
   - Re-ingestion should be idempotent: when you run the same task twice, row counts and key fields remain stable.

3. **LLM normalization sanity checks**
   - `normalized_json` must be valid JSON with required keys.
   - `topics` is a non-empty list of short strings.
   - `ideology_estimate` is in the allowed set.
   - Length checks on `summary` to avoid super-long hallucinations.

4. **Statistical anomaly checks**
   - Over a batch, detect extreme outliers (e.g., one package with thousands of topics, or `date_issued` far in the past/future).

### 4.2 Validation agent and state machine

We can add a dedicated **ValidationAgent** and a state machine for packages:

States:

- `pending` – not yet processed.
- `ingested_raw` – in DB, raw_json stored.
- `normalized` – normalized_json populated.
- `validated_ok` – passed validation.
- `needs_retry` – failed transient checks; should be retried.
- `needs_human_review` – failed high-severity checks; hold for manual review.

#### Algorithm sketch

For each package:

1. After `upsert_package` → mark `state = 'ingested_raw'` (could be a column or a separate status table).
2. After `LLMNormalizerAgent` finishes → mark `state = 'normalized'`.
3. ValidationAgent runs a series of checks:
   - Executes SQL queries to fetch the package row and perhaps neighbors.
   - Checks invariants (schema, external counts, LLM fields).
   - Produces a `ValidationReport` object with:
     - `status`: `ok`, `retry`, `human_review`.
     - `reasons`: list of messages.
4. Based on `ValidationReport.status`:
   - `ok` → set `state = 'validated_ok'`.
   - `retry` → enqueue a retry task (e.g., `refetch_package_summary`, `re_normalize_with_llm`) with a retry counter.
   - `human_review` → log and mark for manual triage; do not retry automatically.

In code terms, we’d add:

- A new `SwarmTask(kind="validate_package", payload={"package_id": ...})`.
- A `ValidationAgent` that can handle that kind.
- Hooks in `GovinfoUpsertAgent` and `LLMNormalizerAgent` to enqueue validation tasks when appropriate.

### 4.3 Self-validation with LLM assistance

The ValidationAgent can be partly LLM-driven:

1. Run SQL queries to compile a compact diagnostic JSON for a package, e.g.:

```json
{
  "package_id": "BILLS-116hr1565ih",
  "collection_code": "BILLS",
  "title_length": 87,
  "has_normalized_json": true,
  "normalized_keys": ["topics", "policy_domain", ...],
  "topics_count": 4,
  "summary_length": 255,
  "congress": 116,
  "date_issued": "2019-03-06",
  "ingest_run_id": 42
}
```

2. Provide to an LLM with a compact prompt:

> “Given this diagnostic JSON and the invariant rules, decide if this package is OK, needs retry, or needs human review.
>  Return only a JSON object: {"status": "ok|retry|human_review", "reasons": ["..."]}.”

3. Parse the result and update state accordingly.

We treat the LLM as a **soft validator** that can reason about edge cases, while the hard invariants (unique keys, null constraints, types) are enforced by PostgreSQL and explicit checks.

### 4.4 Retry / backoff strategy

For tasks marked `needs_retry`:

- Track a retry count per package (e.g., in a `govinfo_package_status` table or via `normalized_json.retries`).
- Use exponential backoff or scheduled re-runs.
- Stop retrying after `N` attempts and escalate to `needs_human_review`.

For transient failures (network errors, 5xx from govinfo, OpenRouter timeouts), the self-validating loop will:

1. Re-enqueue the task.
2. Optionally mark the run in `govinfo_ingest_log` for observability.

---

## 5. Test Strategy (Unit, Integration, Property)

### 5.1 Unit tests

Target small units with `pytest` and a temporary test database (or a transactional test fixture):

1. **`upsert_package`**
   - Insert a package and assert row exists with correct fields.
   - Call `upsert_package` again with changed title and ensure a single row is updated (same `package_id`).
   - Verify `date_issued` parsing and fallback behavior when invalid.

2. **`build_published_url` / `fetch_published_page`**
   - Use `responses` or `requests-mock` to simulate govinfo responses.
   - Ensure pagination logic correctly extracts `next_offset_mark` from `nextPage`.

3. **`llm_normalize_package`** (with a stubbed client)
   - Mock an OpenRouter client that returns a known JSON string.
   - Assert the parsed result is the expected dict.
   - Test failure cases (invalid JSON, exceptions) and ensure `None` is returned.

4. **Agents**
   - `GovinfoPublishedAgent`: given a `fetch_published_page` task and a mocked `fetch_published_page` function, assert it emits the correct follow-up tasks.
   - `GovinfoUpsertAgent`: test handling of `max_packages` and `dry_run` flags.

### 5.2 Integration tests

1. **End-to-end dry-run**
   - Start with an empty schema (on a test DB).
   - Run `govinfo_swarm_ingest.py --init-db --ingest --start-date X --end-date Y --dry-run` with a mocked `requests.Session` that returns fixed JSON.
   - Assert no rows are written, but logs show expected actions.

2. **End-to-end real insert (with fake govinfo)**
   - Same as above, but with `dry_run=False` and a very small number of packages.
   - Assert that the expected `govinfo_packages` rows are present after the run.

3. **LLM path (optional)**
   - Use a test OpenRouter client or stub to simulate normalization.
   - Ensure `normalized_json` is populated as expected.

### 5.3 Property-based tests (optional, but powerful)

Using `hypothesis`:

- Generate random but valid package JSON structures.
- Check that two runs of ingestion with the same inputs produce:
  - Same row count.
  - Same `package_id` set.
  - Stable `normalized_json` shape (when using deterministic or stubbed LLM responses).

---

## 6. Concrete Next Steps

1. **Add a ValidationAgent implementation**
   - New `SwarmTask(kind="validate_package")`.
   - Agent that queries DB, builds diagnostics JSON, and (optionally) calls an LLM to decide `ok|retry|human_review`.
   - Update the package status accordingly.

2. **Extend schema to full 20-table govinfo layout**
   - Introduce tables for sections, citations, mentions, file variants, etc., and wire them into the ingestion flow.
   - Keep the current `govinfo_packages` design as the central hub.

3. **Hook into OpenDiscourse’s broader pipeline**
   - Connect `govinfo_packages` and `normalized_json` to your cross-source `documents` and `entities` model.
   - Feed normalized text and summaries into your vector DB for downstream RAG / analytics.

4. **Add observability**
   - Expose Prometheus metrics (e.g., `govinfo_packages_ingested_total`, `govinfo_llm_normalization_errors_total`).
   - Build a small dashboard to visualize ingestion health and backlog.

These notes should serve as a reference for wiring this into the broader OpenDiscourse ingest + analysis system and for guiding the next round of coding (ValidationAgent, extended schema, and test suite).

