-- Congress.gov committee meetings schema

CREATE TABLE IF NOT EXISTS congress_committee_meetings (
  -- Primary identifiers
  meeting_id TEXT PRIMARY KEY, -- e.g., "118-1"
  congress SMALLINT NOT NULL,
  chamber TEXT NOT NULL,
  event_id TEXT NOT NULL,

  -- Meeting information
  title TEXT,
  committee_code TEXT,
  committee_name TEXT,

  -- Meeting details
  meeting_type TEXT,
  date DATE,
  time TIME,
  location TEXT,
  room TEXT,

  -- Status and details
  status TEXT, -- scheduled, held, postponed, cancelled
  video_url TEXT,
  transcript_url TEXT,

  -- Witnesses and topics
  witnesses JSONB, -- Array of witness objects
  topics JSONB, -- Array of topic objects

  -- Documents
  documents JSONB, -- Array of document objects

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL,

  -- Foreign key
  FOREIGN KEY (committee_code) REFERENCES congress_committees(committee_code) ON DELETE SET NULL
);

-- Indexes for committee meetings
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_congress ON congress_committee_meetings(congress);
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_chamber ON congress_committee_meetings(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_committee ON congress_committee_meetings(committee_code);
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_date ON congress_committee_meetings(date);
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_status ON congress_committee_meetings(status);
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_witnesses ON congress_committee_meetings USING GIN(witnesses);
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_topics ON congress_committee_meetings USING GIN(topics);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_committee_meetings_title_search ON congress_committee_meetings USING GIN(to_tsvector('english', title));
