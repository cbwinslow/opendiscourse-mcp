-- Congress.gov laws schema
-- Enacted legislation (public and private laws)

CREATE TABLE IF NOT EXISTS congress_laws (
  -- Primary identifiers
  law_id TEXT PRIMARY KEY, -- e.g., "117-1" (congress-lawNumber)
  congress SMALLINT NOT NULL,
  law_type TEXT NOT NULL, -- public, private
  law_number TEXT NOT NULL,

  -- Law information
  title TEXT,
  enacted_date DATE,
  bill_id TEXT, -- Reference to originating bill

  -- Law text and content
  text TEXT, -- Full text of the law
  pages INTEGER,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL,

  -- Foreign key (optional, as not all laws may have originating bills)
  FOREIGN KEY (bill_id) REFERENCES congress_bills(bill_id) ON DELETE SET NULL
);

-- Indexes for laws
CREATE INDEX IF NOT EXISTS idx_congress_laws_congress ON congress_laws(congress);
CREATE INDEX IF NOT EXISTS idx_congress_laws_type ON congress_laws(law_type);
CREATE INDEX IF NOT EXISTS idx_congress_laws_number ON congress_laws(law_number);
CREATE INDEX IF NOT EXISTS idx_congress_laws_enacted_date ON congress_laws(enacted_date);
CREATE INDEX IF NOT EXISTS idx_congress_laws_bill ON congress_laws(bill_id);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_laws_title_search ON congress_laws USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_congress_laws_text_search ON congress_laws USING GIN(to_tsvector('english', text));
