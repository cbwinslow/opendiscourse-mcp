-- NDJSON ingestion toolkit for Postgres (staging + validated upserts)
--
-- Usage overview (psql):
--   \i scripts/ingestion/sql/ndjson_ingestion.sql
--   SELECT ingestion_meta.begin_batch('congress_bills', '/path/to/file.ndjson', 'sha256=...', 25000);
--   COPY ingestion_staging.ndjson_lines (batch_id, raw)
--     FROM PROGRAM 'cat /path/to/file.ndjson'
--     WITH (FORMAT text);
--   SELECT ingestion_congress.load_bills_from_staging('<batch_id>');
--   SELECT * FROM ingestion_validation.batch_summary('<batch_id>');

CREATE SCHEMA IF NOT EXISTS ingestion_meta;
CREATE SCHEMA IF NOT EXISTS ingestion_staging;
CREATE SCHEMA IF NOT EXISTS ingestion_validation;
CREATE SCHEMA IF NOT EXISTS ingestion_congress;

-- Batch tracker
CREATE TABLE IF NOT EXISTS ingestion_meta.ndjson_batches (
    batch_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source         TEXT NOT NULL,
    file_path      TEXT NOT NULL,
    manifest_path  TEXT,
    checksum       TEXT,
    expected_rows  INTEGER,
    status         TEXT NOT NULL DEFAULT 'pending', -- pending|staged|loaded|failed
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at   TIMESTAMPTZ,
    records_loaded INTEGER DEFAULT 0,
    errors         JSONB DEFAULT '[]'::jsonb,
    repo_ref       TEXT
);

-- Raw NDJSON staging (one row per JSON object)
CREATE TABLE IF NOT EXISTS ingestion_staging.ndjson_lines (
    batch_id UUID NOT NULL REFERENCES ingestion_meta.ndjson_batches(batch_id) ON DELETE CASCADE,
    line_no  BIGINT GENERATED ALWAYS AS IDENTITY,
    raw      JSONB NOT NULL
) PARTITION BY HASH (batch_id);

-- Create 8 hash partitions for parallel COPY/ingest
DO $$
BEGIN
  FOR i IN 0..7 LOOP
    EXECUTE format(
      'CREATE TABLE IF NOT EXISTS ingestion_staging.ndjson_lines_p%s PARTITION OF ingestion_staging.ndjson_lines FOR VALUES WITH (MODULUS 8, REMAINDER %s);',
      i, i
    );
  END LOOP;
END$$;

-- Begin a batch
CREATE OR REPLACE FUNCTION ingestion_meta.begin_batch(
  p_source TEXT,
  p_file_path TEXT,
  p_checksum TEXT DEFAULT NULL,
  p_expected_rows INTEGER DEFAULT NULL,
  p_manifest_path TEXT DEFAULT NULL,
  p_repo_ref TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
  v_batch_id UUID;
BEGIN
  INSERT INTO ingestion_meta.ndjson_batches(source, file_path, checksum, expected_rows, manifest_path, repo_ref)
  VALUES (p_source, p_file_path, p_checksum, p_expected_rows, p_manifest_path, p_repo_ref)
  RETURNING batch_id INTO v_batch_id;
  RETURN v_batch_id;
END;
$$ LANGUAGE plpgsql;

-- Mark batch completion
CREATE OR REPLACE FUNCTION ingestion_meta.complete_batch(
  p_batch_id UUID,
  p_status TEXT,
  p_records INTEGER,
  p_errors JSONB DEFAULT '[]'::jsonb
) RETURNS VOID AS $$
BEGIN
  UPDATE ingestion_meta.ndjson_batches
  SET status = p_status,
      records_loaded = p_records,
      errors = COALESCE(p_errors, '[]'::jsonb),
      completed_at = now()
  WHERE batch_id = p_batch_id;
END;
$$ LANGUAGE plpgsql;

-- Congress bills loader from staging into congress_bills
CREATE OR REPLACE FUNCTION ingestion_congress.load_bills_from_staging(p_batch_id UUID)
RETURNS TABLE(inserted INTEGER, updated INTEGER, skipped INTEGER) AS $$
DECLARE
  v_inserted INTEGER := 0;
  v_updated  INTEGER := 0;
  v_skipped  INTEGER := 0;
BEGIN
  WITH src AS (
    SELECT raw
    FROM ingestion_staging.ndjson_lines
    WHERE batch_id = p_batch_id
  ), normalized AS (
    SELECT
      (raw->>'congress')::INT                AS congress,
      lower(raw->>'type')                    AS bill_type,
      (raw->>'number')::INT                  AS bill_number,
      raw->>'title'                          AS title,
      raw->'latestAction'->>'actionDate'     AS latest_action_date,
      raw->'latestAction'->>'text'           AS latest_action_text,
      raw->>'originChamber'                  AS origin_chamber,
      raw->>'currentChamber'                 AS current_chamber,
      (raw->>'introducedDate')               AS introduced_date,
      COALESCE(raw->'subjects', '[]'::jsonb) AS subjects,
      COALESCE(raw->'sponsors', '[]'::jsonb) AS sponsors,
      raw                                     AS raw_json,
      format('%s:%s:%s',
        (raw->>'congress'),
        lower(raw->>'type'),
        (raw->>'number')
      ) AS bill_id
    FROM src
  ), upsert AS (
    INSERT INTO congress_bills (
      bill_id, congress, bill_type, bill_number, title, introduced_date,
      origin_chamber, current_chamber, latest_action_date, latest_action_text,
      sponsors, subjects, raw, updated_on, last_api_update
    )
    SELECT
      bill_id, congress, bill_type, bill_number, title, introduced_date,
      origin_chamber, current_chamber, latest_action_date, latest_action_text,
      sponsors, subjects, raw_json, now(), now()
    FROM normalized
    ON CONFLICT (bill_id) DO UPDATE
      SET congress = EXCLUDED.congress,
          bill_type = EXCLUDED.bill_type,
          bill_number = EXCLUDED.bill_number,
          title = EXCLUDED.title,
          introduced_date = EXCLUDED.introduced_date,
          origin_chamber = EXCLUDED.origin_chamber,
          current_chamber = EXCLUDED.current_chamber,
          latest_action_date = EXCLUDED.latest_action_date,
          latest_action_text = EXCLUDED.latest_action_text,
          sponsors = EXCLUDED.sponsors,
          subjects = EXCLUDED.subjects,
          raw = EXCLUDED.raw,
          updated_on = now(),
          last_api_update = now()
    RETURNING xmax = 0 AS inserted_flag
  )
  SELECT
    SUM(CASE WHEN inserted_flag THEN 1 ELSE 0 END),
    SUM(CASE WHEN NOT inserted_flag THEN 1 ELSE 0 END),
    0
  INTO v_inserted, v_updated, v_skipped
  FROM upsert;

  PERFORM ingestion_meta.complete_batch(p_batch_id, 'loaded', v_inserted + v_updated, '[]'::jsonb);
  RETURN QUERY SELECT COALESCE(v_inserted,0), COALESCE(v_updated,0), COALESCE(v_skipped,0);
END;
$$ LANGUAGE plpgsql;

-- Validation summaries per batch
CREATE OR REPLACE FUNCTION ingestion_validation.batch_summary(p_batch_id UUID)
RETURNS TABLE(
  batch_id UUID,
  status TEXT,
  expected_rows INTEGER,
  staged_rows BIGINT,
  loaded_rows INTEGER,
  duplicates BIGINT
) AS $$
BEGIN
  RETURN QUERY
  WITH staged AS (
    SELECT count(*) AS c FROM ingestion_staging.ndjson_lines WHERE batch_id = p_batch_id
  ), loaded AS (
    SELECT count(*) AS c FROM congress_bills WHERE raw->>'batch_id' = p_batch_id::text
  )
  SELECT
    b.batch_id,
    b.status,
    b.expected_rows,
    s.c AS staged_rows,
    b.records_loaded AS loaded_rows,
    0::BIGINT AS duplicates  -- placeholder; relies on bill_id uniqueness
  FROM ingestion_meta.ndjson_batches b
  LEFT JOIN staged s ON true
  WHERE b.batch_id = p_batch_id;
END;
$$ LANGUAGE plpgsql;

-- Helper: view to list recent batches
CREATE OR REPLACE VIEW ingestion_meta.recent_batches AS
SELECT
  batch_id,
  source,
  file_path,
  manifest_path,
  status,
  expected_rows,
  records_loaded,
  started_at,
  completed_at
FROM ingestion_meta.ndjson_batches
ORDER BY started_at DESC
LIMIT 200;

