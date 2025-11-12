-- Congress.gov committee prints schema

CREATE TABLE IF NOT EXISTS congress_committee_prints (
  -- Primary identifiers
  print_id TEXT PRIMARY KEY, -- e.g., "118-1"
  congress SMALLINT NOT NULL,
  chamber TEXT NOT NULL,
  jacket_number TEXT NOT NULL,

  -- Print information
  title TEXT,
  committee_code TEXT,
  committee_name TEXT,

  -- Print details
  part TEXT,
  version TEXT,

  -- Dates
  issued_date DATE,
  last_modified TIMESTAMPTZ,

  -- Content
  pages INTEGER,

  -- URLs
  pdf_url TEXT,
  xml_url TEXT,
  html_url TEXT,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL,

  -- Foreign key
  FOREIGN KEY (committee_code) REFERENCES congress_committees(committee_code) ON DELETE SET NULL
);

-- Indexes for committee prints
CREATE INDEX IF NOT EXISTS idx_congress_committee_prints_congress ON congress_committee_prints(congress);
CREATE INDEX IF NOT EXISTS idx_congress_committee_prints_chamber ON congress_committee_prints(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_committee_prints_committee ON congress_committee_prints(committee_code);
CREATE INDEX IF NOT EXISTS idx_congress_committee_prints_issued_date ON congress_committee_prints(issued_date);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_committee_prints_title_search ON congress_committee_prints USING GIN(to_tsvector('english', title));
