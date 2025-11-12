-- Congress.gov CRS Reports schema
-- Congressional Research Service reports

CREATE TABLE IF NOT EXISTS congress_crs_reports (
  -- Primary identifiers
  report_number TEXT PRIMARY KEY, -- CRS report number
  report_id TEXT UNIQUE, -- Alternative ID

  -- Report information
  title TEXT,
  summary TEXT,

  -- Report details
  authors TEXT[],
  publication_date DATE,
  last_updated DATE,

  -- Content and URLs
  pdf_url TEXT,
  html_url TEXT,
  xml_url TEXT,

  -- Categories and topics
  categories TEXT[],
  topics TEXT[],

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for CRS reports
CREATE INDEX IF NOT EXISTS idx_congress_crs_reports_publication_date ON congress_crs_reports(publication_date);
CREATE INDEX IF NOT EXISTS idx_congress_crs_reports_last_updated ON congress_crs_reports(last_updated);
CREATE INDEX IF NOT EXISTS idx_congress_crs_reports_categories ON congress_crs_reports USING GIN(categories);
CREATE INDEX IF NOT EXISTS idx_congress_crs_reports_topics ON congress_crs_reports USING GIN(topics);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_crs_reports_title_search ON congress_crs_reports USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_congress_crs_reports_summary_search ON congress_crs_reports USING GIN(to_tsvector('english', summary));
