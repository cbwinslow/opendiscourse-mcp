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

CREATE TABLE IF NOT EXISTS congress_summaries (
  -- Primary identifiers
  summary_id TEXT PRIMARY KEY,
  bill_id TEXT,

  -- Summary metadata
  congress SMALLINT,
  bill_type TEXT,
  bill_number TEXT,
  bill_version TEXT,

  -- Summary content
  action_desc TEXT,
  action_date DATE,
  text TEXT,
  as_of_date DATE,
  update_date DATE,

  -- Categories and topics
  categories JSONB, -- Array of category objects
  topics JSONB, -- Array of topic objects

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL,

  -- Foreign key (optional, as summaries may exist for bills not yet ingested)
  FOREIGN KEY (bill_id) REFERENCES congress_bills(bill_id) ON DELETE SET NULL
);

-- Indexes for summaries
CREATE INDEX IF NOT EXISTS idx_congress_summaries_bill ON congress_summaries(bill_id);
CREATE INDEX IF NOT EXISTS idx_congress_summaries_congress ON congress_summaries(congress);
CREATE INDEX IF NOT EXISTS idx_congress_summaries_type ON congress_summaries(bill_type);
CREATE INDEX IF NOT EXISTS idx_congress_summaries_date ON congress_summaries(action_date);
CREATE INDEX IF NOT EXISTS idx_congress_summaries_categories ON congress_summaries USING GIN(categories);
CREATE INDEX IF NOT EXISTS idx_congress_summaries_topics ON congress_summaries USING GIN(topics);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_summaries_text_search ON congress_summaries USING GIN(to_tsvector('english', text));
CREATE INDEX IF NOT EXISTS idx_congress_summaries_action_search ON congress_summaries USING GIN(to_tsvector('english', action_desc));

CREATE TABLE IF NOT EXISTS congress_treaties (
  -- Primary identifiers
  treaty_id TEXT PRIMARY KEY,
  congress SMALLINT NOT NULL,
  treaty_number TEXT NOT NULL,

  -- Treaty information
  title TEXT,
  suffix TEXT,
  receiving_chamber TEXT, -- HOUSE, SENATE
  receiving_chamber_calendar TEXT,

  -- Status and dates
  transmission_date DATE,
  referral_date DATE,
  referral_chamber TEXT,
  committee_referral JSONB,

  -- Resolution information
  resolution_text TEXT,
  resolution_date DATE,

  -- Actions and history
  actions JSONB, -- Array of action objects
  committee_reports JSONB, -- Array of committee report objects

  -- Current status
  current_status TEXT,
  current_status_date DATE,
  current_status_description TEXT,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for treaties
CREATE INDEX IF NOT EXISTS idx_congress_treaties_congress ON congress_treaties(congress);
CREATE INDEX IF NOT EXISTS idx_congress_treaties_number ON congress_treaties(treaty_number);
CREATE INDEX IF NOT EXISTS idx_congress_treaties_receiving_chamber ON congress_treaties(receiving_chamber);
CREATE INDEX IF NOT EXISTS idx_congress_treaties_transmission_date ON congress_treaties(transmission_date);
CREATE INDEX IF NOT EXISTS idx_congress_treaties_current_status ON congress_treaties(current_status);
CREATE INDEX IF NOT EXISTS idx_congress_treaties_actions ON congress_treaties USING GIN(actions);
CREATE INDEX IF NOT EXISTS idx_congress_treaties_committee_reports ON congress_treaties USING GIN(committee_reports);

CREATE TABLE IF NOT EXISTS congress_nominations (
  -- Primary identifiers
  nomination_id TEXT PRIMARY KEY,
  congress SMALLINT NOT NULL,
  nomination_number TEXT NOT NULL,

  -- Nomination details
  received_date DATE,
  nominee_name TEXT,
  nominee_state TEXT,
  nominee_party TEXT,
  position_title TEXT,
  organization TEXT,

  -- Committee information
  committee_name TEXT,
  committee_code TEXT,

  -- Status and actions
  current_status TEXT,
  current_status_date DATE,
  current_status_description TEXT,

  -- Vote information
  confirmation_vote JSONB,
  cloture_vote JSONB,

  -- Additional details
  description TEXT,
  part_of_nominees JSONB, -- For grouped nominations

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for nominations
CREATE INDEX IF NOT EXISTS idx_congress_nominations_congress ON congress_nominations(congress);
CREATE INDEX IF NOT EXISTS idx_congress_nominations_number ON congress_nominations(nomination_number);
CREATE INDEX IF NOT EXISTS idx_congress_nominations_received_date ON congress_nominations(received_date);
CREATE INDEX IF NOT EXISTS idx_congress_nominations_nominee_name ON congress_nominations(nominee_name);
CREATE INDEX IF NOT EXISTS idx_congress_nominations_committee ON congress_nominations(committee_code);
CREATE INDEX IF NOT EXISTS idx_congress_nominations_current_status ON congress_nominations(current_status);
CREATE INDEX IF NOT EXISTS idx_congress_nominations_confirmation_vote ON congress_nominations USING GIN(confirmation_vote);
CREATE INDEX IF NOT EXISTS idx_congress_nominations_cloture_vote ON congress_nominations USING GIN(cloture_vote);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_nominations_description_search ON congress_nominations USING GIN(to_tsvector('english', description));

CREATE TABLE IF NOT EXISTS congress_hearings (
  -- Primary identifiers
  hearing_id TEXT PRIMARY KEY,
  congress SMALLINT NOT NULL,
  chamber TEXT NOT NULL, -- house, senate, joint

  -- Hearing details
  committee_code TEXT,
  committee_name TEXT,
  subcommittee_name TEXT,

  -- Hearing information
  hearing_title TEXT,
  hearing_date DATE,
  hearing_type TEXT, -- legislative, oversight, investigative, etc.

  -- Location and format
  location TEXT,
  room TEXT,
  video_url TEXT,
  transcript_url TEXT,

  -- Witnesses and topics
  witnesses JSONB, -- Array of witness objects
  topics JSONB, -- Array of topic objects
  related_bills JSONB, -- Array of related bill objects

  -- Documents
  documents JSONB, -- Array of document objects

  -- Status
  status TEXT, -- scheduled, postponed, held, etc.

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for hearings
CREATE INDEX IF NOT EXISTS idx_congress_hearings_congress ON congress_hearings(congress);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_chamber ON congress_hearings(chamber);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_committee ON congress_hearings(committee_code);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_date ON congress_hearings(hearing_date);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_type ON congress_hearings(hearing_type);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_status ON congress_hearings(status);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_witnesses ON congress_hearings USING GIN(witnesses);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_topics ON congress_hearings USING GIN(topics);
CREATE INDEX IF NOT EXISTS idx_congress_hearings_related_bills ON congress_hearings USING GIN(related_bills);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_congress_hearings_title_search ON congress_hearings USING GIN(to_tsvector('english', hearing_title));

CREATE TABLE IF NOT EXISTS congress_congress (
  -- Primary identifiers
  congress_id SMALLINT PRIMARY KEY,
  congress_number SMALLINT NOT NULL,

  -- Congress dates
  start_date DATE,
  end_date DATE,

  -- Session information
  sessions JSONB, -- Array of session objects with start/end dates

  -- Chamber leadership
  house_leadership JSONB,
  senate_leadership JSONB,

  -- Committee chairs
  committee_chairs JSONB,

  -- Key statistics
  bills_introduced INTEGER DEFAULT 0,
  bills_enacted INTEGER DEFAULT 0,
  nominations_received INTEGER DEFAULT 0,
  nominations_confirmed INTEGER DEFAULT 0,

  -- Major legislation
  major_legislation JSONB, -- Array of significant bills passed

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Raw API response
  raw JSONB NOT NULL
);

-- Indexes for congress
CREATE INDEX IF NOT EXISTS idx_congress_congress_start_date ON congress_congress(start_date);
CREATE INDEX IF NOT EXISTS idx_congress_congress_end_date ON congress_congress(end_date);
CREATE INDEX IF NOT EXISTS idx_congress_congress_sessions ON congress_congress USING GIN(sessions);
CREATE INDEX IF NOT EXISTS idx_congress_congress_house_leadership ON congress_congress USING GIN(house_leadership);
CREATE INDEX IF NOT EXISTS idx_congress_congress_senate_leadership ON congress_congress USING GIN(senate_leadership);
CREATE INDEX IF NOT EXISTS idx_congress_congress_committee_chairs ON congress_congress USING GIN(committee_chairs);
CREATE INDEX IF NOT EXISTS idx_congress_congress_major_legislation ON congress_congress USING GIN(major_legislation);