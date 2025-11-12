-- Congress.gov committee reports schema

CREATE TABLE IF NOT EXISTS congress_committee_reports (
  -- Primary identifiers
  report_id TEXT PRIMARY KEY, -- e.g., "118-HRPT-1"
  congress SMALLINT NOT NULL,
  report_type TEXT NOT NULL, -- hrpt, srpt, etc.
  report_number TEXT NOT NULL,

  -- Report information
  title TEXT,
  committee_code TEXT,
  committee_name TEXT,

  -- Report details
  subcommittee_name TEXT,
  part TEXT, -- Report part/section
  version TEXT,

  -- Dates
  issued_date DATE,
  last_modified TIMESTAMPTZ,

  -- Content
  pages INTEGER,

  -- URLs and references
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

-- Indexes for committee reports
CREATE INDEX IF NOT EXISTS idx_congress_committee_reports_congress ON congress_committee_reports(congress);
CREATE INDEX IF NOT EXISTS idx_congress_committee_reports_type ON congress_committee_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_congress_committee_reports_number ON congress_committee_reports(report_number);
CREATE INDEX IF NOT EXISTS idx_congress_committee_reports_committee ON congress_committee_reports(committee_code);
CREATE INDEX IF NOT EXISTS idx_congress_committee_reports_issued_date ON congress_committee_reports(issued_date);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_committee_reports_title_search ON congress_committee_reports USING GIN(to_tsvector('english', title));
