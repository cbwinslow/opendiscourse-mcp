#!/usr/bin/env python3
"""
Fix get_job_progress function parameter conflict
"""

import os
import sys
import psycopg2

def fix_function_conflict():
    """Fix the get_job_progress function parameter conflict"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("🔧 Fixing get_job_progress function...")
        
        # Drop and recreate the function with different parameter name
        cursor.execute("DROP FUNCTION IF EXISTS get_job_progress(TEXT)")
        
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
        
        conn.commit()
        print("✅ get_job_progress function fixed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = fix_function_conflict()
    sys.exit(0 if success else 1)