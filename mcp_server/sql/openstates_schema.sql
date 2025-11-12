-- OpenStates OpenCivicData (OCD) compliant schema for Postgres
-- Based on actual OpenStates database structure from pgdump analysis
-- Implements the OCD standard for legislative data

-- ===========================================
-- CORE ENTITIES
-- ===========================================

CREATE TABLE IF NOT EXISTS opencivicdata_division (
    id TEXT PRIMARY KEY, -- ocd-division format
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    subtype1 TEXT,
    subid1 TEXT,
    subtype2 TEXT,
    subid2 TEXT,
    subtype3 TEXT,
    subid3 TEXT,
    subtype4 TEXT,
    subid4 TEXT,
    subtype5 TEXT,
    subid5 TEXT,
    subtype6 TEXT,
    subid6 TEXT,
    subtype7 TEXT,
    subid7 TEXT,
    redirect_id TEXT,

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_jurisdiction (
    id TEXT PRIMARY KEY, -- ocd-jurisdiction format
    name TEXT NOT NULL,
    url TEXT,
    classification TEXT NOT NULL, -- state, municipality, country
    division_id TEXT REFERENCES opencivicdata_division(id),
    latest_bill_update TIMESTAMPTZ,
    latest_people_update TIMESTAMPTZ,

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_legislativesession (
    id UUID PRIMARY KEY,
    identifier TEXT NOT NULL,
    name TEXT NOT NULL,
    classification TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    jurisdiction_id TEXT NOT NULL REFERENCES opencivicdata_jurisdiction(id),
    active BOOLEAN DEFAULT FALSE,

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_organization (
    id TEXT PRIMARY KEY, -- ocd-organization format
    name TEXT NOT NULL,
    classification TEXT NOT NULL, -- legislature, executive, lower, upper, committee, etc.
    jurisdiction_id TEXT REFERENCES opencivicdata_jurisdiction(id),
    parent_id TEXT REFERENCES opencivicdata_organization(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',
    links JSONB NOT NULL DEFAULT '[]',
    sources JSONB NOT NULL DEFAULT '[]',
    other_names JSONB NOT NULL DEFAULT '[]',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_person (
    id TEXT PRIMARY KEY, -- ocd-person format
    name TEXT NOT NULL,
    family_name TEXT NOT NULL,
    given_name TEXT NOT NULL,
    image TEXT NOT NULL,
    gender TEXT NOT NULL,
    biography TEXT NOT NULL,
    birth_date DATE,
    death_date DATE,
    primary_party TEXT NOT NULL,
    current_jurisdiction_id TEXT REFERENCES opencivicdata_jurisdiction(id),
    "current_role" JSONB,

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

-- ===========================================
-- BILL DATA
-- ===========================================

CREATE TABLE IF NOT EXISTS opencivicdata_bill (
    id TEXT PRIMARY KEY, -- ocd-bill format
    identifier TEXT NOT NULL,
    title TEXT NOT NULL,
    classification TEXT[] NOT NULL,
    subject TEXT[] NOT NULL,
    from_organization_id TEXT REFERENCES opencivicdata_organization(id),
    legislative_session_id UUID NOT NULL REFERENCES opencivicdata_legislativesession(id),

    -- Dates
    first_action_date DATE,
    latest_action_date DATE,
    latest_action_description TEXT NOT NULL,
    latest_passage_date DATE,

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',
    citations JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billabstract (
    id UUID PRIMARY KEY,
    abstract TEXT NOT NULL,
    note TEXT NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billaction (
    id UUID PRIMARY KEY,
    description TEXT NOT NULL,
    date DATE NOT NULL,
    classification TEXT[] NOT NULL,
    "order" INTEGER NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),
    organization_id TEXT NOT NULL REFERENCES opencivicdata_organization(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT opencivicdata_billaction_order_check CHECK ("order" >= 0)
);

CREATE TABLE IF NOT EXISTS opencivicdata_billactionrelatedentity (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    action_id UUID NOT NULL REFERENCES opencivicdata_billaction(id),
    organization_id TEXT REFERENCES opencivicdata_organization(id),
    person_id TEXT REFERENCES opencivicdata_person(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billsponsorship (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    "primary" BOOLEAN NOT NULL,
    classification TEXT NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),
    organization_id TEXT REFERENCES opencivicdata_organization(id),
    person_id TEXT REFERENCES opencivicdata_person(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billdocument (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    date DATE NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',
    classification TEXT NOT NULL,

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billdocumentlink (
    id UUID PRIMARY KEY,
    media_type TEXT NOT NULL,
    url TEXT NOT NULL,
    document_id UUID NOT NULL REFERENCES opencivicdata_billdocument(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billversion (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    date DATE NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',
    classification TEXT NOT NULL,

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billversionlink (
    id UUID PRIMARY KEY,
    media_type TEXT NOT NULL,
    url TEXT NOT NULL,
    version_id UUID NOT NULL REFERENCES opencivicdata_billversion(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billtitle (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    note TEXT NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billidentifier (
    id UUID PRIMARY KEY,
    identifier TEXT NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_billsource (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    url TEXT NOT NULL,
    bill_id TEXT NOT NULL REFERENCES opencivicdata_bill(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

-- ===========================================
-- VOTING DATA
-- ===========================================

CREATE TABLE IF NOT EXISTS opencivicdata_voteevent (
    id TEXT PRIMARY KEY, -- ocd-vote format
    identifier TEXT NOT NULL,
    motion_text TEXT NOT NULL,
    motion_classification TEXT[] NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    result TEXT NOT NULL,
    bill_id TEXT REFERENCES opencivicdata_bill(id),
    organization_id TEXT NOT NULL REFERENCES opencivicdata_organization(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_personvote (
    id UUID PRIMARY KEY,
    option TEXT NOT NULL,
    voter_name TEXT NOT NULL,
    note TEXT NOT NULL,
    vote_event_id TEXT NOT NULL REFERENCES opencivicdata_voteevent(id),
    voter_id TEXT REFERENCES opencivicdata_person(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_voteeventcount (
    id UUID PRIMARY KEY,
    option TEXT NOT NULL,
    value INTEGER NOT NULL,
    vote_event_id TEXT NOT NULL REFERENCES opencivicdata_voteevent(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

-- ===========================================
-- MEMBERSHIPS & RELATIONSHIPS
-- ===========================================

CREATE TABLE IF NOT EXISTS opencivicdata_membership (
    id UUID PRIMARY KEY,
    label TEXT NOT NULL,
    role TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    person_id TEXT REFERENCES opencivicdata_person(id),
    organization_id TEXT REFERENCES opencivicdata_organization(id),
    post_id TEXT, -- References OCD post IDs
    on_behalf_of_id TEXT REFERENCES opencivicdata_organization(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_post (
    id TEXT PRIMARY KEY, -- ocd-post format
    label TEXT NOT NULL,
    role TEXT NOT NULL,
    division_id TEXT REFERENCES opencivicdata_division(id),
    organization_id TEXT REFERENCES opencivicdata_organization(id),
    start_date DATE,
    end_date DATE,
    maximum_memberships INTEGER DEFAULT 1,

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

-- ===========================================
-- PERSON & ORGANIZATION DETAILS
-- ===========================================

CREATE TABLE IF NOT EXISTS opencivicdata_personidentifier (
    id UUID PRIMARY KEY,
    identifier TEXT NOT NULL,
    scheme TEXT NOT NULL,
    person_id TEXT NOT NULL REFERENCES opencivicdata_person(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_personname (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    note TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    person_id TEXT NOT NULL REFERENCES opencivicdata_person(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_personlink (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    url TEXT NOT NULL,
    person_id TEXT NOT NULL REFERENCES opencivicdata_person(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_personsource (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    url TEXT NOT NULL,
    person_id TEXT NOT NULL REFERENCES opencivicdata_person(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_personcontactdetail (
    id UUID PRIMARY KEY,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    note TEXT NOT NULL,
    label TEXT NOT NULL,
    person_id TEXT NOT NULL REFERENCES opencivicdata_person(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_organizationidentifier (
    id UUID PRIMARY KEY,
    identifier TEXT NOT NULL,
    scheme TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES opencivicdata_organization(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_organizationname (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    note TEXT NOT NULL,
    start_date DATE,
    end_date DATE,
    organization_id TEXT NOT NULL REFERENCES opencivicdata_organization(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_organizationlink (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    url TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES opencivicdata_organization(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_organizationsource (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    url TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES opencivicdata_organization(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

-- ===========================================
-- EVENTS (Committee hearings, etc.)
-- ===========================================

CREATE TABLE IF NOT EXISTS opencivicdata_event (
    id TEXT PRIMARY KEY, -- ocd-event format
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    classification TEXT NOT NULL,
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    all_day BOOLEAN DEFAULT FALSE,
    timezone TEXT,
    status TEXT NOT NULL,
    upstream_id TEXT,
    deleted BOOLEAN DEFAULT FALSE,
    jurisdiction_id TEXT NOT NULL REFERENCES opencivicdata_jurisdiction(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_eventlocation (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT,
    event_id TEXT NOT NULL REFERENCES opencivicdata_event(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_eventparticipant (
    id UUID PRIMARY KEY,
    note TEXT NOT NULL,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    event_id TEXT NOT NULL REFERENCES opencivicdata_event(id),
    organization_id TEXT REFERENCES opencivicdata_organization(id),
    person_id TEXT REFERENCES opencivicdata_person(id),

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS opencivicdata_eventagendaitem (
    id UUID PRIMARY KEY,
    description TEXT NOT NULL,
    classification TEXT[] NOT NULL,
    "order" INTEGER NOT NULL,
    subjects TEXT[] NOT NULL,
    notes TEXT[] NOT NULL,
    event_id TEXT NOT NULL REFERENCES opencivicdata_event(id),

    -- OCD standard fields
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    extras JSONB NOT NULL DEFAULT '{}',

    -- Metadata
    created_on TIMESTAMPTZ DEFAULT now(),
    updated_on TIMESTAMPTZ DEFAULT now()
);

-- ===========================================
-- INDEXES
-- ===========================================

-- Core entity indexes
CREATE INDEX IF NOT EXISTS idx_ocd_jurisdiction_classification ON opencivicdata_jurisdiction(classification);
CREATE INDEX IF NOT EXISTS idx_ocd_organization_classification ON opencivicdata_organization(classification);
CREATE INDEX IF NOT EXISTS idx_ocd_organization_parent ON opencivicdata_organization(parent_id);
CREATE INDEX IF NOT EXISTS idx_ocd_person_party ON opencivicdata_person(primary_party);

-- Bill indexes
CREATE INDEX IF NOT EXISTS idx_ocd_bill_session ON opencivicdata_bill(legislative_session_id);
CREATE INDEX IF NOT EXISTS idx_ocd_bill_organization ON opencivicdata_bill(from_organization_id);
CREATE INDEX IF NOT EXISTS idx_ocd_bill_identifier ON opencivicdata_bill(identifier);
CREATE INDEX IF NOT EXISTS idx_ocd_bill_classification ON opencivicdata_bill USING GIN(classification);
CREATE INDEX IF NOT EXISTS idx_ocd_bill_subject ON opencivicdata_bill USING GIN(subject);
CREATE INDEX IF NOT EXISTS idx_ocd_bill_dates ON opencivicdata_bill(latest_action_date, first_action_date);

-- Bill relationship indexes
CREATE INDEX IF NOT EXISTS idx_ocd_billaction_bill ON opencivicdata_billaction(bill_id, "order");
CREATE INDEX IF NOT EXISTS idx_ocd_billaction_date ON opencivicdata_billaction(date);
CREATE INDEX IF NOT EXISTS idx_ocd_billsponsorship_bill ON opencivicdata_billsponsorship(bill_id);
CREATE INDEX IF NOT EXISTS idx_ocd_billdocument_bill ON opencivicdata_billdocument(bill_id);
CREATE INDEX IF NOT EXISTS idx_ocd_billversion_bill ON opencivicdata_billversion(bill_id);

-- Vote indexes
CREATE INDEX IF NOT EXISTS idx_ocd_voteevent_bill ON opencivicdata_voteevent(bill_id);
CREATE INDEX IF NOT EXISTS idx_ocd_voteevent_organization ON opencivicdata_voteevent(organization_id);
CREATE INDEX IF NOT EXISTS idx_ocd_voteevent_date ON opencivicdata_voteevent(start_date);
CREATE INDEX IF NOT EXISTS idx_ocd_personvote_vote ON opencivicdata_personvote(vote_event_id);

-- Membership indexes
CREATE INDEX IF NOT EXISTS idx_ocd_membership_person ON opencivicdata_membership(person_id);
CREATE INDEX IF NOT EXISTS idx_ocd_membership_organization ON opencivicdata_membership(organization_id);
CREATE INDEX IF NOT EXISTS idx_ocd_membership_dates ON opencivicdata_membership(start_date, end_date);

-- Event indexes
CREATE INDEX IF NOT EXISTS idx_ocd_event_jurisdiction ON opencivicdata_event(jurisdiction_id);
CREATE INDEX IF NOT EXISTS idx_ocd_event_dates ON opencivicdata_event(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_ocd_event_classification ON opencivicdata_event(classification);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_ocd_bill_title_search ON opencivicdata_bill USING GIN(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_ocd_billaction_description_search ON opencivicdata_billaction USING GIN(to_tsvector('english', description));
CREATE INDEX IF NOT EXISTS idx_ocd_person_name_search ON opencivicdata_person USING GIN(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_ocd_organization_name_search ON opencivicdata_organization USING GIN(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_ocd_event_name_search ON opencivicdata_event USING GIN(to_tsvector('english', name || ' ' || description));

-- JSONB indexes for extras and other JSON fields
CREATE INDEX IF NOT EXISTS idx_ocd_bill_extras ON opencivicdata_bill USING GIN(extras);
CREATE INDEX IF NOT EXISTS idx_ocd_person_extras ON opencivicdata_person USING GIN(extras);
CREATE INDEX IF NOT EXISTS idx_ocd_organization_extras ON opencivicdata_organization USING GIN(extras);
CREATE INDEX IF NOT EXISTS idx_ocd_event_extras ON opencivicdata_event USING GIN(extras);