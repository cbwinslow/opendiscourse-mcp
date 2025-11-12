-- OpenStates schema for Postgres
-- Primary entities: bills, people, events, organizations

CREATE TABLE IF NOT EXISTS openstates_bills (
  id TEXT PRIMARY KEY, -- ocd-bill/.. uuid
  session TEXT,
  jurisdiction TEXT,
  identifier TEXT,
  title TEXT,
  classification TEXT[],
  subjects TEXT[],
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  first_action_date DATE,
  latest_action_date DATE,
  latest_action_description TEXT,
  openstates_url TEXT,
  raw JSONB,
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_openstates_bills_jurisdiction ON openstates_bills(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_openstates_bills_session ON openstates_bills(session);
CREATE INDEX IF NOT EXISTS idx_openstates_bills_updated_at ON openstates_bills(updated_at);

CREATE TABLE IF NOT EXISTS openstates_people (
  id TEXT PRIMARY KEY,
  name TEXT,
  party TEXT,
  jurisdiction TEXT,
  given_name TEXT,
  family_name TEXT,
  image TEXT,
  email TEXT,
  gender TEXT,
  birth_date DATE,
  death_date DATE,
  extras JSONB,
  raw JSONB,
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_openstates_people_jurisdiction ON openstates_people(jurisdiction);

CREATE TABLE IF NOT EXISTS openstates_events (
  id TEXT PRIMARY KEY,
  name TEXT,
  jurisdiction TEXT,
  description TEXT,
  classification TEXT,
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  all_day BOOLEAN,
  status TEXT,
  location JSONB,
  raw JSONB,
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_openstates_events_jurisdiction ON openstates_events(jurisdiction);
