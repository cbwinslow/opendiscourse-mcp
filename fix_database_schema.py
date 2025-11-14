#!/usr/bin/env python3
"""
Fix missing database functions and triggers
"""

import os
import sys
import psycopg2

def fix_missing_components():
    """Add missing functions and triggers"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("🔧 Adding missing functions and triggers...")
        
        # Fix 1: Add check_data_quality function
        print("\n📝 Adding check_data_quality function...")
        cursor.execute("""
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
        """)
        print("✅ check_data_quality function added")
        
        # Fix 2: Add get_ingestion_alerts function
        print("\n📝 Adding get_ingestion_alerts function...")
        cursor.execute("""
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
        """)
        print("✅ get_ingestion_alerts function added")
        
        # Fix 3: Add data quality triggers
        print("\n📝 Adding data quality triggers...")
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS data_quality_bills_trigger ON congress_bills;
            CREATE TRIGGER data_quality_bills_trigger
                BEFORE INSERT OR UPDATE ON congress_bills
                FOR EACH ROW EXECUTE FUNCTION check_data_quality();
        """)
        print("✅ data_quality_bills_trigger added")
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS data_quality_members_trigger ON congress_members;
            CREATE TRIGGER data_quality_members_trigger
                BEFORE INSERT OR UPDATE ON congress_members
                FOR EACH ROW EXECUTE FUNCTION check_data_quality();
        """)
        print("✅ data_quality_members_trigger added")
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS data_quality_committees_trigger ON congress_committees;
            CREATE TRIGGER data_quality_committees_trigger
                BEFORE INSERT OR UPDATE ON congress_committees
                FOR EACH ROW EXECUTE FUNCTION check_data_quality();
        """)
        print("✅ data_quality_committees_trigger added")
        
        # Fix 4: Fix get_job_progress function (ambiguous column reference)
        print("\n📝 Fixing get_job_progress function...")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_job_progress(p_job_id TEXT)
            RETURNS TABLE (
                processed_records BIGINT,
                status TEXT,
                last_updated TIMESTAMP
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT ij.processed_records, ij.status, ij.updated_at
                FROM ingestion_jobs ij
                WHERE ij.job_id = p_job_id;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("✅ get_job_progress function fixed")
        
        conn.commit()
        print("\n🎉 All missing components added successfully!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = fix_missing_components()
    sys.exit(0 if success else 1)