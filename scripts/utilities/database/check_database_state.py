#!/usr/bin/env python3
"""
Check actual database state
"""

import os
import psycopg2
from psycopg2.extras import DictCursor

def check_database_state():
    """Check what's actually in the database"""
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    print("🔍 Checking actual database state...")
    
    # Check triggers
    cursor.execute("""
        SELECT trigger_name 
        FROM information_schema.triggers 
        WHERE trigger_schema = 'public'
        ORDER BY trigger_name
    """)
    triggers = [row['trigger_name'] for row in cursor.fetchall()]
    print(f"\n⚡ Triggers ({len(triggers)}):")
    for trigger in triggers:
        print(f"  - {trigger}")
    
    # Check functions
    cursor.execute("""
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public'
        AND routine_type = 'FUNCTION'
        ORDER BY routine_name
    """)
    functions = [row['routine_name'] for row in cursor.fetchall()]
    print(f"\n🔧 Functions ({len(functions)}):")
    for function in functions:
        print(f"  - {function}")
    
    # Test the specific functions we need
    print(f"\n🧪 Testing specific functions:")
    
    try:
        cursor.execute("SELECT * FROM get_job_progress('test')")
        result = cursor.fetchall()
        print(f"✅ get_job_progress works: {result}")
    except Exception as e:
        print(f"❌ get_job_progress failed: {e}")
    
    try:
        cursor.execute("SELECT * FROM get_ingestion_alerts()")
        result = cursor.fetchall()
        print(f"✅ get_ingestion_alerts works: {len(result)} alerts")
    except Exception as e:
        print(f"❌ get_ingestion_alerts failed: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_database_state()