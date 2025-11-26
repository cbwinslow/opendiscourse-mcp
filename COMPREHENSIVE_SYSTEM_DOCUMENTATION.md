# MCP Legislative Data Server - Comprehensive System Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Database Schema](#database-schema)
3. [Scripts and Tools](#scripts-and-tools)
4. [API Endpoints](#api-endpoints)
5. [Configuration](#configuration)
6. [Usage Examples](#usage-examples)
7. [Monitoring and Deduplication](#monitoring-and-deduplication)
8. [Troubleshooting](#troubleshooting)

## System Overview

The MCP Legislative Data Server is a comprehensive system for ingesting, processing, and serving legislative data from multiple sources including Congress.gov, OpenStates, and GovInfo. The system features advanced monitoring, deduplication, and distributed processing capabilities.

### Key Features

- **Multi-Source Data Ingestion**: Congress.gov, OpenStates, GovInfo
- **Real-Time Monitoring**: Job tracking with progress updates
- **Content-Based Deduplication**: SHA-256 hashing prevents duplicate data
- **Distributed Processing**: GPU acceleration and parallel processing
- **RESTful API**: Full programmatic access to all functionality
- **Comprehensive Testing**: Extensive test coverage with monitoring

---

## Database Schema

### Congress.gov Tables

#### `congress_bills`
Federal legislative bills from Congress.gov API.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `bill_id` | TEXT (PK) | Unique bill identifier | "118-HR-1" |
| `congress` | SMALLINT | Congress number | 118 |
| `bill_type` | TEXT | Bill type (hr, s, hres, sconres) | "hr" |
| `bill_number` | TEXT | Bill number | "1" |
| `title` | TEXT | Bill title | "For the People Act of 2023" |
| `introduced_date` | DATE | Date bill was introduced | "2023-01-09" |
| `origin_chamber` | TEXT | Chamber where bill originated | "HOUSE" |
| `current_chamber` | TEXT | Current chamber | "HOUSE" |
| `latest_action_date` | DATE | Date of latest action | "2023-01-10" |
| `latest_action_text` | TEXT | Description of latest action | "Referred to committee" |
| `subjects` | JSONB | Bill subjects/categories | ["Civil Rights", "Government Operations"] |
| `sponsors` | JSONB | Bill sponsors information | {"count": 5, "sponsors": [...]} |
| `cosponsors` | JSONB | Cosponsors information | {"count": 25, "url": "..."} |
| `committees` | JSONB | Committee assignments | {"count": 2, "url": "..."} |
| `actions` | JSONB | Bill actions | {"count": 15, "url": "..."} |
| `amendments` | JSONB | Related amendments | {"count": 0, "url": "..."} |
| `related_bills` | JSONB | Related legislation | {"count": 3, "url": "..."} |
| `text` | JSONB | Bill text information | {"count": 1, "url": "..."} |
| `titles` | JSONB | Alternative titles | {"count": 2, "titles": [...]} |
| `cbo_cost_estimates` | JSONB | CBO cost estimates | [] |
| `policy_area` | JSONB | Policy area classification | {"name": "Government Operations"} |
| `constitutional_authority_statement_text` | TEXT | Constitutional authority | "Article I, Section 8" |
| `created_on` | TIMESTAMPTZ | Record creation timestamp | "2023-01-09T10:00:00Z" |
| `updated_on` | TIMESTAMPTZ | Last update timestamp | "2023-01-10T15:30:00Z" |
| `last_api_update` | TIMESTAMPTZ | Last API data update | "2023-01-10T15:30:00Z" |
| `raw` | JSONB | Complete raw API response | {...} |

**Indexes:**
- `idx_congress_bills_congress` (congress)
- `idx_congress_bills_type` (bill_type)
- `idx_congress_bills_number` (bill_number)
- `idx_congress_bills_introduced_date` (introduced_date)
- `idx_congress_bills_origin_chamber` (origin_chamber)
- `idx_congress_bills_current_chamber` (current_chamber)
- `idx_congress_bills_policy_area` (policy_area GIN)
- `idx_congress_bills_sponsors` (sponsors GIN)
- `idx_congress_bills_cosponsors` (cosponsors GIN)
- `idx_congress_bills_committees` (committees GIN)
- Full text search on title and latest_action_text

#### `congress_members`
Members of Congress with biographical and political information.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `bioguide_id` | TEXT (PK) | Bioguide identifier | "P000197" |
| `direct_order_name` | TEXT | Full name (First Last) | "Nancy Pelosi" |
| `inverted_order_name` | TEXT | Full name (Last, First) | "Pelosi, Nancy" |
| `honorific_name` | TEXT | Honorific title | "Ms." |
| `first_name` | TEXT | First name | "Nancy" |
| `last_name` | TEXT | Last name | "Pelosi" |
| `birth_year` | INTEGER | Year of birth | 1940 |
| `party_name` | TEXT | Current party | "Democrat" |
| `party_history` | JSONB | Party changes over time | [{"party": "Democrat", "start": "1987"}] |
| `state` | TEXT | State represented | "CA" |
| `district` | TEXT | District number (null for senators) | "12" |
| `current_member` | BOOLEAN | Currently serving | true |
| `terms` | JSONB | Complete term history | [{"chamber": "HOUSE", "congress": 118}] |
| `previous_names` | JSONB | Name changes | [] |
| `depiction` | JSONB | Photo/image information | {"imageUrl": "...", "attribution": "..."} |
| `sponsored_legislation` | JSONB | Bills sponsored | {"count": 1250, "url": "..."} |
| `cosponsored_legislation` | JSONB | Bills cosponsored | {"count": 8500, "url": "..."} |
| `leadership_positions` | JSONB | Leadership roles | [{"title": "Speaker", "congress": 117}] |
| `committee_assignments` | JSONB | Committee memberships | [{"committee": "Rules", "role": "Chair"}] |
| `voting_record` | JSONB | Aggregated voting statistics | {"partyLine": 0.95, "bipartisan": 0.85} |
| `created_on` | TIMESTAMPTZ | Record creation timestamp | "2023-01-01T00:00:00Z" |
| `updated_on` | TIMESTAMPTZ | Last update timestamp | "2023-11-01T00:00:00Z" |
| `last_api_update` | TIMESTAMPTZ | Last API data update | "2023-11-01T00:00:00Z" |
| `raw` | JSONB | Complete raw API response | {...} |

**Indexes:**
- `idx_congress_members_state` (state)
- `idx_congress_members_party` (party_name)
- `idx_congress_members_district` (district)
- `idx_congress_members_current` (current_member)
- `idx_congress_members_name` (direct_order_name)
- GIN indexes on party_history, terms, committee_assignments
- Full text search on direct_order_name

#### `congress_committees`
Congressional committees and subcommittees.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `committee_code` | TEXT (PK) | Committee code | "HSAP" |
| `chamber` | TEXT | House or Senate | "house" |
| `committee_name` | TEXT | Full committee name | "Committee on Appropriations" |
| `congress` | SMALLINT | Congress number | 118 |
| `committee_type` | TEXT | Type of committee | "standing" |
| `jurisdiction` | TEXT | Committee jurisdiction | "Appropriations" |
| `parent_committee_code` | TEXT | Parent committee (for subcommittees) | "HSAP" |
| `chair` | JSONB | Chair information | {"bioguideId": "P000197", "name": "Nancy Pelosi"} |
| `ranking_member` | JSONB | Ranking member information | {"bioguideId": "R000395", "name": "Tom Cole"} |
| `subcommittee_count` | INTEGER | Number of subcommittees | 12 |
| `bills_reported` | JSONB | Bills reported | {"count": 45, "url": "..."} |
| `hearings_held` | JSONB | Hearings held | {"count": 120, "url": "..."} |
| `nominations_reported` | JSONB | Nominations reported | {"count": 25, "url": "..."} |
| `subcommittees` | JSONB | Subcommittee details | [{"code": "HSAP01", "name": "..."}] |
| `current_members` | JSONB | Current membership | [{"bioguideId": "...", "role": "Chair"}] |
| `establishment_date` | DATE | Committee establishment | "1865-07-31" |
| `abolition_date` | DATE | Committee abolition (if applicable) | null |
| `created_on` | TIMESTAMPTZ | Record creation timestamp | "2023-01-01T00:00:00Z" |
| `updated_on` | TIMESTAMPTZ | Last update timestamp | "2023-11-01T00:00:00Z" |
| `last_api_update` | TIMESTAMPTZ | Last API data update | "2023-11-01T00:00:00Z" |
| `raw` | JSONB | Complete raw API response | {...} |

**Indexes:**
- `idx_congress_committees_chamber` (chamber)
- `idx_congress_committees_congress` (congress)
- `idx_congress_committees_type` (committee_type)
- `idx_congress_committees_parent` (parent_committee_code)
- `idx_congress_committees_name` (committee_name)
- GIN index on current_members

#### `congress_votes`
Roll call votes in Congress.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `vote_id` | TEXT (PK) | Unique vote identifier | "h2023-05-16.001" |
| `congress` | SMALLINT | Congress number | 118 |
| `session` | SMALLINT | Session number | 1 |
| `chamber` | TEXT | House or Senate | "house" |
| `roll_number` | INTEGER | Roll call number | 234 |
| `vote_date` | DATE | Date of vote | "2023-05-16" |
| `vote_time` | TIME | Time of vote | "14:30:00" |
| `question` | TEXT | Question being voted on | "On Passage" |
| `description` | TEXT | Vote description | "H.R. 1234 - Infrastructure Bill" |
| `vote_type` | TEXT | Type of vote | "YEA-AND-NAY" |
| `result` | TEXT | Vote result | "Passed" |
| `total_yes` | INTEGER | Yes votes | 220 |
| `total_no` | INTEGER | No votes | 210 |
| `total_present` | INTEGER | Present votes | 0 |
| `total_not_voting` | INTEGER | Not voting | 5 |
| `tie_breaker` | JSONB | Tie breaker vote (Senate) | null |
| `document` | JSONB | Associated bill/resolution | {"billId": "118-HR-1234"} |
| `member_votes` | JSONB | Individual member votes | [{"member": "P000197", "vote": "Yea"}] |
| `amendments` | JSONB | Related amendments | [] |
| `created_on` | TIMESTAMPTZ | Record creation timestamp | "2023-05-16T14:30:00Z" |
| `updated_on` | TIMESTAMPTZ | Last update timestamp | "2023-05-16T14:30:00Z" |
| `last_api_update` | TIMESTAMPTZ | Last API data update | "2023-05-16T14:30:00Z" |
| `raw` | JSONB | Complete raw API response | {...} |

**Indexes:**
- `idx_congress_votes_congress` (congress)
- `idx_congress_votes_chamber` (chamber)
- `idx_congress_votes_date` (vote_date)
- `idx_congress_votes_result` (result)
- GIN indexes on document, member_votes

#### `congress_bill_actions`
Individual actions taken on bills.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `action_id` | TEXT (PK) | Composite action identifier | "118-HR-1-001" |
| `bill_id` | TEXT (FK) | Associated bill | "118-HR-1" |
| `action_date` | DATE | Date of action | "2023-01-10" |
| `sequence_number` | INTEGER | Action sequence | 1 |
| `action_code` | TEXT | Action code | "H11100" |
| `action_text` | TEXT | Action description | "Referred to the Committee on..." |
| `action_type` | TEXT | Type of action | "Committee" |
| `chamber` | TEXT | Chamber where action occurred | "HOUSE" |
| `committee` | JSONB | Committee information | {"code": "HSJU", "name": "Judiciary"} |
| `source_system_code` | TEXT | Source system | "house" |
| `source_system_name` | TEXT | Source system name | "House" |
| `created_on` | TIMESTAMPTZ | Record creation timestamp | "2023-01-10T12:00:00Z" |
| `updated_on` | TIMESTAMPTZ | Last update timestamp | "2023-01-10T12:00:00Z" |

**Indexes:**
- `idx_congress_bill_actions_bill` (bill_id)
- `idx_congress_bill_actions_date` (action_date)
- `idx_congress_bill_actions_type` (action_type)
- `idx_congress_bill_actions_chamber` (chamber)
- GIN index on committee
- Full text search on action_text

#### `congress_bill_text`
Bill text versions and formats.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `text_id` | TEXT (PK) | Unique text identifier | "118-HR-1-IH" |
| `bill_id` | TEXT (FK) | Associated bill | "118-HR-1" |
| `text_type` | TEXT | Type of text | "Introduced" |
| `text_format` | TEXT | Format (XML, HTML, PDF) | "XML" |
| `date_issued` | DATE | Date text was issued | "2023-01-09" |
| `congress` | SMALLINT | Congress number | 118 |
| `bill_type` | TEXT | Bill type | "HR" |
| `bill_number` | TEXT | Bill number | "1" |
| `bill_version` | TEXT | Bill version | "IH" |
| `full_text` | TEXT | Complete text content | "<bill>...</bill>" |
| `extracted_text` | TEXT | OCR/extracted text | "A BILL To..." |
| `file_path` | TEXT | Local file path | "/data/bills/118-HR-1.xml" |
| `file_size` | INTEGER | File size in bytes | 125000 |
| `mime_type` | TEXT | MIME type | "application/xml" |
| `processing_status` | TEXT | Processing status | "completed" |
| `processing_attempts` | INTEGER | Processing attempts | 1 |
| `last_processing_attempt` | TIMESTAMPTZ | Last processing time | "2023-01-09T10:00:00Z" |
| `created_on` | TIMESTAMPTZ | Record creation timestamp | "2023-01-09T10:00:00Z" |
| `updated_on` | TIMESTAMPTZ | Last update timestamp | "2023-01-09T10:00:00Z" |

**Indexes:**
- `idx_congress_bill_text_bill` (bill_id)
- `idx_congress_bill_text_type` (text_type)
- `idx_congress_bill_text_format` (text_format)
- `idx_congress_bill_text_date` (date_issued)
- `idx_congress_bill_text_processing_status` (processing_status)
- Full text search on full_text and extracted_text

### OpenStates Tables

#### `opencivicdata_jurisdiction`
Geographic jurisdictions (states, municipalities).

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | TEXT (PK) | OCD jurisdiction ID | "ocd-jurisdiction/country:us/state:ca" |
| `name` | TEXT | Jurisdiction name | "California" |
| `url` | TEXT | Official website | "https://www.ca.gov" |
| `classification` | TEXT | Type of jurisdiction | "state" |
| `division_id` | TEXT (FK) | Geographic division | "ocd-division/country:us/state:ca" |
| `latest_bill_update` | TIMESTAMPTZ | Last bill update | "2023-11-01T00:00:00Z" |
| `latest_people_update` | TIMESTAMPTZ | Last people update | "2023-11-01T00:00:00Z" |
| `created_at` | TIMESTAMPTZ | Record creation | "2023-01-01T00:00:00Z" |
| `updated_at` | TIMESTAMPTZ | Last update | "2023-11-01T00:00:00Z" |
| `extras` | JSONB | Additional data | {} |

#### `opencivicdata_legislativesession`
Legislative sessions within jurisdictions.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | UUID (PK) | Session identifier | "550e8400-e29b-41d4-a716-446655440000" |
| `identifier` | TEXT | Session identifier | "2023" |
| `name` | TEXT | Session name | "2023 Regular Session" |
| `classification` | TEXT | Session type | "primary" |
| `start_date` | DATE | Session start | "2023-01-01" |
| `end_date` | DATE | Session end | "2023-12-31" |
| `jurisdiction_id` | TEXT (FK) | Parent jurisdiction | "ocd-jurisdiction/country:us/state:ca" |
| `active` | BOOLEAN | Currently active | false |

#### `opencivicdata_person`
Legislators and government officials.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | TEXT (PK) | OCD person ID | "ocd-person/12345678-1234-1234-1234-123456789012" |
| `name` | TEXT | Full name | "Kevin McCarthy" |
| `family_name` | TEXT | Last name | "McCarthy" |
| `given_name` | TEXT | First name | "Kevin" |
| `image` | TEXT | Photo URL | "https://example.com/photo.jpg" |
| `gender` | TEXT | Gender | "male" |
| `biography` | TEXT | Biographical information | "Speaker of the House..." |
| `birth_date` | DATE | Date of birth | "1965-01-26" |
| `death_date` | DATE | Date of death | null |
| `primary_party` | TEXT | Party affiliation | "Republican" |
| `current_jurisdiction_id` | TEXT (FK) | Current jurisdiction | "ocd-jurisdiction/country:us/state:ca" |
| `current_role` | JSONB | Current role details | {"title": "Speaker", "org": "..."} |
| `created_at` | TIMESTAMPTZ | Record creation | "2023-01-01T00:00:00Z" |
| `updated_at` | TIMESTAMPTZ | Last update | "2023-11-01T00:00:00Z" |
| `extras` | JSONB | Additional data | {} |

#### `opencivicdata_bill`
Legislative bills from state legislatures.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | TEXT (PK) | OCD bill ID | "ocd-bill/12345678-1234-1234-1234-123456789012" |
| `identifier` | TEXT | Bill identifier | "AB 123" |
| `title` | TEXT | Bill title | "Budget Act of 2023" |
| `classification` | TEXT[] | Bill types | ["bill"] |
| `subject` | TEXT[] | Subject categories | ["Budget", "Finance"] |
| `from_organization_id` | TEXT (FK) | Originating organization | "ocd-organization/..." |
| `legislative_session_id` | UUID (FK) | Legislative session | "550e8400-e29b-41d4-a716-446655440000" |
| `first_action_date` | DATE | First action date | "2023-01-15" |
| `latest_action_date` | DATE | Latest action date | "2023-09-15" |
| `latest_action_description` | TEXT | Latest action | "Signed by Governor" |
| `latest_passage_date` | DATE | Passage date | "2023-09-10" |
| `created_at` | TIMESTAMPTZ | Record creation | "2023-01-15T00:00:00Z" |
| `updated_at` | TIMESTAMPTZ | Last update | "2023-09-15T00:00:00Z" |
| `extras` | JSONB | Additional data | {} |
| `citations` | JSONB | Legal citations | {} |

#### `opencivicdata_voteevent`
Roll call votes in state legislatures.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | TEXT (PK) | OCD vote ID | "ocd-vote/12345678-1234-1234-1234-123456789012" |
| `identifier` | TEXT | Vote identifier | "2023-05-16-001" |
| `motion_text` | TEXT | Motion being voted on | "Shall the bill pass?" |
| `motion_classification` | TEXT[] | Motion types | ["passage"] |
| `start_date` | TIMESTAMPTZ | Vote start time | "2023-05-16T14:30:00Z" |
| `result` | TEXT | Vote result | "pass" |
| `bill_id` | TEXT (FK) | Associated bill | "ocd-bill/..." |
| `organization_id` | TEXT (FK) | Organization voting | "ocd-organization/..." |
| `created_at` | TIMESTAMPTZ | Record creation | "2023-05-16T14:30:00Z" |
| `updated_at` | TIMESTAMPTZ | Last update | "2023-05-16T14:30:00Z" |
| `extras` | JSONB | Additional data | {} |

### GovInfo Tables

#### `govinfo_collections`
Document collections available from GovInfo.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `collection_code` | TEXT (PK) | Collection code | "BILLS" |
| `collection_name` | TEXT | Collection name | "Congressional Bills" |
| `package_count` | INTEGER | Number of packages | 15000 |
| `granule_count` | INTEGER | Number of granules | 45000 |
| `category` | TEXT | Content category | "legislative" |
| `branch` | TEXT | Government branch | "legislative" |
| `description` | TEXT | Collection description | "All congressional bills..." |
| `api_endpoint` | TEXT | API endpoint | "/collections/BILLS" |
| `bulk_download_available` | BOOLEAN | Bulk download available | true |
| `enabled` | BOOLEAN | Collection enabled | true |
| `priority` | INTEGER | Processing priority | 1 |
| `update_frequency` | TEXT | Update frequency | "daily" |
| `last_full_update` | TIMESTAMPTZ | Last full update | "2023-11-01T00:00:00Z" |
| `last_incremental_update` | TIMESTAMPTZ | Last incremental update | "2023-11-12T00:00:00Z" |
| `total_processed` | INTEGER | Total processed | 14500 |
| `total_failed` | INTEGER | Total failed | 25 |
| `raw` | JSONB | Raw API response | {...} |

#### `govinfo_packages`
Document packages (bills, reports, etc.).

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `package_id` | TEXT (PK) | Package identifier | "BILLS-118hr1" |
| `collection_code` | TEXT (FK) | Parent collection | "BILLS" |
| `last_modified` | TIMESTAMPTZ | Last modification | "2023-01-09T10:00:00Z" |
| `date_issued` | DATE | Issue date | "2023-01-09" |
| `title` | TEXT | Document title | "For the People Act of 2023" |
| `collection_name` | TEXT | Collection name | "Congressional Bills" |
| `category` | TEXT | Category | "legislative" |
| `branch` | TEXT | Branch | "legislative" |
| `document_type` | TEXT | Document type | "HR" |
| `pages` | INTEGER | Page count | 125 |
| `government_author1` | TEXT | Primary author | "House Committee on..." |
| `su_doc_class_number` | TEXT | SuDoc classification | "Y 1.6:" |
| `congress` | SMALLINT | Congress number | 118 |
| `session` | SMALLINT | Session number | 1 |
| `bill_type` | TEXT | Bill type | "hr" |
| `bill_number` | TEXT | Bill number | "1" |
| `bill_version` | TEXT | Bill version | "ih" |
| `origin_chamber` | TEXT | Originating chamber | "HOUSE" |
| `current_chamber` | TEXT | Current chamber | "HOUSE" |
| `is_appropriation` | BOOLEAN | Appropriation bill | false |
| `is_private` | BOOLEAN | Private bill | false |
| `publisher` | TEXT | Publishing agency | "U.S. Government Publishing Office" |
| `other_identifiers` | JSONB | Additional identifiers | {"issn": "1234-5678"} |
| `references` | JSONB | Legal references | {"USCODE": ["26 U.S.C. 1"]} |
| `details_link` | TEXT | Details URL | "https://www.govinfo.gov/..." |
| `granules_link` | TEXT | Granules URL | "https://www.govinfo.gov/..." |
| `package_link` | TEXT | Package URL | "https://www.govinfo.gov/..." |
| `has_txt` | BOOLEAN | Text format available | true |
| `has_pdf` | BOOLEAN | PDF format available | true |
| `has_xml` | BOOLEAN | XML format available | true |
| `has_mods` | BOOLEAN | MODS available | true |
| `has_premis` | BOOLEAN | PREMIS available | true |
| `has_zip` | BOOLEAN | ZIP available | true |
| `txt_link` | TEXT | Text download URL | "https://www.govinfo.gov/..." |
| `pdf_link` | TEXT | PDF download URL | "https://www.govinfo.gov/..." |
| `xml_link` | TEXT | XML download URL | "https://www.govinfo.gov/..." |
| `mods_link` | TEXT | MODS download URL | "https://www.govinfo.gov/..." |
| `premis_link` | TEXT | PREMIS download URL | "https://www.govinfo.gov/..." |
| `zip_link` | TEXT | ZIP download URL | "https://www.govinfo.gov/..." |
| `related` | JSONB | Related documents | {"billStatusLink": "..."} |
| `full_text` | TEXT | Extracted full text | "A BILL To..." |
| `extracted_text` | TEXT | OCR/extracted text | "A BILL To..." |
| `mods_metadata` | JSONB | MODS metadata | {...} |
| `premis_metadata` | JSONB | Preservation metadata | {...} |
| `processing_status` | TEXT | Processing status | "completed" |
| `processing_attempts` | INTEGER | Processing attempts | 1 |
| `last_processing_attempt` | TIMESTAMPTZ | Last processing | "2023-01-09T10:00:00Z" |
| `processing_errors` | JSONB | Processing errors | [] |
| `raw_summary` | JSONB | Raw summary API | {...} |
| `raw` | JSONB | Raw package API | {...} |

#### `govinfo_granules`
Document granules (sections, pages).

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `granule_id` | TEXT (PK) | Granule identifier | "BILLS-118hr1-1" |
| `package_id` | TEXT (FK) | Parent package | "BILLS-118hr1" |
| `title` | TEXT | Granule title | "Section 1" |
| `granule_class` | TEXT | Granule class | "BILL" |
| `date_issued` | DATE | Issue date | "2023-01-09" |
| `last_modified` | TIMESTAMPTZ | Last modification | "2023-01-09T10:00:00Z" |
| `heading` | TEXT | Section heading | "Short Title" |
| `sub_heading` | TEXT | Sub heading | null |
| `pages` | INTEGER | Page count | 1 |
| `parent_package_id` | TEXT | Parent package | "BILLS-118hr1" |
| `sequence_number` | INTEGER | Sequence number | 1 |
| `text_link` | TEXT | Text download URL | "https://www.govinfo.gov/..." |
| `pdf_link` | TEXT | PDF download URL | "https://www.govinfo.gov/..." |
| `xml_link` | TEXT | XML download URL | "https://www.govinfo.gov/..." |
| `mods_link` | TEXT | MODS download URL | "https://www.govinfo.gov/..." |
| `premis_link` | TEXT | PREMIS download URL | "https://www.govinfo.gov/..." |
| `has_text` | BOOLEAN | Text available | true |
| `has_pdf` | BOOLEAN | PDF available | true |
| `has_xml` | BOOLEAN | XML available | true |
| `has_mods` | BOOLEAN | MODS available | true |
| `has_premis` | BOOLEAN | PREMIS available | true |
| `full_text` | TEXT | Full text content | "This Act may be cited..." |
| `extracted_text` | TEXT | Extracted text | "This Act may be cited..." |
| `mods_metadata` | JSONB | MODS metadata | {...} |
| `premis_metadata` | JSONB | Preservation metadata | {...} |
| `processing_status` | TEXT | Processing status | "completed" |
| `processing_attempts` | INTEGER | Processing attempts | 1 |
| `last_processing_attempt` | TIMESTAMPTZ | Last processing | "2023-01-09T10:00:00Z" |
| `processing_errors` | JSONB | Processing errors | [] |
| `raw` | JSONB | Raw API response | {...} |

### Monitoring Tables

#### `ingestion_jobs`
Tracks data ingestion jobs and their progress.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `job_id` | TEXT (PK) | Unique job identifier | "congress_bills_118_hr_1731420000" |
| `source` | TEXT | Data source | "congress" |
| `collection` | TEXT | Collection type | "bills_118_hr" |
| `status` | TEXT | Job status | "completed" |
| `start_time` | TIMESTAMP | Job start time | "2023-11-12T16:30:00Z" |
| `end_time` | TIMESTAMP | Job end time | "2023-11-12T16:45:00Z" |
| `total_records` | INTEGER | Total records to process | 1000 |
| `processed_records` | INTEGER | Records processed | 1000 |
| `duplicates_found` | INTEGER | Duplicates detected | 25 |
| `errors` | JSONB | Error messages | [] |
| `metadata` | JSONB | Job metadata | {"api_key": "***", "congress": 118} |
| `created_at` | TIMESTAMP | Record creation | "2023-11-12T16:30:00Z" |
| `updated_at` | TIMESTAMP | Last update | "2023-11-12T16:45:00Z" |

#### `record_hashes`
Tracks content hashes for deduplication.

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `table_name` | TEXT | Target table name | "congress_bills" |
| `record_id` | TEXT | Record identifier | "118-HR-1" |
| `content_hash` | TEXT | SHA-256 content hash | "a665a45920422f9d417e4..." |
| `created_at` | TIMESTAMP | Hash creation time | "2023-11-12T16:30:00Z" |

---

## Scripts and Tools

### Ingestion Scripts

#### `congress_ingest.py`
Ingests federal legislative data from Congress.gov API.

**Usage:**
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
export CONGRESS_API_KEY=your_api_key

# Basic usage - ingest bills from Congress 118
python mcp_server/scripts/congress_ingest.py --congress 118

# Specific bill types
python mcp_server/scripts/congress_ingest.py --congress 118 --billType hr

# Start from specific page
python mcp_server/scripts/congress_ingest.py --congress 118 --page 5
```

**Parameters:**
- `--congress`: Congress number (required)
- `--billType`: Bill type filter (hr, s, hres, sconres, etc.)
- `--api_key`: Congress.gov API key (or set CONGRESS_API_KEY env var)
- `--page`: Starting page number (default: 1)

**Features:**
- Automatic job monitoring and progress tracking
- Content-based deduplication using SHA-256 hashing
- Handles API pagination automatically
- Comprehensive error logging and recovery

#### `openstates_ingest.py`
Ingests state legislative data from OpenStates API.

**Usage:**
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
export OPENSTATES_API_KEY=your_api_key

# Basic usage - ingest bills from California
python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction ca

# Search by keywords
python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction ca --q "education budget"

# Control pagination
python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction ca --page 1 --per_page 50
```

**Parameters:**
- `--jurisdiction`: State code (ca, tx, ny, etc.)
- `--q`: Search query string
- `--api_key`: OpenStates API key (or set OPENSTATES_API_KEY env var)
- `--page`: Page number (default: 1)
- `--per_page`: Results per page (default: 50, max: 50)

**Features:**
- Full OpenCivicData compliance
- Comprehensive bill metadata including sponsors, actions, votes
- Automatic deduplication and monitoring
- Handles complex legislative workflows

#### `govinfo_ingest.py`
Ingests government publications from GovInfo bulk data.

**Usage:**
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
export GOVINFO_API_KEY=your_api_key

# Basic usage - ingest congressional bills
python mcp_server/scripts/govinfo_ingest.py --collection BILLS

# Specific year
python mcp_server/scripts/govinfo_ingest.py --collection BILLS --year 2023

# Custom download directory
python mcp_server/scripts/govinfo_ingest.py --collection BILLS --download_dir /tmp/govinfo
```

**Parameters:**
- `--collection`: Collection code (BILLS, CREC, FR, etc.) (required)
- `--year`: Year filter (optional)
- `--download_dir`: Download directory (default: ./data)
- `--api_key`: GovInfo API key (or set GOVINFO_API_KEY env var)

**Features:**
- Bulk data processing with XML parsing
- Full text extraction and OCR processing
- Document relationship tracking
- Comprehensive metadata preservation

#### `enhanced_congress_ingest.py`
Advanced Congress ingestion with GPU acceleration and distributed processing.

**Usage:**
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
export CONGRESS_API_KEY=your_api_key

# Basic enhanced ingestion
python mcp_server/scripts/enhanced_congress_ingest.py --congress 118

# With GPU acceleration
python mcp_server/scripts/enhanced_congress_ingest.py --congress 118 --use-gpu

# Distributed processing
python mcp_server/scripts/enhanced_congress_ingest.py --congress 118 --use-parallel --use-async

# Full configuration
python mcp_server/scripts/enhanced_congress_ingest.py \
  --congress 118 \
  --use-gpu \
  --use-parallel \
  --use-async \
  --batch-size 1000 \
  --max-pages 100 \
  --enable-progress \
  --enable-compression
```

**Parameters:**
- `--congress`: Congress number (required)
- `--bill-type`: Bill type filter
- `--api-key`: Congress.gov API key
- `--max-pages`: Maximum pages to process (default: 100)
- `--use-gpu`: Enable GPU processing
- `--use-parallel`: Enable parallel processing
- `--use-async`: Enable async processing
- `--batch-size`: Processing batch size (default: 1000)
- `--redis-url`: Redis URL for progress tracking
- `--enable-progress`: Enable progress tracking
- `--enable-compression`: Enable data compression

**Features:**
- GPU-accelerated data processing
- Distributed parallel execution
- Async I/O for high throughput
- Advanced progress tracking
- Data compression and optimization

### CLI Tools

#### `ingestion_cli.py`
Command-line interface for advanced ingestion management.

**Usage:**
```bash
# Create and execute a job
python mcp_server/scripts/ingestion_cli.py create congress bills --congress 118

# Schedule recurring jobs
python mcp_server/scripts/ingestion_cli.py schedule congress bills daily_update \
  --cron "0 2 * * *" \
  --congress 118

# List scheduled jobs
python mcp_server/scripts/ingestion_cli.py list

# Check job status
python mcp_server/scripts/ingestion_cli.py status congress_bills_118_hr_1731420000

# Distributed ingestion
python mcp_server/scripts/ingestion_cli.py distributed congress \
  --hosts user1@host1:22 user2@host2:22 \
  --congress 118

# SSH key setup
python mcp_server/scripts/ingestion_cli.py ssh-setup --setup-host host1 --setup-user user1

# Sync codebase to remote hosts
python mcp_server/scripts/ingestion_cli.py sync --hosts user1@host1 user2@host2
```

**Commands:**
- `create`: Create and execute ingestion job
- `schedule`: Schedule recurring ingestion job
- `list`: List scheduled jobs
- `status`: Get job execution status
- `remove`: Remove scheduled job
- `distributed`: Run distributed ingestion
- `ssh-setup`: Setup SSH keys for passwordless access
- `sync`: Sync codebase to remote hosts

### Utility Scripts

#### `init_db.sh`
Database initialization script.

**Usage:**
```bash
# Initialize database with all schemas
./mcp_server/scripts/init_db.sh

# Initialize specific schema
./mcp_server/scripts/init_db.sh congress
./mcp_server/scripts/init_db.sh openstates
./mcp_server/scripts/init_db.sh govinfo
```

**Features:**
- Creates all required tables and indexes
- Sets up proper permissions
- Initializes monitoring tables
- Validates database connectivity

### Shell Scripts

#### `comprehensive_ingest.sh`
Complete ingestion workflow script.

**Usage:**
```bash
# Run full ingestion pipeline
./comprehensive_ingest.sh

# With custom configuration
export CONGRESS_API_KEY=your_key
export OPENSTATES_API_KEY=your_key
export GOVINFO_API_KEY=your_key
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

./comprehensive_ingest.sh --congress 118 --jurisdictions "ca,tx,ny" --collections "BILLS,CREC"
```

**Parameters:**
- `--congress`: Congress number
- `--jurisdictions`: Comma-separated state codes
- `--collections`: Comma-separated GovInfo collections
- `--parallel`: Run ingestion in parallel
- `--monitor`: Enable monitoring dashboard

#### `setup_ingestion_user.sh`
User and environment setup script.

**Usage:**
```bash
# Setup ingestion user and environment
./setup_ingestion_user.sh username

# With custom database
./setup_ingestion_user.sh username --database mydb --host db.example.com
```

#### `monitor_ingestion.sh`
Ingestion monitoring dashboard script.

**Usage:**
```bash
# Start monitoring dashboard
./monitor_ingestion.sh

# Monitor specific job
./monitor_ingestion.sh --job-id congress_bills_118_hr_1731420000

# Continuous monitoring
./monitor_ingestion.sh --watch --interval 30
```

---

## API Endpoints

### Authentication Endpoints

#### `POST /mcp/register_token`
Register API tokens for data sources.

**Request:**
```json
{
  "site": "congress",
  "user_id": "user123",
  "api_key": "your_api_key_here"
}
```

**Response:**
```json
{
  "status": "ok",
  "site": "congress",
  "user_id": "user123"
}
```

### Execution Endpoints

#### `POST /mcp/execute`
Execute API functions directly.

**Request:**
```json
{
  "user_id": "user123",
  "site": "congress",
  "function": "search_bills",
  "args": {
    "congress": 118,
    "billType": "hr"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "bills": [...],
    "pagination": {...}
  }
}
```

#### `POST /mcp/ingest_data`
Trigger data ingestion jobs.

**Request:**
```json
{
  "user_id": "user123",
  "site": "congress",
  "database_url": "postgresql://user:pass@localhost:5432/dbname",
  "query_params": {
    "congress": 118,
    "billType": "hr"
  },
  "ingestion_mode": "incremental"
}
```

**Response:**
```json
{
  "status": "success",
  "site": "congress",
  "ingestion_mode": "incremental",
  "message": "Data ingestion completed for congress",
  "output": "..."
}
```

### Data Access Endpoints

#### `POST /mcp/query_data`
Query database tables.

**Request:**
```json
{
  "user_id": "user123",
  "database_url": "postgresql://user:pass@localhost:5432/dbname",
  "table": "congress_bills",
  "where_clause": "congress = 118 AND bill_type = 'hr'",
  "limit": 100,
  "order_by": "introduced_date DESC"
}
```

**Response:**
```json
{
  "status": "success",
  "table": "congress_bills",
  "count": 50,
  "columns": ["bill_id", "title", "introduced_date", ...],
  "data": [...]
}
```

#### `POST /mcp/export_data`
Export data to files.

**Request:**
```json
{
  "user_id": "user123",
  "database_url": "postgresql://user:pass@localhost:5432/dbname",
  "table": "congress_bills",
  "format": "csv",
  "where_clause": "congress = 118",
  "output_path": "/tmp/congress_bills_118.csv"
}
```

**Response:**
```json
{
  "status": "success",
  "table": "congress_bills",
  "format": "csv",
  "file": "/tmp/congress_bills_118.csv",
  "records": 1250
}
```

### Information Endpoints

#### `GET /mcp/functions`
List available API functions.

**Response:**
```json
{
  "congress": [
    "search_bills", "get_bill", "get_bill_actions", "get_bill_text",
    "list_members", "get_member", "bulk_download_collection",
    "query_congress_bills", "analyze_bill_sponsors_congress",
    "get_congressional_trends", "search_congress_bills_advanced",
    "analyze_member_activity", "compare_congresses", "export_congress_data",
    "query_bills_by_party", "query_bills_by_member_name", "query_bills_by_year_range",
    "query_bills_by_topics", "query_member_voting_record", "query_committee_members",
    "search_bills_by_text_content"
  ],
  "openstates": [
    "search_bills", "get_bill", "search_people", "get_person",
    "search_events", "get_event", "get_openapi_schema",
    "query_bills", "export_bills", "analyze_bill_sponsors",
    "find_related_bills", "get_legislative_trends", "search_bills_advanced",
    "get_bill_statistics", "export_filtered_data", "compare_legislatures",
    "generate_bill_report", "query_bills_by_party", "query_bills_by_person_name",
    "query_bills_by_year_range", "query_bills_by_topics", "query_person_voting_record",
    "query_committees", "search_bills_by_text_content"
  ],
  "govinfo": [
    "list_collections", "bulk_download", "fetch_bulk_file", "ingest_xml_to_df",
    "query_govinfo_documents", "analyze_document_collections",
    "get_document_trends", "search_documents_advanced",
    "analyze_document_metadata", "compare_collections", "export_govinfo_data",
    "query_documents_by_year_range", "query_documents_by_topics",
    "query_documents_by_type", "search_documents_by_text_content",
    "query_recent_documents", "analyze_document_types", "query_documents_by_metadata_field"
  ]
}
```

#### `GET /mcp/data_model`
Get database schema information.

**Response:**
```json
{
  "congress_bills": {
    "bill_id": "text (primary key)",
    "congress": "smallint",
    "bill_type": "text",
    "bill_number": "text",
    "title": "text",
    "introduced_date": "date",
    "origin_chamber": "text",
    "current_chamber": "text",
    "latest_action_date": "date",
    "latest_action_text": "text",
    "subjects": "jsonb",
    "sponsors": "jsonb",
    "cosponsors": "jsonb",
    "committees": "jsonb",
    "actions": "jsonb",
    "amendments": "jsonb",
    "related_bills": "jsonb",
    "text": "jsonb",
    "titles": "jsonb",
    "cbo_cost_estimates": "jsonb",
    "policy_area": "jsonb",
    "constitutional_authority_statement_text": "text",
    "created_on": "timestamptz",
    "updated_on": "timestamptz",
    "last_api_update": "timestamptz",
    "raw": "jsonb"
  },
  // ... other tables
}
```

### Monitoring Endpoints

#### `GET /mcp/ingestion/jobs`
List ingestion jobs.

**Parameters:**
- `status` (optional): Filter by status (pending, running, completed, failed)

**Response:**
```json
[
  {
    "job_id": "congress_bills_118_hr_1731420000",
    "source": "congress",
    "collection": "bills_118_hr",
    "status": "completed",
    "start_time": "2023-11-12T16:30:00.000Z",
    "end_time": "2023-11-12T16:45:00.000Z",
    "total_records": 1000,
    "processed_records": 1000,
    "duplicates_found": 25,
    "errors": [],
    "metadata": {
      "api_key": "abc12345...",
      "congress": 118,
      "bill_type": "hr"
    }
  }
]
```

#### `GET /mcp/ingestion/jobs/{job_id}`
Get specific job details.

**Response:**
```json
{
  "job_id": "congress_bills_118_hr_1731420000",
  "source": "congress",
  "collection": "bills_118_hr",
  "status": "completed",
  "start_time": "2023-11-12T16:30:00.000Z",
  "end_time": "2023-11-12T16:45:00.000Z",
  "total_records": 1000,
  "processed_records": 1000,
  "duplicates_found": 25,
  "errors": [],
  "metadata": {
    "api_key": "abc12345...",
    "congress": 118,
    "bill_type": "hr"
  }
}
```

#### `POST /mcp/ingestion/start`
Start a new ingestion job.

**Request:**
```json
{
  "source": "congress",
  "collection": "bills",
  "metadata": {
    "congress": 118,
    "bill_type": "hr"
  }
}
```

**Response:**
```json
{
  "job_id": "congress_bills_118_hr_1731420000",
  "status": "created"
}
```

#### `DELETE /mcp/ingestion/cleanup`
Clean up old ingestion data.

**Parameters:**
- `days` (optional): Days to keep (default: 30)

**Response:**
```json
{
  "status": "success",
  "message": "Cleaned up data older than 30 days"
}
```

#### `GET /mcp/health`
System health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-11-12T16:30:00.000Z",
  "version": "1.0.0"
}
```

---

## Configuration

### Environment Variables

#### Required
- `DATABASE_URL`: PostgreSQL connection string
  - Format: `postgresql://user:password@host:port/database`

#### API Keys
- `CONGRESS_API_KEY`: Congress.gov API key
- `OPENSTATES_API_KEY`: OpenStates API key
- `GOVINFO_API_KEY`: GovInfo API key

#### Optional Processing
- `USE_COPY`: Enable PostgreSQL COPY for bulk inserts (`true`/`false`)
- `USE_SQLALCHEMY`: Use SQLAlchemy instead of psycopg2 (`true`/`false`)
- `REDIS_URL`: Redis URL for distributed processing

### Database Configuration

#### Connection Pooling
```sql
-- Set connection limits
ALTER SYSTEM SET max_connections = 200;
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
```

#### Performance Tuning
```sql
-- Increase work memory for complex queries
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';

-- Enable parallel processing
ALTER SYSTEM SET max_parallel_workers_per_gather = 4;
ALTER SYSTEM SET max_parallel_workers = 8;
```

### Monitoring Configuration

#### Automatic Setup
The monitoring system automatically:
- Creates required database tables on first use
- Sets up proper indexes for performance
- Handles connection errors gracefully
- Continues operation even if monitoring fails

#### Cleanup Configuration
- Default retention: 30 days for ingestion jobs
- Hash cleanup: Automatic removal of old deduplication data
- Log rotation: Configurable log retention periods

---

## Usage Examples

### Basic Data Ingestion

#### 1. Congress Bills
```bash
# Set environment
export DATABASE_URL="postgresql://user:pass@localhost:5432/legislation"
export CONGRESS_API_KEY="your_congress_api_key"

# Ingest bills from Congress 118
python mcp_server/scripts/congress_ingest.py --congress 118 --billType hr
```

#### 2. State Legislation
```bash
export OPENSTATES_API_KEY="your_openstates_api_key"

# Ingest California bills
python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction ca --q "education"
```

#### 3. Government Publications
```bash
export GOVINFO_API_KEY="your_govinfo_api_key"

# Ingest congressional bills
python mcp_server/scripts/govinfo_ingest.py --collection BILLS --year 2023
```

### Advanced Usage

#### Parallel Processing
```bash
# Enhanced Congress ingestion with GPU acceleration
python mcp_server/scripts/enhanced_congress_ingest.py \
  --congress 118 \
  --use-gpu \
  --use-parallel \
  --batch-size 1000 \
  --max-pages 50
```

#### Distributed Ingestion
```bash
# CLI-based distributed processing
python mcp_server/scripts/ingestion_cli.py distributed congress \
  --hosts user1@host1:22 user2@host2:22 \
  --congress 118
```

#### Scheduled Jobs
```bash
# Schedule daily Congress updates
python mcp_server/scripts/ingestion_cli.py schedule congress bills daily_update \
  --cron "0 2 * * *" \
  --congress 118
```

### API Usage

#### Register API Keys
```bash
curl -X POST http://localhost:8000/mcp/register_token \
  -H "Content-Type: application/json" \
  -d '{
    "site": "congress",
    "user_id": "user123",
    "api_key": "your_api_key"
  }'
```

#### Execute API Functions
```bash
curl -X POST http://localhost:8000/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "site": "congress",
    "function": "search_bills",
    "args": {
      "congress": 118,
      "billType": "hr"
    }
  }'
```

#### Query Data
```bash
curl -X POST http://localhost:8000/mcp/query_data \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "database_url": "postgresql://user:pass@localhost:5432/legislation",
    "table": "congress_bills",
    "where_clause": "congress = 118 AND bill_type = '\''hr'\''",
    "limit": 10,
    "order_by": "introduced_date DESC"
  }'
```

#### Monitor Ingestion
```bash
# Check running jobs
curl http://localhost:8000/mcp/ingestion/jobs?status=running

# Get specific job status
curl http://localhost:8000/mcp/ingestion/jobs/congress_bills_118_hr_1731420000
```

### Data Analysis Examples

#### Find Recent Bills by Topic
```sql
SELECT bill_id, title, introduced_date, subjects
FROM congress_bills
WHERE congress = 118
  AND subjects ? 'Civil Rights'
  AND introduced_date >= '2023-01-01'
ORDER BY introduced_date DESC
LIMIT 20;
```

#### Analyze Legislative Activity
```sql
SELECT
  EXTRACT(MONTH FROM introduced_date) as month,
  COUNT(*) as bills_introduced,
  COUNT(DISTINCT sponsor_data->>'bioguideId') as active_sponsors
FROM congress_bills b,
     jsonb_array_elements(b.sponsors->'sponsors') as sponsor_data
WHERE congress = 118
  AND introduced_date >= '2023-01-01'
GROUP BY EXTRACT(MONTH FROM introduced_date)
ORDER BY month;
```

#### Track Committee Activity
```sql
SELECT
  c.committee_name,
  COUNT(b.*) as bills_reported,
  AVG(EXTRACT(DAY FROM (b.latest_action_date - b.introduced_date))) as avg_days_to_action
FROM congress_committees c
LEFT JOIN congress_bills b ON b.committees ? c.committee_code
WHERE c.congress = 118
GROUP BY c.committee_code, c.committee_name
ORDER BY bills_reported DESC;
```

---

## Monitoring and Deduplication

### Job Monitoring

#### Real-Time Progress Tracking
```python
from mcp_server.utils.monitoring import monitor

# Create and monitor a job
job_id = monitor.create_job('congress', 'bills_118_hr')

with monitor.monitor_job(job_id):
    # Your ingestion logic
    for batch in process_batches():
        monitor.update_progress(job_id, processed_count, duplicates_count)
```

#### Job Status Queries
```python
# Get all running jobs
running_jobs = monitor.get_all_jobs(status='running')

# Get specific job details
job_details = monitor.get_job_status('congress_bills_118_hr_1731420000')
```

### Content-Based Deduplication

#### Automatic Deduplication
```python
from mcp_server.utils.monitoring import deduplicator

# Check for duplicates before insertion
content_hash = deduplicator.get_content_hash(record_data, exclude_fields=['raw'])
if deduplicator.is_duplicate('congress_bills', content_hash, record_id):
    # Skip duplicate
    continue

# Insert record
insert_record(record_data)
```

#### Hash Management
```python
# Cleanup old hashes (removes hashes older than 30 days)
deduplicator.cleanup_old_hashes(days=30)

# Check if specific record exists
exists = deduplicator.is_duplicate('table_name', content_hash, record_id)
```

### Monitoring Dashboard

#### Web Interface
```bash
# Start the FastAPI server
uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000

# Access monitoring endpoints
# http://localhost:8000/mcp/ingestion/jobs
# http://localhost:8000/docs (Swagger UI)
```

#### CLI Monitoring
```bash
# List all jobs
python mcp_server/scripts/ingestion_cli.py list

# Get job status
python mcp_server/scripts/ingestion_cli.py status congress_bills_118_hr_1731420000

# Monitor with shell script
./monitor_ingestion.sh --watch --interval 30
```

---

## Troubleshooting

### Common Issues

#### Database Connection Issues
**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**
```bash
# Check database status
pg_isready -h localhost -p 5432

# Verify connection string
psql "postgresql://user:pass@localhost:5432/dbname" -c "SELECT 1;"

# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql-*.log
```

#### API Rate Limiting
**Problem:** `HTTP 429 Too Many Requests`

**Solutions:**
- Implement exponential backoff
- Reduce concurrent requests
- Check API documentation for rate limits
- Use API keys if available

#### Memory Issues
**Problem:** `MemoryError` during large data processing

**Solutions:**
```bash
# Increase system memory limits
ulimit -v unlimited

# Process data in smaller batches
--batch-size 500

# Enable data compression
--enable-compression
```

#### Duplicate Data Issues
**Problem:** Same records ingested multiple times

**Solutions:**
- Verify deduplication is enabled
- Check hash generation logic
- Clean up old hashes: `DELETE FROM record_hashes WHERE created_at < NOW() - INTERVAL '30 days';`

### Performance Optimization

#### Database Tuning
```sql
-- Analyze tables for query optimization
ANALYZE congress_bills;
ANALYZE opencivicdata_bill;

-- Reindex if needed
REINDEX TABLE congress_bills;
REINDEX INDEX idx_congress_bills_title_search;
```

#### Query Optimization
```sql
-- Use indexes effectively
SELECT * FROM congress_bills
WHERE congress = 118 AND bill_type = 'hr'
ORDER BY introduced_date DESC;

-- Avoid full table scans
EXPLAIN ANALYZE SELECT COUNT(*) FROM congress_bills WHERE subjects ? 'Budget';
```

#### Monitoring Performance
```bash
# Check slow queries
SELECT query, total_time, calls, mean_time
FROM pg_stat_statements
ORDER BY total_time DESC
LIMIT 10;

# Monitor connection usage
SELECT count(*) as connections FROM pg_stat_activity;
```

### Error Recovery

#### Failed Ingestion Jobs
```bash
# Check job status
curl http://localhost:8000/mcp/ingestion/jobs?status=failed

# Get detailed error information
curl http://localhost:8000/mcp/ingestion/jobs/{job_id}

# Retry failed jobs
python mcp_server/scripts/ingestion_cli.py create congress bills --congress 118
```

#### Data Consistency Issues
```sql
-- Find orphaned records
SELECT b.* FROM congress_bill_actions b
LEFT JOIN congress_bills cb ON b.bill_id = cb.bill_id
WHERE cb.bill_id IS NULL;

-- Clean up orphaned data
DELETE FROM congress_bill_actions
WHERE bill_id NOT IN (SELECT bill_id FROM congress_bills);
```

### Logging and Debugging

#### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with verbose output
python mcp_server/scripts/congress_ingest.py --congress 118 -v
```

#### Log Analysis
```bash
# Search for errors in logs
grep "ERROR" /var/log/mcp_ingestion.log

# Monitor ingestion progress
tail -f /var/log/mcp_ingestion.log | grep "Ingested"
```

#### Health Checks
```bash
# API health check
curl http://localhost:8000/mcp/health

# Database connectivity
psql -c "SELECT version();"

# Disk space
df -h /var/lib/postgresql
```

### Support and Resources

#### Documentation
- [Congress.gov API Documentation](https://api.congress.gov/)
- [OpenStates API Documentation](https://openstates.org/api/)
- [GovInfo API Documentation](https://www.govinfo.gov/developers)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

#### Community Resources
- GitHub Issues: Report bugs and request features
- Stack Overflow: Technical questions
- PostgreSQL Mailing Lists: Database-specific issues

---

*This comprehensive documentation covers the complete MCP Legislative Data Server system. For additional support or questions, please refer to the GitHub repository or create an issue.*
