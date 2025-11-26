# Congress.gov Ingestion Bundle

This bundle contains Python scripts and SQL helpers to ingest Congress.gov v3 API
collections into NDJSON/SQLite or PostgreSQL JSONB, with incremental watermarking.

Files:

- `congress_gov_unbounded_ingest.py` — NDJSON + optional SQLite, unbounded.
- `congress_gov_pg_ingest.py`       — PostgreSQL JSONB + watermark, optional NDJSON.
- `congress_schema_views.sql`       — Example materialized views and indexes.
