-- Congress.gov comprehensive schema for Postgres
-- Based on actual Congress.gov API v3 responses

CREATE TABLE IF NOT EXISTS congress_bills (
  -- Primary identifiers
  bill_id TEXT PRIMARY KEY, -- e.g., "118-HR-1"
  congress SMALLINT NOT NULL,
  bill_type TEXT NOT NULL, -- hr, s, hres, sconres, etc.
  bill_number TEXT NOT NULL, -- API returns as string

  -- Basic bill information
  title TEXT,
  introduced_date DATE,
  origin_chamber TEXT, -- HOUSE, SENATE
  current_chamber TEXT, -- HOUSE, SENATE, JOINT

  -- Status and actions
  latest_action_date DATE,
  latest_action_text TEXT,
  latest_action_type TEXT,

  -- Relationships (stored as JSONB since API returns paginated objects)
  sponsors JSONB, -- Direct sponsors array
  cosponsors JSONB, -- {count, countIncludingWithdrawnCosponsors, url}
  committees JSONB, -- {count, url}
  actions JSONB, -- {count, url}
  amendments JSONB, -- {count, url}
  related_bills JSONB, -- {count, url}

  -- Content
  subjects JSONB, -- {count, url}
  summaries JSONB, -- {count, url}
  text JSONB, -- {count, url}
  titles JSONB, -- {count, url}

  -- CBO cost estimates
  cbo_cost_estimates JSONB, -- Array of cost estimate objects

  -- Policy and categorization
  policy_area JSONB, -- {name, policyAreaDescription}

  -- Constitutional authority
  constitutional_authority_statement_text TEXT,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for bills
CREATE INDEX IF NOT EXISTS idx_congress_bills_congress ON congress_bills(congress);
CREATE INDEX IF NOT EXISTS idx_congress_bills_type ON congress_bills(bill_type);
CREATE INDEX IF NOT EXISTS idx_congress_bills_number ON congress_bills(bill_number);
CREATE INDEX IF NOT EXISTS idx_congress_bills_introduced_date ON congress_bills(introduced_date);
CREATE INDEX IF NOT EXISTS idx_congress_bills_origin_chamber ON congress_bills(origin_chamber);
CREATE INDEX IF NOT EXISTS idx_congress_bills_current_chamber ON congress_bills(current_chamber);
CREATE INDEX IF NOT EXISTS idx_congress_bills_policy_area ON congress_bills USING GIN(policy_area);
CREATE INDEX IF NOT EXISTS idx_congress_bills_sponsors ON congress_bills USING GIN(sponsors);
CREATE INDEX IF NOT EXISTS idx_congress_bills_cosponsors ON congress_bills USING GIN(cosponsors);
CREATE INDEX IF NOT EXISTS idx_congress_bills_committees ON congress_bills USING GIN(committees);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_bills_title_search ON congress_bills USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_congress_bills_latest_action_search ON congress_bills USING GIN(to_tsvector('english', latest_action_text));

CREATE TABLE IF NOT EXISTS congress_members (
  -- Primary identifiers
  bioguide_id TEXT PRIMARY KEY,
  direct_order_name TEXT, -- e.g., "Sherrod Brown"
  inverted_order_name TEXT, -- e.g., "Brown, Sherrod"
  honorific_name TEXT, -- e.g., "Mr.", "Ms."

  -- Name components
  first_name TEXT,
  last_name TEXT,
  birth_year INTEGER,

  -- Political information
  party_name TEXT, -- Current party
  party_history JSONB, -- Array of party changes over time
  state TEXT,
  district TEXT, -- May be null for senators

  -- Current status
  current_member BOOLEAN DEFAULT FALSE,

  -- Terms in office
  terms JSONB, -- Array of term objects with chamber, congress, district, etc.

  -- Previous names (if any)
  previous_names JSONB, -- Array of name change objects

  -- Depiction/image
  depiction JSONB, -- {imageUrl, attribution}

  -- Legislative activity
  sponsored_legislation JSONB, -- {count, url}
  cosponsored_legislation JSONB, -- {count, url}

  -- Leadership positions
  leadership_positions JSONB, -- Array of leadership roles

  -- Committee assignments
  committee_assignments JSONB, -- Array of committee assignments

  -- Voting record
  voting_record JSONB, -- Aggregated voting statistics

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for members
CREATE INDEX IF NOT EXISTS idx_congress_members_state ON congress_members(state);
CREATE INDEX IF NOT EXISTS idx_congress_members_party ON congress_members(party_name);
CREATE INDEX IF NOT EXISTS idx_congress_members_district ON congress_members(district);
CREATE INDEX IF NOT EXISTS idx_congress_members_current ON congress_members(current_member);
CREATE INDEX IF NOT EXISTS idx_congress_members_name ON congress_members(direct_order_name);
CREATE INDEX IF NOT EXISTS idx_congress_members_party_history ON congress_members USING GIN(party_history);
CREATE INDEX IF NOT EXISTS idx_congress_members_terms ON congress_members USING GIN(terms);
CREATE INDEX IF NOT EXISTS idx_congress_members_committee_assignments ON congress_members USING GIN(committee_assignments);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_members_name_search ON congress_members USING GIN(to_tsvector('english', direct_order_name));

CREATE TABLE IF NOT EXISTS congress_committees (
  -- Primary identifiers
  committee_code TEXT PRIMARY KEY, -- e.g., "HSAP"
  chamber TEXT NOT NULL, -- house, senate, joint
  committee_name TEXT NOT NULL,

  -- Committee details
  congress SMALLINT,
  committee_type TEXT, -- standing, select, joint, etc.
  jurisdiction TEXT,
  parent_committee_code TEXT,

  -- Membership
  chair JSONB, -- Chair member info
  ranking_member JSONB, -- Ranking member info
  subcommittee_count INTEGER DEFAULT 0,

  -- Activity
  bills_reported JSONB, -- {count, url}
  hearings_held JSONB, -- {count, url}
  nominations_reported JSONB, -- {count, url}

  -- Subcommittees
  subcommittees JSONB, -- Array of subcommittee objects

  -- Current membership
  current_members JSONB, -- Array of current members

  -- Historical data
  establishment_date DATE,
  abolition_date DATE,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for committees
CREATE INDEX IF NOT EXISTS idx_congress_committees_chamber ON congress_committees(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_committees_congress ON congress_committees(congress);
CREATE INDEX IF NOT EXISTS idx_congress_committees_type ON congress_committees(committee_type);
CREATE INDEX IF NOT EXISTS idx_congress_committees_parent ON congress_committees(parent_committee_code);
CREATE INDEX IF NOT EXISTS idx_congress_committees_name ON congress_committees(committee_name);
CREATE INDEX IF NOT EXISTS idx_congress_committees_current_members ON congress_committees USING GIN(current_members);

CREATE TABLE IF NOT EXISTS congress_votes (
  -- Primary identifiers
  vote_id TEXT PRIMARY KEY, -- e.g., "h2023-05-16.001"
  congress SMALLINT NOT NULL,
  session SMALLINT,
  chamber TEXT NOT NULL, -- house, senate
  roll_number INTEGER,
  vote_date DATE NOT NULL,
  vote_time TIME,

  -- Vote details
  question TEXT, -- The question being voted on
  description TEXT, -- Description of the vote
  vote_type TEXT, -- YEA-AND-NAY, etc.
  result TEXT, -- Agreed to, Rejected, etc.

  -- Vote counts
  total_yes INTEGER DEFAULT 0,
  total_no INTEGER DEFAULT 0,
  total_present INTEGER DEFAULT 0,
  total_not_voting INTEGER DEFAULT 0,

  -- Tie breaker (for Senate)
  tie_breaker JSONB,

  -- Vote document reference
  document JSONB, -- Bill or resolution being voted on

  -- Individual member votes
  member_votes JSONB, -- Array of {member, vote} objects

  -- Amendments
  amendments JSONB, -- Related amendments

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for votes
CREATE INDEX IF NOT EXISTS idx_congress_votes_congress ON congress_votes(congress);
CREATE INDEX IF NOT EXISTS idx_congress_votes_chamber ON congress_votes(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_votes_date ON congress_votes(vote_date);
CREATE INDEX IF NOT EXISTS idx_congress_votes_result ON congress_votes(result);
CREATE INDEX IF NOT EXISTS idx_congress_votes_document ON congress_votes USING GIN(document);
CREATE INDEX IF NOT EXISTS idx_congress_votes_member_votes ON congress_votes USING GIN(member_votes);

CREATE TABLE IF NOT EXISTS congress_bill_actions (
  -- Primary identifiers
  action_id TEXT PRIMARY KEY, -- Composite key
  bill_id TEXT NOT NULL,
  action_date DATE NOT NULL,
  sequence_number INTEGER,

  -- Action details
  action_code TEXT,
  action_text TEXT,
  action_type TEXT, -- Committee, Floor, Presidential, etc.
  chamber TEXT,

  -- Committee information (if committee action)
  committee JSONB,

  -- Source system
  source_system_code TEXT,
  source_system_name TEXT,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),

  -- Foreign key
  FOREIGN KEY (bill_id) REFERENCES congress_bills(bill_id) ON DELETE CASCADE
);

-- Indexes for bill actions
CREATE INDEX IF NOT EXISTS idx_congress_bill_actions_bill ON congress_bill_actions(bill_id);
CREATE INDEX IF NOT EXISTS idx_congress_bill_actions_date ON congress_bill_actions(action_date);
CREATE INDEX IF NOT EXISTS idx_congress_bill_actions_type ON congress_bill_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_congress_bill_actions_chamber ON congress_bill_actions(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_bill_actions_committee ON congress_bill_actions USING GIN(committee);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_bill_actions_text_search ON congress_bill_actions USING GIN(to_tsvector('english', action_text));

CREATE TABLE IF NOT EXISTS congress_bill_text (
  -- Primary identifiers
  text_id TEXT PRIMARY KEY,
  bill_id TEXT NOT NULL,
  text_type TEXT NOT NULL, -- Introduced, Engrossed, Enrolled, etc.
  text_format TEXT NOT NULL, -- XML, HTML, PDF, etc.

  -- Text metadata
  date_issued DATE,
  congress SMALLINT,
  bill_type TEXT,
  bill_number TEXT,
  bill_version TEXT,

  -- Content
  full_text TEXT, -- Full text content when available
  extracted_text TEXT, -- OCR/extracted text from PDFs

  -- File information
  file_path TEXT,
  file_size INTEGER,
  mime_type TEXT,

  -- Processing status
  processing_status TEXT DEFAULT 'pending',
  processing_attempts INTEGER DEFAULT 0,
  last_processing_attempt TIMESTAMPTZ,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),

  -- Foreign key
  FOREIGN KEY (bill_id) REFERENCES congress_bills(bill_id) ON DELETE CASCADE
);

-- Indexes for bill text
CREATE INDEX IF NOT EXISTS idx_congress_bill_text_bill ON congress_bill_text(bill_id);
CREATE INDEX IF NOT EXISTS idx_congress_bill_text_type ON congress_bill_text(text_type);
CREATE INDEX IF NOT EXISTS idx_congress_bill_text_format ON congress_bill_text(text_format);
CREATE INDEX IF NOT EXISTS idx_congress_bill_text_date ON congress_bill_text(date_issued);
CREATE INDEX IF NOT EXISTS idx_congress_bill_text_processing_status ON congress_bill_text(processing_status);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_bill_text_full_search ON congress_bill_text USING GIN(to_tsvector('english', full_text));
CREATE INDEX IF NOT EXISTS idx_congress_bill_text_extracted_search ON congress_bill_text USING GIN(to_tsvector('english', extracted_text));