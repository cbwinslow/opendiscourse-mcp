-- Congress.gov Congressional Record schema
-- Daily official record of congressional proceedings

CREATE TABLE IF NOT EXISTS congress_congressional_record (
  -- Primary identifiers
  record_id TEXT PRIMARY KEY, -- e.g., "2023-01-01"
  record_date DATE NOT NULL,
  record_type TEXT NOT NULL, -- daily, bound

  -- Record details
  volume_number INTEGER,
  issue_number INTEGER,
  pages INTEGER,

  -- Content and URLs
  pdf_url TEXT,
  html_url TEXT,
  xml_url TEXT,

  -- Daily record specific
  start_page INTEGER,
  end_page INTEGER,

  -- Bound record specific
  year INTEGER,
  month INTEGER,
  day INTEGER,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for congressional record
CREATE INDEX IF NOT EXISTS idx_congress_congressional_record_date ON congress_congressional_record(record_date);
CREATE INDEX IF NOT EXISTS idx_congress_congressional_record_type ON congress_congressional_record(record_type);
CREATE INDEX IF NOT EXISTS idx_congress_congressional_record_volume ON congress_congressional_record(volume_number);
CREATE INDEX IF NOT EXISTS idx_congress_congressional_record_year ON congress_congressional_record(year);
