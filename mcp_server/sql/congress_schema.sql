-- Congress.gov schema for Postgres
-- Store bills, members, votes, and raw payloads

CREATE TABLE IF NOT EXISTS congress_bills (
  id TEXT PRIMARY KEY, -- composite or generated id (e.g., congress:billType:billNumber)
  congress SMALLINT,
  bill_type TEXT,
  bill_number INT,
  title TEXT,
  latest_action_date DATE,
  latest_action_description TEXT,
  subjects TEXT[],
  sponsors JSONB,
  raw JSONB,
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_congress_bills_congress ON congress_bills(congress);
CREATE INDEX IF NOT EXISTS idx_congress_bills_billnum ON congress_bills(bill_type, bill_number);

CREATE TABLE IF NOT EXISTS congress_members (
  bioguide_id TEXT PRIMARY KEY,
  first_name TEXT,
  last_name TEXT,
  party TEXT,
  state TEXT,
  district TEXT,
  raw JSONB,
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS congress_votes (
  id TEXT PRIMARY KEY,
  congress SMALLINT,
  session SMALLINT,
  vote_number TEXT,
  date TIMESTAMPTZ,
  result TEXT,
  counts JSONB,
  raw JSONB,
  created_on TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_congress_votes_date ON congress_votes(date);
