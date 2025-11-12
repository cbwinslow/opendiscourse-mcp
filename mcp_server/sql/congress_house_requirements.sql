-- Congress.gov House requirements schema

CREATE TABLE IF NOT EXISTS congress_house_requirements (
  -- Primary identifiers
  requirement_number TEXT PRIMARY KEY,

  -- Requirement information
  title TEXT,
  description TEXT,

  -- Dates
  date_issued DATE,
  last_modified TIMESTAMPTZ,

  -- Content and URLs
  pdf_url TEXT,
  html_url TEXT,
  xml_url TEXT,

  -- Matching communications
  matching_communications JSONB, -- Array of related communications

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for house requirements
CREATE INDEX IF NOT EXISTS idx_congress_house_requirements_date ON congress_house_requirements(date_issued);
CREATE INDEX IF NOT EXISTS idx_congress_house_requirements_matching_communications ON congress_house_requirements USING GIN(matching_communications);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_house_requirements_title_search ON congress_house_requirements USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_congress_house_requirements_description_search ON congress_house_requirements USING GIN(to_tsvector('english', description));
