#!/usr/bin/env python3
"""
Final comprehensive end-to-end test
"""

import os
import sys
import time
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

def test_comprehensive_functionality():
    """Comprehensive functionality test"""
    print("🧪 COMPREHENSIVE END-TO-END TEST")
    print("=" * 60)
    
    source_env_file()
    
    test_results = {}
    
    # Test 1: Environment Setup
    print("\n🔧 Test 1: Environment Setup")
    try:
        required_vars = ['DATABASE_URL', 'CONGRESS_API_KEY', 'GOVINFO_API_KEY', 'OPENSTATES_API_KEY']
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"  ❌ Missing environment variables: {missing_vars}")
            test_results['environment'] = False
        else:
            print("  ✅ All required environment variables set")
            test_results['environment'] = True
    except Exception as e:
        print(f"  ❌ Environment check failed: {e}")
        test_results['environment'] = False
    
    # Test 2: Database Connectivity
    print("\n🗄️  Test 2: Database Connectivity")
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result[0] == 1:
            print("  ✅ Database connection working")
            test_results['database'] = True
        else:
            print("  ❌ Database query failed")
            test_results['database'] = False
            
        conn.close()
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        test_results['database'] = False
    
    # Test 3: API Connectivity
    print("\n🌐 Test 3: API Connectivity")
    import requests
    
    api_tests = [
        ('Congress', 'https://api.congress.gov/v3/bill?congress=118&limit=1', 
         {'X-API-Key': os.getenv('CONGRESS_API_KEY')}),
        ('GovInfo', 'https://api.govinfo.gov/collections', 
         {'api_key': os.getenv('GOVINFO_API_KEY')}),
        ('OpenStates', 'https://v3.openstates.org/jurisdictions?limit=1', 
         {'X-API-Key': os.getenv('OPENSTATES_API_KEY')})
    ]
    
    api_success = 0
    for name, url, auth in api_tests:
        try:
            if 'api_key' in auth:
                response = requests.get(url, params=auth, timeout=10)
            else:
                response = requests.get(url, headers=auth, timeout=10)
            
            if response.status_code == 200:
                print(f"  ✅ {name} API working")
                api_success += 1
            else:
                print(f"  ❌ {name} API failed: {response.status_code}")
        except Exception as e:
            print(f"  ❌ {name} API error: {e}")
    
    test_results['apis'] = api_success >= 2  # At least 2 APIs working
    
    # Test 4: Database Schema
    print("\n📊 Test 4: Database Schema")
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check key tables
        tables_to_check = ['congress_bills', 'congress_members', 'ingestion_jobs', 'ingestion_performance_log']
        tables_found = 0
        
        for table in tables_to_check:
            cursor.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
            if cursor.fetchone()[0] > 0:
                tables_found += 1
        
        if tables_found == len(tables_to_check):
            print(f"  ✅ All {len(tables_to_check)} key tables found")
            test_results['schema'] = True
        else:
            print(f"  ❌ Only {tables_found}/{len(tables_to_check)} tables found")
            test_results['schema'] = False
            
        conn.close()
    except Exception as e:
        print(f"  ❌ Schema check failed: {e}")
        test_results['schema'] = False
    
    # Test 5: Monitoring System
    print("\n📈 Test 5: Monitoring System")
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test monitoring functions
        cursor.execute("SELECT set_ingestion_job_context('test_monitoring')")
        cursor.execute("SELECT * FROM get_job_progress('test_monitoring')")
        cursor.execute("SELECT clear_ingestion_job_context()")
        
        print("  ✅ Monitoring functions working")
        test_results['monitoring'] = True
        
        conn.close()
    except Exception as e:
        print(f"  ❌ Monitoring system failed: {e}")
        test_results['monitoring'] = False
    
    # Test 6: Data Access
    print("\n📋 Test 6: Data Access")
    try:
        db_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Check existing data
        cursor.execute("SELECT COUNT(*) FROM congress_bills")
        bills_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM congress_members")
        members_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM ingestion_jobs")
        jobs_count = cursor.fetchone()[0]
        
        print(f"  ✅ Data accessible: {bills_count} bills, {members_count} members, {jobs_count} jobs")
        test_results['data_access'] = True
        
        conn.close()
    except Exception as e:
        print(f"  ❌ Data access failed: {e}")
        test_results['data_access'] = False
    
    # Test 7: Ingestion Scripts
    print("\n📜 Test 7: Ingestion Scripts")
    try:
        scripts_dir = "/home/cbwinslow/opendiscourse/mcp_server/scripts"
        if os.path.exists(scripts_dir):
            scripts = [f for f in os.listdir(scripts_dir) if f.endswith('.py')]
            print(f"  ✅ Found {len(scripts)} ingestion scripts")
            test_results['scripts'] = True
        else:
            print("  ❌ Scripts directory not found")
            test_results['scripts'] = False
    except Exception as e:
        print(f"  ❌ Script check failed: {e}")
        test_results['scripts'] = False
    
    # Results Summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST RESULTS:")
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:15}: {status}")
        if result:
            passed_tests += 1
    
    success_rate = (passed_tests / total_tests) * 100
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"  Tests Passed: {passed_tests}/{total_tests}")
    print(f"  Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 85:
        print(f"  🎉 EXCELLENT - System ready for production!")
        return 0
    elif success_rate >= 70:
        print(f"  ⚠️  GOOD - System mostly functional")
        return 0
    else:
        print(f"  ❌ NEEDS WORK - Multiple issues found")
        return 1

if __name__ == "__main__":
    sys.exit(test_comprehensive_functionality())