-- Congress.gov communications schema
-- House and Senate communications

CREATE TABLE IF NOT EXISTS congress_communications (
  -- Primary identifiers
  communication_id TEXT PRIMARY KEY, -- e.g., "118-HC-1"
  congress SMALLINT NOT NULL,
  chamber TEXT NOT NULL, -- house, senate
  communication_type TEXT NOT NULL,
  communication_number TEXT NOT NULL,

  -- Communication details
  title TEXT,
  date_issued DATE,
  submitter TEXT,

  -- Content and URLs
  pdf_url TEXT,
  html_url TEXT,
  xml_url TEXT,

  -- House communication specific
  house_requirement_number TEXT,

  -- Senate communication specific
  senate_requirement_number TEXT,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for communications
CREATE INDEX IF NOT EXISTS idx_congress_communications_congress ON congress_communications(congress);
CREATE INDEX IF NOT EXISTS idx_congress_communications_chamber ON congress_communications(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_communications_type ON congress_communications(communication_type);
CREATE INDEX IF NOT EXISTS idx_congress_communications_date ON congress_communications(date_issued);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_communications_title_search ON congress_communications USING GIN(to_tsvector('english', title));
