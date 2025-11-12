-- GovInfo comprehensive schema for Postgres
-- Complete government publications and official documents
-- Based on actual GovInfo API response structures from https://github.com/usgpo/api

CREATE TABLE IF NOT EXISTS govinfo_collections (
  -- Primary identifiers
  collection_code TEXT PRIMARY KEY,
  collection_name TEXT NOT NULL,

  -- Collection statistics
  package_count INTEGER DEFAULT 0,
  granule_count INTEGER,

  -- Collection metadata
  category TEXT,
  branch TEXT, -- legislative, executive, judicial
  description TEXT,

  -- API information
  api_endpoint TEXT,
  bulk_download_available BOOLEAN DEFAULT FALSE,

  -- Processing configuration
  enabled BOOLEAN DEFAULT TRUE,
  priority INTEGER DEFAULT 1, -- Processing priority (1=high, 5=low)
  update_frequency TEXT DEFAULT 'daily', -- daily, weekly, monthly

  -- Statistics
  last_full_update TIMESTAMPTZ,
  last_incremental_update TIMESTAMPTZ,
  total_processed INTEGER DEFAULT 0,
  total_failed INTEGER DEFAULT 0,

  -- Raw API response
  raw JSONB,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now()
);

-- Indexes for collections
CREATE INDEX IF NOT EXISTS idx_govinfo_collections_category ON govinfo_collections(category);
CREATE INDEX IF NOT EXISTS idx_govinfo_collections_branch ON govinfo_collections(branch);
CREATE INDEX IF NOT EXISTS idx_govinfo_collections_enabled ON govinfo_collections(enabled);
CREATE INDEX IF NOT EXISTS idx_govinfo_collections_priority ON govinfo_collections(priority);

CREATE TABLE IF NOT EXISTS govinfo_packages (
  -- Primary identifiers (from collections API)
  package_id TEXT PRIMARY KEY,
  collection_code TEXT NOT NULL,

  -- Timestamps (from API)
  last_modified TIMESTAMPTZ NOT NULL,
  date_issued DATE,

  -- Basic metadata (from summary API)
  title TEXT,
  collection_name TEXT,
  category TEXT,
  branch TEXT, -- legislative, executive, judicial

  -- Content information
  document_type TEXT, -- FR, CREC, BILLS, etc.
  pages INTEGER,
  government_author1 TEXT,
  su_doc_class_number TEXT,

  -- Collection-specific metadata (varies by collection)
  congress SMALLINT,
  session SMALLINT,
  bill_type TEXT, -- hr, s, hres, sconres, etc.
  bill_number TEXT,
  bill_version TEXT, -- ih, rh, enr, etc.
  origin_chamber TEXT, -- HOUSE, SENATE
  current_chamber TEXT, -- HOUSE, SENATE, JOINT
  is_appropriation BOOLEAN,
  is_private BOOLEAN,

  -- Publisher and identifiers
  publisher TEXT,
  other_identifiers JSONB, -- migrated-doc-id, ils-system-id, stock-number, issn, etc.

  -- Links and availability (from API)
  details_link TEXT,
  granules_link TEXT,
  package_link TEXT,

  -- Download availability flags
  has_txt BOOLEAN DEFAULT FALSE,
  has_pdf BOOLEAN DEFAULT FALSE,
  has_xml BOOLEAN DEFAULT FALSE,
  has_mods BOOLEAN DEFAULT FALSE,
  has_premis BOOLEAN DEFAULT FALSE,
  has_zip BOOLEAN DEFAULT FALSE,

  -- Download URLs (from API)
  txt_link TEXT,
  pdf_link TEXT,
  xml_link TEXT,
  mods_link TEXT,
  premis_link TEXT,
  zip_link TEXT,

  -- Related documents (from API)
  related JSONB, -- Contains billStatusLink and other related links

  -- Citations and references (from API)
  "references" JSONB, -- Contains USCODE, STATUTE, PLAW references

  -- Full text content (when extracted)
  full_text TEXT,
  extracted_text TEXT, -- OCR or extracted text from PDFs

  -- Structured metadata
  mods_metadata JSONB, -- Full MODS XML parsed to JSON
  premis_metadata JSONB, -- Preservation metadata

  -- Processing metadata
  processing_status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
  processing_attempts INTEGER DEFAULT 0,
  last_processing_attempt TIMESTAMPTZ,
  processing_errors JSONB,

  -- Raw API response
  raw_summary JSONB,
  raw JSONB,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Foreign key
  FOREIGN KEY (collection_code) REFERENCES govinfo_collections(collection_code)
);

-- Indexes for packages
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_collection ON govinfo_packages(collection_code);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_date_issued ON govinfo_packages(date_issued);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_last_modified ON govinfo_packages(last_modified);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_type ON govinfo_packages(document_type);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_congress ON govinfo_packages(congress);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_bill_number ON govinfo_packages(bill_number);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_title ON govinfo_packages(title);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_processing_status ON govinfo_packages(processing_status);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_other_identifiers ON govinfo_packages USING GIN(other_identifiers);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_references ON govinfo_packages USING GIN("references");
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_related ON govinfo_packages USING GIN(related);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_mods_metadata ON govinfo_packages USING GIN(mods_metadata);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_full_text ON govinfo_packages USING GIN(to_tsvector('english', full_text));
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_extracted_text ON govinfo_packages USING GIN(to_tsvector('english', extracted_text));
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_title_search ON govinfo_packages USING GIN(to_tsvector('english', title));

CREATE TABLE IF NOT EXISTS govinfo_granules (
  -- Primary identifiers
  granule_id TEXT PRIMARY KEY,
  package_id TEXT NOT NULL,

  -- Granule metadata
  title TEXT,
  granule_class TEXT,
  date_issued DATE,
  last_modified TIMESTAMPTZ,

  -- Content information
  pages INTEGER,
  heading TEXT,
  sub_heading TEXT,

  -- Hierarchical information
  parent_package_id TEXT,
  sequence_number INTEGER,

  -- Content access
  text_link TEXT,
  pdf_link TEXT,
  xml_link TEXT,
  mods_link TEXT,
  premis_link TEXT,
  zip_link TEXT,

  -- Content availability
  has_text BOOLEAN DEFAULT FALSE,
  has_pdf BOOLEAN DEFAULT FALSE,
  has_xml BOOLEAN DEFAULT FALSE,
  has_mods BOOLEAN DEFAULT FALSE,
  has_premis BOOLEAN DEFAULT FALSE,

  -- Full text content
  full_text TEXT,
  extracted_text TEXT,

  -- Structured metadata
  mods_metadata JSONB,
  premis_metadata JSONB,

  -- Processing metadata
  processing_status TEXT DEFAULT 'pending',
  processing_attempts INTEGER DEFAULT 0,
  last_processing_attempt TIMESTAMPTZ,
  processing_errors JSONB,

  -- Raw API response
  raw JSONB,

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),
  last_api_update TIMESTAMPTZ DEFAULT now(),

  -- Foreign key
  FOREIGN KEY (package_id) REFERENCES govinfo_packages(package_id) ON DELETE CASCADE
);

-- Indexes for granules
CREATE INDEX IF NOT EXISTS idx_govinfo_granules_package ON govinfo_granules(package_id);
CREATE INDEX IF NOT EXISTS idx_govinfo_granules_date ON govinfo_granules(date_issued);
CREATE INDEX IF NOT EXISTS idx_govinfo_granules_title ON govinfo_granules(title);
CREATE INDEX IF NOT EXISTS idx_govinfo_granules_processing_status ON govinfo_granules(processing_status);
CREATE INDEX IF NOT EXISTS idx_govinfo_granules_mods_metadata ON govinfo_granules USING GIN(mods_metadata);

-- Full text search indexes for granules
CREATE INDEX IF NOT EXISTS idx_govinfo_granules_full_text ON govinfo_granules USING GIN(to_tsvector('english', full_text));
CREATE INDEX IF NOT EXISTS idx_govinfo_granules_extracted_text ON govinfo_granules USING GIN(to_tsvector('english', extracted_text));

CREATE TABLE IF NOT EXISTS govinfo_document_relationships (
  -- Primary identifiers
  id TEXT PRIMARY KEY,
  source_package_id TEXT NOT NULL,
  target_package_id TEXT NOT NULL,

  -- Relationship details
  relationship_type TEXT NOT NULL, -- cites, amends, supersedes, related_bill, etc.
  description TEXT,
  effective_date DATE,

  -- Source information
  collection_code TEXT,
  relationship_source TEXT, -- how this relationship was determined

  -- Metadata
  created_on TIMESTAMPTZ DEFAULT now(),
  updated_on TIMESTAMPTZ DEFAULT now(),

  -- Foreign keys
  FOREIGN KEY (source_package_id) REFERENCES govinfo_packages(package_id) ON DELETE CASCADE,
  FOREIGN KEY (target_package_id) REFERENCES govinfo_packages(package_id) ON DELETE CASCADE
);

-- Indexes for relationships
CREATE INDEX IF NOT EXISTS idx_govinfo_relationships_source ON govinfo_document_relationships(source_package_id);
CREATE INDEX IF NOT EXISTS idx_govinfo_relationships_target ON govinfo_document_relationships(target_package_id);
CREATE INDEX IF NOT EXISTS idx_govinfo_relationships_type ON govinfo_document_relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_govinfo_relationships_collection ON govinfo_document_relationships(collection_code);

CREATE TABLE IF NOT EXISTS govinfo_processing_log (
  -- Primary identifiers
  id SERIAL PRIMARY KEY,
  package_id TEXT,
  granule_id TEXT,

  -- Processing details
  operation TEXT NOT NULL, -- download, parse, extract, index, etc.
  status TEXT NOT NULL, -- started, completed, failed
  start_time TIMESTAMPTZ DEFAULT now(),
  end_time TIMESTAMPTZ,
  duration INTERVAL,

  -- Error information
  error_message TEXT,
  error_details JSONB,

  -- Processing metadata
  file_size INTEGER, -- bytes
  content_type TEXT,
  processing_node TEXT, -- which system/node did the processing

  -- Foreign keys
  FOREIGN KEY (package_id) REFERENCES govinfo_packages(package_id) ON DELETE CASCADE,
  FOREIGN KEY (granule_id) REFERENCES govinfo_granules(granule_id) ON DELETE CASCADE
);

-- Indexes for processing log
CREATE INDEX IF NOT EXISTS idx_govinfo_processing_log_package ON govinfo_processing_log(package_id);
CREATE INDEX IF NOT EXISTS idx_govinfo_processing_log_granule ON govinfo_processing_log(granule_id);
CREATE INDEX IF NOT EXISTS idx_govinfo_processing_log_operation ON govinfo_processing_log(operation);
CREATE INDEX IF NOT EXISTS idx_govinfo_processing_log_status ON govinfo_processing_log(status);
CREATE INDEX IF NOT EXISTS idx_govinfo_processing_log_start_time ON govinfo_processing_log(start_time);
