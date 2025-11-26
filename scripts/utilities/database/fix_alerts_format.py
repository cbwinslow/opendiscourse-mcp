#!/usr/bin/env python3
"""
Fix get_ingestion_alerts function format issue
"""

import os
import psycopg2

def fix_alerts_function_format():
    """Fix format specifier issue in get_ingestion_alerts"""
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    print("🔧 Fixing get_ingestion_alerts function format issue...")
    
    cursor.execute("""
        CREATE OR REPLACE FUNCTION get_ingestion_alerts()
        RETURNS TABLE (
            alert_type TEXT,
            severity TEXT,
            message TEXT,
            details JSONB
        ) AS $$
        BEGIN
            -- Slow running jobs alert
            RETURN QUERY
            SELECT 
                'slow_job'::TEXT,
                'WARNING'::TEXT,
                format('Job %s has been running for %s minutes', 
                       ij.job_id, 
                       EXTRACT(EPOCH FROM (NOW() - ij.start_time))/60)::TEXT,
                jsonb_build_object(
                    'job_id', ij.job_id,
                    'running_minutes', EXTRACT(EPOCH FROM (NOW() - ij.start_time))/60,
                    'processed_records', ij.processed_records
                )
            FROM ingestion_jobs ij
            WHERE ij.status = 'running' 
            AND ij.start_time < NOW() - INTERVAL '30 minutes';
            
            -- High error rate alert (fixed format)
            RETURN QUERY
            SELECT 
                'high_error_rate'::TEXT,
                'CRITICAL'::TEXT,
                'Error rate is ' || ROUND(error_rate, 2) || '% in the last hour',
                jsonb_build_object(
                    'error_rate', error_rate,
                    'total_jobs', job_count,
                    'failed_jobs', failed_count
                )
            FROM (
                SELECT 
                    COUNT(*) as job_count,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_count,
                    CASE 
                        WHEN COUNT(*) > 0 THEN (COUNT(CASE WHEN status = 'failed' THEN 1 END) * 100.0 / COUNT(*))
                        ELSE 0 
                    END as error_rate
                FROM ingestion_jobs 
                WHERE created_at > NOW() - INTERVAL '1 hour'
            ) sub
            WHERE job_count > 0 AND error_rate > 10;
            
            -- Data quality issues alert (fixed format)
            RETURN QUERY
            SELECT 
                'data_quality_issues'::TEXT,
                'WARNING'::TEXT,
                'Data quality pass rate is ' || ROUND(pass_rate, 2) || '% for table ' || table_name,
                jsonb_build_object(
                    'table_name', table_name,
                    'pass_rate', pass_rate,
                    'failed_checks', failed_checks
                )
            FROM (
                SELECT 
                    table_name,
                    COUNT(*) as total_checks,
                    COUNT(CASE WHEN status = 'PASS' THEN 1 END) as passed_checks,
                    COUNT(CASE WHEN status = 'FAIL' THEN 1 END) as failed_checks,
                    CASE 
                        WHEN COUNT(*) > 0 THEN (COUNT(CASE WHEN status = 'PASS' THEN 1 END) * 100.0 / COUNT(*))
                        ELSE 100 
                    END as pass_rate
                FROM data_quality_monitoring 
                WHERE timestamp > NOW() - INTERVAL '24 hours'
                GROUP BY table_name
            ) sub
            WHERE total_checks > 0 AND pass_rate < 95;
            
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    conn.commit()
    print("✅ get_ingestion_alerts function format fixed!")
    
    # Test the function
    try:
        cursor.execute("SELECT * FROM get_ingestion_alerts()")
        alerts = cursor.fetchall()
        print(f"✅ get_ingestion_alerts working: {len(alerts)} alerts")
    except Exception as e:
        print(f"❌ get_ingestion_alerts test failed: {e}")
    
    conn.close()

if __name__ == "__main__":
    fix_alerts_function_format()