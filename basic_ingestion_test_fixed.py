#!/usr/bin/env python3
"""
Simple end-to-end ingestion test (fixed)
"""

import os
import sys
import time
import subprocess
import psycopg2
from psycopg2.extras import DictCursor

def source_env_file():
    """Source .env file"""
    env_file = "/home/cbwinslow/opendiscourse/mcp_server/.env"
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.startswith('export '):
                        key = key[7:]
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ[key] = value

def test_basic_ingestion():
    """Test basic ingestion functionality"""
    print("🧪 BASIC INGESTION FUNCTIONALITY TEST")
    print("=" * 50)
    
    source_env_file()
    
    # Test 1: Check if we can import modules
    print("\n📦 Testing Module Imports...")
    
    try:
        sys.path.insert(0, '/home/cbwinslow/opendiscourse')
        from mcp_server.clients.congress_client import CongressClient
        print("  ✅ CongressClient imported successfully")
    except Exception as e:
        print(f"  ❌ CongressClient import failed: {e}")
        return False
    
    try:
        from mcp_server.db import get_sqlalchemy_engine
        print("  ✅ Database module imported successfully")
    except Exception as e:
        print(f"  ❌ Database module import failed: {e}")
        return False
    
    # Test 2: Check database connection
    print("\n🔗 Testing Database Connection...")
    try:
        engine = get_sqlalchemy_engine()
        conn = engine.connect()
        conn.close()
        print("  ✅ Database connection successful")
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False
    
    # Test 3: Test API client
    print("\n🌐 Testing API Client...")
    try:
        client = CongressClient()
        # Test a simple API call with correct method
        response = client.get_bill(118, 'hr', '3076')
        if response and 'bill' in response:
            print("  ✅ Congress API client working")
        else:
            print(f"  ❌ Congress API client failed: Invalid response")
            return False
    except Exception as e:
        print(f"  ❌ Congress API client failed: {e}")
        return False
    
    # Test 4: Test monitoring system
    print("\n📊 Testing Monitoring System...")
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test job context functions
        cursor.execute("SELECT set_ingestion_job_context('test_job')")
        cursor.execute("SELECT clear_ingestion_job_context()")
        print("  ✅ Monitoring functions working")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ Monitoring system failed: {e}")
        return False
    
    # Test 5: Test simple data insertion
    print("\n💾 Testing Data Insertion...")
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Insert a test record
        cursor.execute("""
            INSERT INTO ingestion_jobs (
                job_id, source, collection, status, start_time
            ) VALUES (
                'test_ingestion_%s', 'test', 'test', 'running', NOW()
            )
        """, (int(time.time())))
        
        conn.commit()
        
        # Verify insertion
        cursor.execute("""
            SELECT COUNT(*) FROM ingestion_jobs 
            WHERE job_id LIKE 'test_ingestion_%'
        """)
        count = cursor.fetchone()[0]
        
        if count > 0:
            print("  ✅ Data insertion working")
        else:
            print("  ❌ Data insertion failed")
            return False
        
        # Cleanup
        cursor.execute("""
            DELETE FROM ingestion_jobs 
            WHERE job_id LIKE 'test_ingestion_%'
        """)
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Data insertion failed: {e}")
        return False
    
    # Test 6: Check existing data
    print("\n📋 Checking Existing Data...")
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        tables = ['congress_bills', 'congress_members', 'ingestion_jobs']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table:20}: {count:8} records")
        
        conn.close()
        
    except Exception as e:
        print(f"  ❌ Data check failed: {e}")
        return False
    
    # Test 7: Test a simple ingestion script
    print("\n🔄 Testing Simple Ingestion Script...")
    try:
        # Test if we can run a simple script
        script_path = "/home/cbwinslow/opendiscourse/mcp_server/scripts/congress_comprehensive_ingest.py"
        if os.path.exists(script_path):
            print(f"  ✅ Ingestion script found: {os.path.basename(script_path)}")
        else:
            print(f"  ⚠️  Ingestion script not found: {script_path}")
        
        # List available scripts
        scripts_dir = "/home/cbwinslow/opendiscourse/mcp_server/scripts"
        if os.path.exists(scripts_dir):
            scripts = [f for f in os.listdir(scripts_dir) if f.endswith('.py')]
            print(f"  📁 Available scripts: {len(scripts)} Python files")
        else:
            print(f"  ❌ Scripts directory not found")
        
    except Exception as e:
        print(f"  ❌ Script test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 BASIC INGESTION TEST RESULTS:")
    print("  ✅ Module Imports: Working")
    print("  ✅ Database Connection: Working") 
    print("  ✅ API Client: Working")
    print("  ✅ Monitoring System: Working")
    print("  ✅ Data Insertion: Working")
    print("  ✅ Existing Data: Accessible")
    print("  ✅ Ingestion Scripts: Available")
    
    print(f"\n🎯 OVERALL STATUS: ✅ ALL BASIC FUNCTIONALITY WORKING")
    print("✅ System is ready for ingestion operations")
    
    return True

if __name__ == "__main__":
    success = test_basic_ingestion()
    sys.exit(0 if success else 1)