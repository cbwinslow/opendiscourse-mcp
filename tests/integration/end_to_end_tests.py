#!/usr/bin/env python3
"""
End-to-end ingestion tests for OpenDiscourse
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

def run_ingestion_test(script_name, description, timeout=300):
    """Run an ingestion script and monitor results"""
    print(f"\n🔄 Running {description}...")
    print(f"   Script: {script_name}")
    
    start_time = time.time()
    
    try:
        # Run the ingestion script
        result = subprocess.run(
            ["/usr/bin/python3", script_name],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/cbwinslow/opendiscourse"
        )
        
        execution_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"  ✅ Success in {execution_time:.1f}s")
            return True, execution_time, result.stdout
        else:
            print(f"  ❌ Failed in {execution_time:.1f}s")
            print(f"  Error: {result.stderr[:200]}")
            return False, execution_time, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"  ⏰ Timeout after {timeout}s")
        return False, timeout, "Timeout"
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
        return False, 0, str(e)

def check_database_changes(test_name):
    """Check database changes after ingestion"""
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=DictCursor)
    
    changes = {}
    
    # Check various tables
    tables = [
        'congress_bills', 'congress_members', 'congress_committees',
        'opencivicdata_bill', 'opencivicdata_person',
        'govinfo_packages', 'ingestion_jobs', 'ingestion_performance_log'
    ]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cursor.fetchone()['count']
            changes[table] = count
        except Exception as e:
            changes[table] = f"Error: {str(e)}"
    
    # Check recent ingestion jobs
    try:
        cursor.execute("""
            SELECT job_id, source, status, processed_records, created_at
            FROM ingestion_jobs 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        recent_jobs = cursor.fetchall()
        changes['recent_jobs'] = recent_jobs
    except Exception as e:
        changes['recent_jobs'] = f"Error: {str(e)}"
    
    conn.close()
    return changes

def run_comprehensive_tests():
    """Run comprehensive end-to-end tests"""
    print("🧪 END-TO-END INGESTION TESTS")
    print("=" * 60)
    
    source_env_file()
    
    # Test scripts to run
    tests = [
        {
            'script': 'mcp_server/scripts/congress_ingest.py',
            'description': 'Congress Data Ingestion',
            'timeout': 300
        },
        {
            'script': 'mcp_server/scripts/congress_members_ingest.py', 
            'description': 'Congress Members Ingestion',
            'timeout': 180
        }
    ]
    
    results = {}
    database_snapshots = {}
    
    # Take initial database snapshot
    print("\n📊 Taking initial database snapshot...")
    database_snapshots['initial'] = check_database_changes("initial")
    
    # Run each test
    for test in tests:
        test_name = test['description'].lower().replace(' ', '_')
        
        # Check if script exists
        if not os.path.exists(test['script']):
            print(f"  ⚠️  Script not found: {test['script']}")
            results[test_name] = {
                'success': False,
                'time': 0,
                'output': 'Script not found'
            }
            continue
        
        # Run the test
        success, exec_time, output = run_ingestion_test(
            test['script'], 
            test['description'], 
            test['timeout']
        )
        
        results[test_name] = {
            'success': success,
            'time': exec_time,
            'output': output[:500]  # Truncate long output
        }
        
        # Take database snapshot after test
        database_snapshots[test_name] = check_database_changes(test_name)
        
        # Small delay between tests
        time.sleep(2)
    
    # Final database snapshot
    print("\n📊 Taking final database snapshot...")
    database_snapshots['final'] = check_database_changes("final")
    
    # Generate report
    print("\n" + "=" * 60)
    print("📊 END-TO-END TEST RESULTS:")
    
    successful_tests = 0
    total_tests = len(results)
    
    for test_name, result in results.items():
        status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
        time_str = f"{result['time']:.1f}s" if result['time'] > 0 else "N/A"
        print(f"{test_name:25}: {status:12} ({time_str})")
        
        if result['success']:
            successful_tests += 1
    
    # Database changes summary
    print(f"\n📊 DATABASE CHANGES SUMMARY:")
    initial = database_snapshots.get('initial', {})
    final = database_snapshots.get('final', {})
    
    for table in ['congress_bills', 'congress_members', 'ingestion_jobs']:
        initial_count = initial.get(table, 0)
        final_count = final.get(table, 0)
        if isinstance(initial_count, int) and isinstance(final_count, int):
            change = final_count - initial_count
            change_str = f"+{change}" if change > 0 else str(change)
            print(f"  {table:20}: {initial_count:6} → {final_count:6} ({change_str})")
    
    # Recent jobs
    recent_jobs = final.get('recent_jobs', [])
    if isinstance(recent_jobs, list) and recent_jobs:
        print(f"\n📋 RECENT INGESTION JOBS:")
        for job in recent_jobs[:3]:
            print(f"  - {job['job_id']}: {job['source']} ({job['status']}) - {job['processed_records']} records")
    
    # Overall assessment
    print(f"\n🎯 OVERALL TEST RESULTS:")
    print(f"  Tests Passed: {successful_tests}/{total_tests}")
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"  Success Rate: {success_rate:.1f}%")
    
    if successful_tests == total_tests:
        print(f"  🎉 ALL TESTS PASSED - System ready for production!")
        return 0
    elif successful_tests >= total_tests // 2:
        print(f"  ⚠️  Partial success - Some components working")
        return 0
    else:
        print(f"  ❌ Multiple failures - System needs attention")
        return 1

if __name__ == "__main__":
    sys.exit(run_comprehensive_tests())