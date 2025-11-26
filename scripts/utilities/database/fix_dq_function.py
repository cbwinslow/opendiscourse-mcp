#!/usr/bin/env python3
"""
Fix data quality function akeys issue
"""

import os
import psycopg2

def fix_data_quality_function():
    """Fix the akeys function issue in check_data_quality"""
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    print("🔧 Fixing check_data_quality function...")
    
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
            
            -- Log quality issues if any found (fixed akeys issue)
            IF jsonb_typeof(quality_issues) != 'null' AND quality_issues != '{}'::jsonb THEN
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
    
    conn.commit()
    print("✅ check_data_quality function fixed!")
    
    conn.close()

if __name__ == "__main__":
    fix_data_quality_function()