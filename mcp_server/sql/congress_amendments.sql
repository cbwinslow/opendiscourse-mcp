-- Congress.gov amendments schema
-- Standalone amendments (separate from bill amendments)

CREATE TABLE IF NOT EXISTS congress_amendments (
  -- Primary identifiers
  amendment_id TEXT PRIMARY KEY, -- e.g., "117-HAMDT-1"
  congress SMALLINT NOT NULL,
  amendment_type TEXT NOT NULL, -- hamdt, samdt
  amendment_number TEXT NOT NULL,

  -- Amendment information
  purpose TEXT,
  description TEXT,
  introduced_date DATE,
  latest_action_date DATE,
  latest_action_text TEXT,

  -- Relationships
  amends_bill_id TEXT, -- Bill being amended
  sponsor_bioguide_id TEXT, -- Primary sponsor

  -- Amendment details
  chamber TEXT, -- house, senate
  proposed_date DATE,
  submitted_date DATE,

  -- Status
  disposition TEXT, -- Agreed to, Rejected, etc.
  disposition_date DATE,

  -- Content
  text TEXT, -- Amendment text

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL,

  -- Foreign keys
  FOREIGN KEY (amends_bill_id) REFERENCES congress_bills(bill_id) ON DELETE SET NULL,
  FOREIGN KEY (sponsor_bioguide_id) REFERENCES congress_members(bioguide_id) ON DELETE SET NULL
);

-- Indexes for amendments
CREATE INDEX IF NOT EXISTS idx_congress_amendments_congress ON congress_amendments(congress);
CREATE INDEX IF NOT EXISTS idx_congress_amendments_type ON congress_amendments(amendment_type);
CREATE INDEX IF NOT EXISTS idx_congress_amendments_number ON congress_amendments(amendment_number);
CREATE INDEX IF NOT EXISTS idx_congress_amendments_bill ON congress_amendments(amends_bill_id);
CREATE INDEX IF NOT EXISTS idx_congress_amendments_sponsor ON congress_amendments(sponsor_bioguide_id);
CREATE INDEX IF NOT EXISTS idx_congress_amendments_chamber ON congress_amendments(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_amendments_introduced_date ON congress_amendments(introduced_date);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_amendments_purpose_search ON congress_amendments USING GIN(to_tsvector('english', purpose));
CREATE INDEX IF NOT EXISTS idx_congress_amendments_description_search ON congress_amendments USING GIN(to_tsvector('english', description));
CREATE INDEX IF NOT EXISTS idx_congress_amendments_text_search ON congress_amendments USING GIN(to_tsvector('english', text));
