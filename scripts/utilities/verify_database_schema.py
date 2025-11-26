#!/usr/bin/env python3
"""
Database schema verification script for OpenDiscourse.
Checks if all required tables, triggers, and functions exist.
"""

import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
from typing import Dict, List

def get_database_connection():
    """Get database connection from environment"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    return psycopg2.connect(db_url)

def check_tables(conn) -> Dict[str, bool]:
    """Check if all required tables exist"""
    required_tables = [
        # Core ingestion tables
        'congress_bills',
        'congress_members', 
        'congress_committees',
        'congress_votes',
        'congress_bill_actions',
        'congress_bill_text',
        
        # OpenStates tables
        'opencivicdata_bill',
        'opencivicdata_person',
        'opencivicdata_organization',
        'opencivicdata_voteevent',
        'opencivicdata_membership',
        'opencivicdata_event',
        
        # GovInfo tables
        'govinfo_packages',
        'govinfo_granules', 
        'govinfo_collections',
        
        # Monitoring tables
        'ingestion_jobs',
        'record_hashes',
        'ingestion_performance_log',
        'data_quality_monitoring',
        'resource_usage_monitoring'
    ]
    
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
    """)
    existing_tables = {row['table_name'] for row in cursor.fetchall()}
    
    table_status = {}
    for table in required_tables:
        table_status[table] = table in existing_tables
        if table in existing_tables:
            print(f"✅ Table '{table}' exists")
        else:
            print(f"❌ Table '{table}' MISSING")
    
    return table_status

def check_triggers(conn) -> Dict[str, bool]:
    """Check if all required triggers exist"""
    required_triggers = [
        # Congress triggers
        'trg_congress_bills_progress',
        'trg_congress_members_progress', 
        'trg_congress_committees_progress',
        'trg_congress_votes_progress',
        'trg_congress_bill_actions_progress',
        'trg_congress_bill_text_progress',
        
        # OpenStates triggers
        'trg_opencivicdata_bill_progress',
        'trg_opencivicdata_person_progress',
        'trg_opencivicdata_organization_progress',
        'trg_opencivicdata_voteevent_progress',
        'trg_opencivicdata_membership_progress',
        'trg_opencivicdata_event_progress',
        
        # GovInfo triggers
        'trg_govinfo_packages_progress',
        'trg_govinfo_granules_progress',
        'trg_govinfo_collections_progress',
        
        # Data quality triggers
        'data_quality_bills_trigger',
        'data_quality_members_trigger',
        'data_quality_committees_trigger'
    ]
    
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("""
        SELECT trigger_name 
        FROM information_schema.triggers 
        WHERE trigger_schema = 'public'
    """)
    existing_triggers = {row['trigger_name'] for row in cursor.fetchall()}
    
    trigger_status = {}
    for trigger in required_triggers:
        trigger_status[trigger] = trigger in existing_triggers
        if trigger in existing_triggers:
            print(f"✅ Trigger '{trigger}' exists")
        else:
            print(f"❌ Trigger '{trigger}' MISSING")
    
    return trigger_status

def check_functions(conn) -> Dict[str, bool]:
    """Check if all required functions exist"""
    required_functions = [
        'update_ingestion_progress',
        'check_duplicate_record',
        'set_ingestion_job_context',
        'clear_ingestion_job_context',
        'get_job_progress',
        'check_data_quality',
        'get_ingestion_alerts'
    ]
    
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("""
        SELECT routine_name 
        FROM information_schema.routines 
        WHERE routine_schema = 'public'
        AND routine_type = 'FUNCTION'
    """)
    existing_functions = {row['routine_name'] for row in cursor.fetchall()}
    
    function_status = {}
    for function in required_functions:
        function_status[function] = function in existing_functions
        if function in existing_functions:
            print(f"✅ Function '{function}' exists")
        else:
            print(f"❌ Function '{function}' MISSING")
    
    return function_status

def check_indexes(conn) -> Dict[str, bool]:
    """Check if performance indexes exist"""
    important_indexes = [
        'idx_perf_log_job_id',
        'idx_perf_log_timestamp',
        'idx_dq_table',
        'idx_dq_timestamp',
        'idx_resource_job_id',
        'idx_resource_timestamp'
    ]
    
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'public'
    """)
    existing_indexes = {row['indexname'] for row in cursor.fetchall()}
    
    index_status = {}
    for index in important_indexes:
        index_status[index] = index in existing_indexes
        if index in existing_indexes:
            print(f"✅ Index '{index}' exists")
        else:
            print(f"⚠️  Index '{index}' missing (may affect performance)")
    
    return index_status

def test_trigger_functionality(conn) -> bool:
    """Test if trigger system is working"""
    cursor = conn.cursor()
    
    try:
        # Test setting job context
        cursor.execute("SELECT set_ingestion_job_context('test_job_id')")
        print("✅ Job context function works")
        
        # Test clearing job context  
        cursor.execute("SELECT clear_ingestion_job_context()")
        print("✅ Job context clearing works")
        
        # Test getting job progress
        cursor.execute("SELECT * FROM get_job_progress('test_job_id')")
        print("✅ Job progress function works")
        
        return True
        
    except Exception as e:
        print(f"❌ Trigger functionality test failed: {e}")
        return False

def main():
    """Main verification function"""
    print("🔍 Verifying OpenDiscourse Database Schema...")
    print("=" * 60)
    
    conn = None
    try:
        conn = get_database_connection()
        
        # Check all components
        print("\n📋 Checking Tables:")
        table_status = check_tables(conn)
        
        print("\n⚡ Checking Triggers:")
        trigger_status = check_triggers(conn)
        
        print("\n🔧 Checking Functions:")
        function_status = check_functions(conn)
        
        print("\n📈 Checking Indexes:")
        index_status = check_indexes(conn)
        
        print("\n🧪 Testing Functionality:")
        functionality_works = test_trigger_functionality(conn)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 SUMMARY:")
        
        all_tables_ok = all(table_status.values())
        all_triggers_ok = all(trigger_status.values())
        all_functions_ok = all(function_status.values())
        
        print(f"Tables: {'✅ OK' if all_tables_ok else '❌ ISSUES'}")
        print(f"Triggers: {'✅ OK' if all_triggers_ok else '❌ ISSUES'}")  
        print(f"Functions: {'✅ OK' if all_functions_ok else '❌ ISSUES'}")
        print(f"Functionality: {'✅ OK' if functionality_works else '❌ ISSUES'}")
        
        # Overall status
        overall_ok = all_tables_ok and all_triggers_ok and all_functions_ok and functionality_works
        
        if overall_ok:
            print("\n🎉 DATABASE SCHEMA IS READY FOR INGESTION!")
            return 0
        else:
            print("\n❌ DATABASE SCHEMA HAS ISSUES - NEEDS SETUP")
            return 1
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return 1
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    sys.exit(main())