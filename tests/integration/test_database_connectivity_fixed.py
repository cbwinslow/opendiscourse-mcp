#!/usr/bin/env python3
"""
Test database connectivity and configuration (fixed)
"""

import os
import sys
import psycopg2
from psycopg2.extras import DictCursor
import time

def test_database_connectivity():
    """Comprehensive database connectivity and configuration test"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return False
    
    print("🔍 Testing Database Connectivity and Configuration...")
    print("=" * 60)
    
    try:
        # Test 1: Basic Connection
        print("\n📡 Test 1: Basic Database Connection")
        start_time = time.time()
        conn = psycopg2.connect(db_url)
        connection_time = time.time() - start_time
        print(f"✅ Connected successfully in {connection_time:.3f} seconds")
        
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        # Test 2: Database Version
        print("\n📊 Test 2: Database Information")
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL: {version.split(',')[0]}")
        
        # Test 3: Database Size
        cursor.execute("""
            SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
        """)
        db_size = cursor.fetchone()['db_size']
        print(f"✅ Database Size: {db_size}")
        
        # Test 4: Connection Limits
        cursor.execute("""
            SELECT setting as max_connections 
            FROM pg_settings 
            WHERE name = 'max_connections'
        """)
        max_conn = cursor.fetchone()['max_connections']
        print(f"✅ Max Connections: {max_conn}")
        
        # Test 5: Active Connections
        cursor.execute("""
            SELECT count(*) as active_connections 
            FROM pg_stat_activity 
            WHERE state = 'active'
        """)
        active_conn = cursor.fetchone()['active_connections']
        print(f"✅ Active Connections: {active_conn}")
        
        # Test 6: Table Count
        cursor.execute("""
            SELECT count(*) as table_count
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()['table_count']
        print(f"✅ Tables: {table_count}")
        
        # Test 7: Index Performance
        cursor.execute("""
            SELECT count(*) as index_count
            FROM pg_indexes 
            WHERE schemaname = 'public'
        """)
        index_count = cursor.fetchone()['index_count']
        print(f"✅ Indexes: {index_count}")
        
        # Test 8: Write Performance
        print("\n⚡ Test 8: Write Performance")
        start_time = time.time()
        cursor.execute("""
            CREATE TEMP TABLE test_perf (
                id SERIAL PRIMARY KEY,
                test_data TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Insert 1000 test records
        for i in range(1000):
            cursor.execute("""
                INSERT INTO test_perf (test_data) 
                VALUES ('test_record_%s')
            """, (i,))
        
        conn.commit()
        write_time = time.time() - start_time
        print(f"✅ Inserted 1000 records in {write_time:.3f} seconds")
        print(f"✅ Write Rate: {1000/write_time:.0f} records/second")
        
        # Test 9: Read Performance
        print("\n📖 Test 9: Read Performance")
        start_time = time.time()
        cursor.execute("SELECT COUNT(*) FROM test_perf")
        count = cursor.fetchone()[0]
        read_time = time.time() - start_time
        print(f"✅ Counted {count} records in {read_time:.3f} seconds")
        
        # Test 10: Check congress_bills structure first
        print("\n🔍 Test 10: Congress Bills Table Structure")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'congress_bills'
            AND table_schema = 'public'
            ORDER BY ordinal_position
            LIMIT 10
        """)
        columns = cursor.fetchall()
        print("✅ Congress bills columns:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")
        
        # Test 11: Trigger System Performance (using correct columns)
        print("\n⚡ Test 11: Trigger System Performance")
        cursor.execute("SELECT set_ingestion_job_context('connectivity_test')")
        
        start_time = time.time()
        cursor.execute("""
            INSERT INTO congress_bills (
                bill_id, congress, bill_type, title, 
                introduced_date, sponsor_bioguide_id
            ) VALUES (
                'test_connectivity', 118, 'hr', 
                'Database Connectivity Test Bill', 
                '2024-01-01', 'T000000'
            )
        """)
        conn.commit()
        trigger_time = time.time() - start_time
        print(f"✅ Trigger execution in {trigger_time:.3f} seconds")
        
        # Test 12: Job Progress Tracking
        cursor.execute("SELECT * FROM get_job_progress('connectivity_test')")
        progress = cursor.fetchall()
        print(f"✅ Job progress tracking: {len(progress)} records")
        
        # Test 13: Cleanup
        cursor.execute("DELETE FROM congress_bills WHERE bill_id = 'test_connectivity'")
        cursor.execute("SELECT clear_ingestion_job_context()")
        conn.commit()
        print("✅ Test data cleaned up")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 CONNECTIVITY TEST SUMMARY:")
        print(f"✅ Connection Time: {connection_time:.3f}s")
        print(f"✅ Write Performance: {1000/write_time:.0f} records/sec")
        print(f"✅ Read Performance: {count/read_time:.0f} records/sec")
        print(f"✅ Trigger Performance: {trigger_time:.3f}s")
        print(f"✅ Database Size: {db_size}")
        print(f"✅ All systems operational!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ DATABASE CONNECTIVITY TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connectivity()
    sys.exit(0 if success else 1)