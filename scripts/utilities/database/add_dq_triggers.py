#!/usr/bin/env python3
"""
Add missing data quality triggers
"""

import os
import psycopg2

def add_data_quality_triggers():
    """Add the missing data quality triggers"""
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    print("🔧 Adding missing data quality triggers...")
    
    # First ensure check_data_quality function exists
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
    
    # Add the triggers
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
    
    conn.commit()
    print("🎉 All data quality triggers added successfully!")
    
    conn.close()

if __name__ == "__main__":
    add_data_quality_triggers()