-- Comprehensive database triggers for detailed analysis and benchmarking
-- These triggers provide automatic telemetry and audit trails for all ingestion operations

-- 1. Enhanced Ingestion Job Monitoring Trigger
CREATE OR REPLACE FUNCTION update_ingestion_progress()
RETURNS TRIGGER AS $$
DECLARE
    active_job_id TEXT;
    table_name TEXT;
    start_time TIMESTAMP WITH TIME ZONE;
    processing_time INTEGER;
BEGIN
    -- Get active job ID from session variable (set by ingestion scripts)
    active_job_id := current_setting('ingestion.active_job_id', TRUE);

    -- If no active job, skip monitoring
    IF active_job_id IS NULL OR active_job_id = '' THEN
        RETURN NEW;
    END IF;

    -- Get table name and calculate processing time
    table_name := TG_TABLE_NAME;
    start_time := clock_timestamp();

    -- Update ingestion job progress with performance metrics
    UPDATE ingestion_jobs
    SET
        processed_records = processed_records + 1,
        updated_at = NOW(),
        metadata = jsonb_set(
            COALESCE(metadata, '{}'::jsonb),
            '{last_processing_time_ms}',
            (EXTRACT(MILLISECOND FROM (clock_timestamp() - start_time)))::jsonb
        )
    WHERE job_id = active_job_id
      AND status = 'running';

    -- Log detailed performance metrics
    INSERT INTO ingestion_performance_log (
        job_id, table_name, operation_type, processing_time_ms, timestamp
    ) VALUES (
        active_job_id, table_name, TG_OP, 
        EXTRACT(MILLISECOND FROM (clock_timestamp() - start_time))::INTEGER,
        NOW()
    );

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

-- ===========================================
-- ENHANCED MONITORING TABLES
-- ===========================================

-- Performance logging table
CREATE TABLE IF NOT EXISTS ingestion_performance_log (
    id SERIAL PRIMARY KEY,
    job_id TEXT NOT NULL,
    table_name TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    processing_time_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_perf_log_job_id ON ingestion_performance_log(job_id);
CREATE INDEX idx_perf_log_timestamp ON ingestion_performance_log(timestamp);

-- Data quality monitoring table
CREATE TABLE IF NOT EXISTS data_quality_monitoring (
    id SERIAL PRIMARY KEY,
    table_name TEXT NOT NULL,
    record_id TEXT,
    quality_check TEXT NOT NULL,
    status TEXT NOT NULL, -- 'PASS', 'FAIL', 'WARNING'
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_dq_table ON data_quality_monitoring(table_name);
CREATE INDEX idx_dq_timestamp ON data_quality_monitoring(timestamp);

-- Resource usage monitoring table
CREATE TABLE IF NOT EXISTS resource_usage_monitoring (
    id SERIAL PRIMARY KEY,
    job_id TEXT,
    cpu_usage_percent NUMERIC(5,2),
    memory_usage_mb NUMERIC(10,2),
    disk_io_mb NUMERIC(10,2),
    network_io_mb NUMERIC(10,2),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_resource_job_id ON resource_usage_monitoring(job_id);
CREATE INDEX idx_resource_timestamp ON resource_usage_monitoring(timestamp);

-- ===========================================
-- DATA QUALITY TRIGGERS
-- ===========================================

CREATE OR REPLACE FUNCTION check_data_quality()
RETURNS TRIGGER AS $$
DECLARE
    quality_issues JSONB := '{}';
    record_identifier TEXT;
BEGIN
    -- Get record identifier based on table
    CASE TG_TABLE_NAME
        WHEN 'congress_bills' THEN
            record_identifier := NEW.bill_id;
            -- Check bill data quality
            IF NEW.bill_id IS NULL OR NEW.bill_id = '' THEN
                quality_issues := jsonb_set(quality_issues, '{missing_bill_id}', 'true'::jsonb);
            END IF;
            
            IF NEW.congress IS NULL OR NEW.congress < 100 OR NEW.congress > 200 THEN
                quality_issues := jsonb_set(quality_issues, '{invalid_congress}', jsonb_build_object('value', NEW.congress));
            END IF;
            
            IF NEW.title IS NULL OR LENGTH(NEW.title) < 10 THEN
                quality_issues := jsonb_set(quality_issues, '{short_title}', jsonb_build_object('length', LENGTH(COALESCE(NEW.title, ''))));
            END IF;
            
        WHEN 'congress_members' THEN
            record_identifier := NEW.bioguide_id;
            -- Check member data quality
            IF NEW.bioguide_id IS NULL OR NEW.bioguide_id = '' THEN
                quality_issues := jsonb_set(quality_issues, '{missing_bioguide_id}', 'true'::jsonb);
            END IF;
            
            IF NEW.first_name IS NULL OR NEW.last_name IS NULL THEN
                quality_issues := jsonb_set(quality_issues, '{missing_name}', 'true'::jsonb);
            END IF;
            
        WHEN 'congress_committees' THEN
            record_identifier := NEW.committee_code;
            -- Check committee data quality
            IF NEW.committee_code IS NULL OR NEW.committee_code = '' THEN
                quality_issues := jsonb_set(quality_issues, '{missing_committee_code}', 'true'::jsonb);
            END IF;
            
            IF NEW.name IS NULL OR LENGTH(NEW.name) < 5 THEN
                quality_issues := jsonb_set(quality_issues, '{invalid_name}', jsonb_build_object('name', COALESCE(NEW.name, '')));
            END IF;
    END CASE;
    
    -- Log quality issues if any found
    IF jsonb_array_length(akeys(quality_issues)) > 0 THEN
        INSERT INTO data_quality_monitoring (
            table_name, record_id, quality_check, status, details, timestamp
        ) VALUES (
            TG_TABLE_NAME,
            record_identifier,
            'automated_quality_check',
            'FAIL',
            quality_issues,
            NOW()
        );
    ELSE
        -- Log successful quality check
        INSERT INTO data_quality_monitoring (
            table_name, record_id, quality_check, status, details, timestamp
        ) VALUES (
            TG_TABLE_NAME,
            record_identifier,
            'automated_quality_check',
            'PASS',
            '{}'::jsonb,
            NOW()
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply data quality triggers
DROP TRIGGER IF EXISTS data_quality_bills_trigger ON congress_bills;
CREATE TRIGGER data_quality_bills_trigger
    BEFORE INSERT OR UPDATE ON congress_bills
    FOR EACH ROW EXECUTE FUNCTION check_data_quality();

DROP TRIGGER IF EXISTS data_quality_members_trigger ON congress_members;
CREATE TRIGGER data_quality_members_trigger
    BEFORE INSERT OR UPDATE ON congress_members
    FOR EACH ROW EXECUTE FUNCTION check_data_quality();

DROP TRIGGER IF EXISTS data_quality_committees_trigger ON congress_committees;
CREATE TRIGGER data_quality_committees_trigger
    BEFORE INSERT OR UPDATE ON congress_committees
    FOR EACH ROW EXECUTE FUNCTION check_data_quality();

-- ===========================================
-- PERFORMANCE ANALYSIS VIEWS
-- ===========================================

CREATE OR REPLACE VIEW ingestion_performance_summary AS
SELECT 
    DATE(ijl.timestamp) as performance_date,
    ijl.table_name,
    COUNT(*) as total_operations,
    AVG(ijl.processing_time_ms) as avg_processing_time_ms,
    MAX(ijl.processing_time_ms) as max_processing_time_ms,
    MIN(ijl.processing_time_ms) as min_processing_time_ms,
    STDDEV(ijl.processing_time_ms) as stddev_processing_time_ms
FROM ingestion_performance_log ijl
GROUP BY DATE(ijl.timestamp), ijl.table_name
ORDER BY performance_date DESC, ijl.table_name;

CREATE OR REPLACE VIEW data_quality_summary AS
SELECT 
    DATE(dqm.timestamp) as quality_date,
    dqm.table_name,
    COUNT(*) as total_checks,
    COUNT(CASE WHEN dqm.status = 'PASS' THEN 1 END) as passed_checks,
    COUNT(CASE WHEN dqm.status = 'FAIL' THEN 1 END) as failed_checks,
    COUNT(CASE WHEN dqm.status = 'WARNING' THEN 1 END) as warning_checks,
    ROUND((COUNT(CASE WHEN dqm.status = 'PASS' THEN 1 END) * 100.0 / COUNT(*)), 2) as pass_rate_percent
FROM data_quality_monitoring dqm
GROUP BY DATE(dqm.timestamp), dqm.table_name
ORDER BY quality_date DESC, dqm.table_name;

-- ===========================================
-- ALERT FUNCTIONS
-- ===========================================

CREATE OR REPLACE FUNCTION get_ingestion_alerts()
RETURNS TABLE (
    alert_type TEXT,
    severity TEXT,
    message TEXT,
    details JSONB
) AS $$
BEGIN
    -- Slow running jobs alert
    RETURN QUERY
    SELECT 
        'slow_job'::TEXT,
        'WARNING'::TEXT,
        format('Job %s has been running for %s minutes', 
               ij.job_id, 
               EXTRACT(EPOCH FROM (NOW() - ij.start_time))/60)::TEXT,
        jsonb_build_object(
            'job_id', ij.job_id,
            'running_minutes', EXTRACT(EPOCH FROM (NOW() - ij.start_time))/60,
            'processed_records', ij.processed_records
        )
    FROM ingestion_jobs ij
    WHERE ij.status = 'running' 
    AND ij.start_time < NOW() - INTERVAL '30 minutes';
    
    -- High error rate alert
    RETURN QUERY
    SELECT 
        'high_error_rate'::TEXT,
        'CRITICAL'::TEXT,
        format('Error rate is %.2f%% in the last hour', 
               error_rate::TEXT),
        jsonb_build_object(
            'error_rate', error_rate,
            'total_jobs', job_count,
            'failed_jobs', failed_count
        )
    FROM (
        SELECT 
            COUNT(*) as job_count,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
            (COUNT(CASE WHEN status = 'failed' THEN 1 END) * 100.0 / COUNT(*)) as error_rate
        FROM ingestion_jobs 
        WHERE created_at > NOW() - INTERVAL '1 hour'
    ) sub
    WHERE error_rate > 10;
    
    -- Data quality issues alert
    RETURN QUERY
    SELECT 
        'data_quality_issues'::TEXT,
        'WARNING'::TEXT,
        format('Data quality pass rate is %.2f%% for table %s', 
               pass_rate::TEXT, table_name::TEXT),
        jsonb_build_object(
            'table_name', table_name,
            'pass_rate', pass_rate,
            'failed_checks', failed_checks
        )
    FROM (
        SELECT 
            table_name,
            COUNT(*) as total_checks,
            COUNT(CASE WHEN status = 'PASS' THEN 1 END) as passed_checks,
            COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failed_checks,
            (COUNT(CASE WHEN status = 'PASS' THEN 1 END) * 100.0 / COUNT(*)) as pass_rate
        FROM data_quality_monitoring 
        WHERE timestamp > NOW() - INTERVAL '24 hours'
        GROUP BY table_name
    ) sub
    WHERE pass_rate < 95;
    
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT ON ingestion_performance_log TO opendiscourse;
GRANT SELECT, INSERT ON data_quality_monitoring TO opendiscourse;
GRANT SELECT, INSERT ON resource_usage_monitoring TO opendiscourse;
GRANT SELECT ON ingestion_performance_summary TO opendiscourse;
GRANT SELECT ON data_quality_summary TO opendiscourse;
