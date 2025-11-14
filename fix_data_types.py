#!/usr/bin/env python3
"""
Check table structure and fix function data types
"""

import os
import psycopg2
from psycopg2.extras import DictCursor

def check_and_fix_structure():
    """Check table structure and fix data type issues"""
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    print("🔍 Checking ingestion_jobs table structure...")
    
    # Check table structure
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'ingestion_jobs'
        AND table_schema = 'public'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    
    print(f"\n📋 ingestion_jobs columns:")
    for col in columns:
        print(f"  - {col['column_name']}: {col['data_type']} ({'nullable' if col['is_nullable'] == 'YES' else 'not null'})")
    
    # Check if data quality triggers exist
    cursor.execute("""
        SELECT trigger_name 
        FROM information_schema.triggers 
        WHERE trigger_schema = 'public'
        AND trigger_name LIKE 'data_quality%'
        ORDER BY trigger_name
    """)
    dq_triggers = [row['trigger_name'] for row in cursor.fetchall()]
    
    print(f"\n⚡ Data Quality Triggers ({len(dq_triggers)}):")
    for trigger in dq_triggers:
        print(f"  - {trigger}")
    
    # Fix get_job_progress function with correct data types
    print(f"\n🔧 Fixing get_job_progress function...")
    cursor.execute("DROP FUNCTION IF EXISTS get_job_progress(TEXT)")
    
    cursor.execute("""
        CREATE OR REPLACE FUNCTION get_job_progress(p_job_id TEXT)
        RETURNS TABLE (
            processed_records INTEGER,
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
    
    # Test the function
    try:
        cursor.execute("SELECT * FROM get_job_progress('test')")
        result = cursor.fetchall()
        print(f"✅ get_job_progress works: {result}")
    except Exception as e:
        print(f"❌ get_job_progress still failed: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_and_fix_structure()