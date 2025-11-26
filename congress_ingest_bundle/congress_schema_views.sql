-- congress_schema_views.sql
-- Helper SQL for OpenDiscourse / Congress.gov ingestion
-- Creates materialized views and indexes on top of the JSONB tables
-- produced by congress_gov_pg_ingest.py.

-- NOTE: You may need to adjust JSON paths depending on the actual shape
-- of the raw payloads stored in the `raw` column.

-- ===== Bills flattened view =====
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_bills_flat AS
SELECT
    id,
    raw,
    (raw->>'congress')               AS congress,
    (raw->>'number')                 AS bill_number,
    (raw->>'title')                  AS title,
    (raw->>'type')                   AS bill_type,
    (raw->'sponsor'->>'fullName')    AS sponsor_name,
    (raw->'sponsor'->>'party')       AS sponsor_party,
    (raw->'sponsor'->>'state')       AS sponsor_state,
    (raw->>'introducedDate')::date   AS introduced_date,
    (raw->>'latestActionDate')::date AS latest_action_date,
    (raw->>'latestActionText')       AS latest_action_text,
    ingested_at
FROM public.bills;

CREATE INDEX IF NOT EXISTS mv_bills_flat_congress_num_idx
    ON public.mv_bills_flat (congress, bill_number);

CREATE INDEX IF NOT EXISTS mv_bills_flat_sponsor_party_idx
    ON public.mv_bills_flat (sponsor_party);


-- ===== Members flattened view =====
CREATE MATERIALIZED VIEW IF NOT EXISTS public.mv_members_flat AS
SELECT
    id,
    raw,
    (raw->>'bioguideId') AS bioguide_id,
    (raw->>'firstName')  AS first_name,
    (raw->>'lastName')   AS last_name,
    (raw->>'party')      AS party,
    (raw->>'state')      AS state,
    (raw->>'district')   AS district,
    (raw->>'chamber')    AS chamber,
    ingested_at
FROM public.members;

CREATE INDEX IF NOT EXISTS mv_members_flat_bioguide_idx
    ON public.mv_members_flat (bioguide_id);

CREATE INDEX IF NOT EXISTS mv_members_flat_party_state_idx
    ON public.mv_members_flat (party, state);


-- ===== Watermark inspection =====
-- Quick helper query to inspect the incremental watermark table.
-- (Table is auto-created by congress_gov_pg_ingest.py.)
--
-- SELECT * FROM public.congress_ingest_watermark ORDER BY collection;
