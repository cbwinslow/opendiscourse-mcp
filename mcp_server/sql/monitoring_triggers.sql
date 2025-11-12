-- Database triggers for automatic ingestion monitoring
-- Provides real-time progress tracking without manual updates

-- ===========================================
-- TRIGGER FUNCTION FOR INGESTION MONITORING
-- ===========================================

CREATE OR REPLACE FUNCTION update_ingestion_progress()
RETURNS TRIGGER AS $$
DECLARE
    active_job_id TEXT;
    table_name TEXT;
BEGIN
    -- Get the active job ID from session variable (set by ingestion scripts)
    active_job_id := current_setting('ingestion.active_job_id', TRUE);

    -- If no active job, skip monitoring
    IF active_job_id IS NULL OR active_job_id = '' THEN
        RETURN NEW;
    END IF;

    -- Get table name
    table_name := TG_TABLE_NAME;

    -- Update the ingestion job progress
    UPDATE ingestion_jobs
    SET
        processed_records = processed_records + 1,
        updated_at = NOW()
    WHERE job_id = active_job_id
      AND status = 'running';

    -- Log the operation (optional - can be disabled for performance)
    -- INSERT INTO ingestion_log (job_id, table_name, operation, record_count)
    -- VALUES (active_job_id, table_name, 'INSERT', 1);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- TRIGGERS FOR CONGRESS TABLES
-- ===========================================

-- Congress Bills
DROP TRIGGER IF EXISTS trg_congress_bills_progress ON congress_bills;
CREATE TRIGGER trg_congress_bills_progress
    AFTER INSERT ON congress_bills
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- Congress Members
DROP TRIGGER IF EXISTS trg_congress_members_progress ON congress_members;
CREATE TRIGGER trg_congress_members_progress
    AFTER INSERT ON congress_members
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- Congress Committees
DROP TRIGGER IF EXISTS trg_congress_committees_progress ON congress_committees;
CREATE TRIGGER trg_congress_committees_progress
    AFTER INSERT ON congress_committees
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- Congress Votes
DROP TRIGGER IF EXISTS trg_congress_votes_progress ON congress_votes;
CREATE TRIGGER trg_congress_votes_progress
    AFTER INSERT ON congress_votes
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- Congress Bill Actions
DROP TRIGGER IF EXISTS trg_congress_bill_actions_progress ON congress_bill_actions;
CREATE TRIGGER trg_congress_bill_actions_progress
    AFTER INSERT ON congress_bill_actions
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- Congress Bill Text
DROP TRIGGER IF EXISTS trg_congress_bill_text_progress ON congress_bill_text;
CREATE TRIGGER trg_congress_bill_text_progress
    AFTER INSERT ON congress_bill_text
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- ===========================================
-- TRIGGERS FOR OPENSTATES TABLES
-- ===========================================

-- OpenStates Bills
DROP TRIGGER IF EXISTS trg_opencivicdata_bill_progress ON opencivicdata_bill;
CREATE TRIGGER trg_opencivicdata_bill_progress
    AFTER INSERT ON opencivicdata_bill
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- OpenStates People
DROP TRIGGER IF EXISTS trg_opencivicdata_person_progress ON opencivicdata_person;
CREATE TRIGGER trg_opencivicdata_person_progress
    AFTER INSERT ON opencivicdata_person
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- OpenStates Organizations
DROP TRIGGER IF EXISTS trg_opencivicdata_organization_progress ON opencivicdata_organization;
CREATE TRIGGER trg_opencivicdata_organization_progress
    AFTER INSERT ON opencivicdata_organization
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- OpenStates Vote Events
DROP TRIGGER IF EXISTS trg_opencivicdata_voteevent_progress ON opencivicdata_voteevent;
CREATE TRIGGER trg_opencivicdata_voteevent_progress
    AFTER INSERT ON opencivicdata_voteevent
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- OpenStates Memberships
DROP TRIGGER IF EXISTS trg_opencivicdata_membership_progress ON opencivicdata_membership;
CREATE TRIGGER trg_opencivicdata_membership_progress
    AFTER INSERT ON opencivicdata_membership
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- OpenStates Events
DROP TRIGGER IF EXISTS trg_opencivicdata_event_progress ON opencivicdata_event;
CREATE TRIGGER trg_opencivicdata_event_progress
    AFTER INSERT ON opencivicdata_event
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- ===========================================
-- TRIGGERS FOR GOVINFO TABLES
-- ===========================================

-- GovInfo Packages
DROP TRIGGER IF EXISTS trg_govinfo_packages_progress ON govinfo_packages;
CREATE TRIGGER trg_govinfo_packages_progress
    AFTER INSERT ON govinfo_packages
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- GovInfo Granules
DROP TRIGGER IF EXISTS trg_govinfo_granules_progress ON govinfo_granules;
CREATE TRIGGER trg_govinfo_granules_progress
    AFTER INSERT ON govinfo_granules
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- GovInfo Collections
DROP TRIGGER IF EXISTS trg_govinfo_collections_progress ON govinfo_collections;
CREATE TRIGGER trg_govinfo_collections_progress
    AFTER INSERT ON govinfo_collections
    FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();

-- ===========================================
-- DEDUPLICATION TRIGGER FUNCTION
-- ===========================================

CREATE OR REPLACE FUNCTION check_duplicate_record()
RETURNS TRIGGER AS $$
DECLARE
    content_hash TEXT;
    table_name TEXT;
    record_id TEXT;
BEGIN
    -- Get table and record info
    table_name := TG_TABLE_NAME;

    -- Generate content hash (exclude metadata fields that change)
    -- This is a simplified version - in practice you'd want more sophisticated hashing
    content_hash := md5(NEW::TEXT);

    -- Check if this content already exists
    IF EXISTS (
        SELECT 1 FROM record_hashes
        WHERE table_name = table_name
          AND content_hash = content_hash
    ) THEN
        -- Log duplicate attempt
        RAISE WARNING 'Duplicate record detected in table % with hash %', table_name, content_hash;
        -- Could either skip insert or allow with warning
        -- For now, allow but log
    ELSE
        -- Insert hash for future duplicate checking
        INSERT INTO record_hashes (table_name, record_id, content_hash)
        VALUES (table_name, NEW.id, content_hash);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- UTILITY FUNCTIONS
-- ===========================================

-- Function to set active job context
CREATE OR REPLACE FUNCTION set_ingestion_job_context(job_id TEXT)
RETURNS VOID AS $$
BEGIN
    -- Set session variable for triggers
    PERFORM set_config('ingestion.active_job_id', job_id, FALSE);
END;
$$ LANGUAGE plpgsql;

-- Function to clear job context
CREATE OR REPLACE FUNCTION clear_ingestion_job_context()
RETURNS VOID AS $$
BEGIN
    -- Clear session variable
    PERFORM set_config('ingestion.active_job_id', '', FALSE);
END;
$$ LANGUAGE plpgsql;

-- Function to get current job progress
CREATE OR REPLACE FUNCTION get_job_progress(job_id TEXT)
RETURNS TABLE (
    processed_records BIGINT,
    status TEXT,
    last_updated TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT ij.processed_records, ij.status, ij.updated_at
    FROM ingestion_jobs ij
    WHERE ij.job_id = job_id;
END;
$$ LANGUAGE plpgsql;
