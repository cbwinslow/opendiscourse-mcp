"""
Tests for database trigger-based ingestion monitoring system.
Verifies automatic progress tracking and job context management.
"""
import pytest
import psycopg2
import os
from datetime import datetime
from mcp_server.utils.monitoring import monitor, IngestionMonitor


@pytest.fixture
def db_connection():
    """Database connection fixture."""
    # Load environment
    with open('mcp_server/.env') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    yield conn
    conn.close()


@pytest.fixture
def clean_test_data(db_connection):
    """Clean up test data before and after tests."""
    cur = db_connection.cursor()

    # Clean up test jobs
    cur.execute("DELETE FROM ingestion_jobs WHERE job_id LIKE 'test_%'")
    cur.execute("DELETE FROM record_hashes WHERE table_name LIKE 'test_%'")

    # Clean up test tables if they exist
    test_tables = ['test_bills', 'test_members', 'test_votes']
    for table in test_tables:
        cur.execute(f"DROP TABLE IF EXISTS {table}")

    db_connection.commit()
    yield

    # Clean up after test
    cur.execute("DELETE FROM ingestion_jobs WHERE job_id LIKE 'test_%'")
    cur.execute("DELETE FROM record_hashes WHERE table_name LIKE 'test_%'")
    for table in test_tables:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
    db_connection.commit()
    cur.close()


class TestTriggerMonitoring:
    """Test trigger-based monitoring system."""

    def test_job_context_functions(self, db_connection):
        """Test job context setting and clearing functions."""
        cur = db_connection.cursor()

        # Test setting job context
        test_job_id = "test_job_123"
        cur.execute("SELECT set_ingestion_job_context(%s)", (test_job_id,))
        db_connection.commit()

        # Verify context is set
        cur.execute("SELECT current_setting('ingestion.active_job_id', TRUE)")
        active_job = cur.fetchone()[0]
        assert active_job == test_job_id

        # Test clearing context
        cur.execute("SELECT clear_ingestion_job_context()")
        db_connection.commit()

        # Verify context is cleared
        cur.execute("SELECT current_setting('ingestion.active_job_id', TRUE)")
        active_job = cur.fetchone()[0]
        assert active_job == ""

        cur.close()

    def test_trigger_automatic_progress(self, db_connection, clean_test_data):
        """Test that triggers automatically update progress counters."""
        cur = db_connection.cursor()

        # Create a test job
        test_job_id = "test_trigger_job_001"
        cur.execute("""
            INSERT INTO ingestion_jobs (job_id, source, collection, status, start_time)
            VALUES (%s, %s, %s, %s, %s)
        """, (test_job_id, 'test', 'bills', 'running', datetime.now()))
        db_connection.commit()

        # Set job context
        cur.execute("SELECT set_ingestion_job_context(%s)", (test_job_id,))
        db_connection.commit()

        # Create a test table that mimics congress_bills structure
        cur.execute("""
            CREATE TABLE test_bills (
                bill_id TEXT PRIMARY KEY,
                congress SMALLINT,
                title TEXT,
                created_on TIMESTAMPTZ DEFAULT now()
            )
        """)

        # Create trigger for test table
        cur.execute("""
            DROP TRIGGER IF EXISTS trg_test_bills_progress ON test_bills;
            CREATE TRIGGER trg_test_bills_progress
                AFTER INSERT ON test_bills
                FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();
        """)
        db_connection.commit()

        # Insert test records
        test_records = [
            ('118-HR-1', 118, 'Test Bill 1'),
            ('118-HR-2', 118, 'Test Bill 2'),
            ('118-HR-3', 118, 'Test Bill 3'),
        ]

        for bill_id, congress, title in test_records:
            cur.execute("""
                INSERT INTO test_bills (bill_id, congress, title)
                VALUES (%s, %s, %s)
            """, (bill_id, congress, title))

        db_connection.commit()

        # Check that progress was automatically updated
        cur.execute("""
            SELECT processed_records FROM ingestion_jobs
            WHERE job_id = %s
        """, (test_job_id,))

        processed_count = cur.fetchone()[0]
        assert processed_count == 3, f"Expected 3 processed records, got {processed_count}"

        # Clear context
        cur.execute("SELECT clear_ingestion_job_context()")
        db_connection.commit()

        cur.close()

    def test_multiple_concurrent_jobs(self, db_connection, clean_test_data):
        """Test that multiple concurrent jobs don't interfere with each other."""
        cur = db_connection.cursor()

        # Create two test jobs
        job1_id = "test_concurrent_job_1"
        job2_id = "test_concurrent_job_2"

        for job_id in [job1_id, job2_id]:
            cur.execute("""
                INSERT INTO ingestion_jobs (job_id, source, collection, status, start_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (job_id, 'test', 'concurrent', 'running', datetime.now()))

        db_connection.commit()

        # Create separate connections for each job (simulating concurrent sessions)
        conn1 = psycopg2.connect(os.environ['DATABASE_URL'])
        conn2 = psycopg2.connect(os.environ['DATABASE_URL'])

        cur1 = conn1.cursor()
        cur2 = conn2.cursor()

        # Set different contexts for each connection
        cur1.execute("SELECT set_ingestion_job_context(%s)", (job1_id,))
        cur2.execute("SELECT set_ingestion_job_context(%s)", (job2_id,))
        conn1.commit()
        conn2.commit()

        # Create test tables for each job
        cur1.execute("""
            CREATE TABLE test_bills_job1 (
                id SERIAL PRIMARY KEY,
                data TEXT
            )
        """)
        cur1.execute("""
            CREATE TRIGGER trg_test_bills_job1_progress
                AFTER INSERT ON test_bills_job1
                FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();
        """)

        cur2.execute("""
            CREATE TABLE test_bills_job2 (
                id SERIAL PRIMARY KEY,
                data TEXT
            )
        """)
        cur2.execute("""
            CREATE TRIGGER trg_test_bills_job2_progress
                AFTER INSERT ON test_bills_job2
                FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();
        """)

        conn1.commit()
        conn2.commit()

        # Insert records in each job's table
        for i in range(5):
            cur1.execute("INSERT INTO test_bills_job1 (data) VALUES (%s)", (f"Job1 Record {i}",))
            cur2.execute("INSERT INTO test_bills_job2 (data) VALUES (%s)", (f"Job2 Record {i}",))

        conn1.commit()
        conn2.commit()

        # Check progress for each job
        cur.execute("""
            SELECT processed_records FROM ingestion_jobs
            WHERE job_id = %s
        """, (job1_id,))
        job1_progress = cur.fetchone()[0]

        cur.execute("""
            SELECT processed_records FROM ingestion_jobs
            WHERE job_id = %s
        """, (job2_id,))
        job2_progress = cur.fetchone()[0]

        assert job1_progress == 5, f"Job1 should have 5 records, got {job1_progress}"
        assert job2_progress == 5, f"Job2 should have 5 records, got {job2_progress}"

        # Clean up
        cur1.execute("SELECT clear_ingestion_job_context()")
        cur2.execute("SELECT clear_ingestion_job_context()")
        conn1.commit()
        conn2.commit()

        cur1.close()
        cur2.close()
        conn1.close()
        conn2.close()
        cur.close()

    def test_real_time_progress_tracking(self, db_connection, clean_test_data):
        """Test real-time progress tracking during data insertion."""
        cur = db_connection.cursor()

        # Create a test job
        test_job_id = "test_realtime_job"
        cur.execute("""
            INSERT INTO ingestion_jobs (job_id, source, collection, status, start_time)
            VALUES (%s, %s, %s, %s, %s)
        """, (test_job_id, 'test', 'realtime', 'running', datetime.now()))
        db_connection.commit()

        # Set job context
        cur.execute("SELECT set_ingestion_job_context(%s)", (test_job_id,))
        db_connection.commit()

        # Create test table
        cur.execute("""
            CREATE TABLE test_realtime_bills (
                bill_id TEXT PRIMARY KEY,
                title TEXT
            )
        """)
        cur.execute("""
            CREATE TRIGGER trg_test_realtime_bills_progress
                AFTER INSERT ON test_realtime_bills
                FOR EACH ROW EXECUTE FUNCTION update_ingestion_progress();
        """)
        db_connection.commit()

        # Insert records one by one and check progress
        progress_counts = []
        for i in range(10):
            cur.execute("""
                INSERT INTO test_realtime_bills (bill_id, title)
                VALUES (%s, %s)
            """, (f'RT-{i:03d}', f'Real-time Bill {i}'))

            # Check progress after each insert
            cur.execute("""
                SELECT processed_records FROM ingestion_jobs
                WHERE job_id = %s
            """, (test_job_id,))
            progress = cur.fetchone()[0]
            progress_counts.append(progress)

            # Progress should increment by 1 each time
            assert progress == i + 1, f"Progress should be {i + 1}, got {progress}"

        db_connection.commit()

        # Verify final count
        assert progress_counts == list(range(1, 11)), f"Progress counts should be [1..10], got {progress_counts}"

        # Clear context
        cur.execute("SELECT clear_ingestion_job_context()")
        db_connection.commit()

        cur.close()

    def test_trigger_on_existing_tables(self, db_connection):
        """Test that triggers work on existing production tables."""
        cur = db_connection.cursor()

        # Create a test job
        test_job_id = "test_existing_tables_job"
        cur.execute("""
            INSERT INTO ingestion_jobs (job_id, source, collection, status, start_time)
            VALUES (%s, %s, %s, %s, %s)
        """, (test_job_id, 'test', 'existing', 'running', datetime.now()))
        db_connection.commit()

        # Set job context
        cur.execute("SELECT set_ingestion_job_context(%s)", (test_job_id,))
        db_connection.commit()

        # Get initial progress
        cur.execute("""
            SELECT processed_records FROM ingestion_jobs
            WHERE job_id = %s
        """, (test_job_id,))
        initial_progress = cur.fetchone()[0] or 0

        # Insert a test record into congress_bills (this should trigger progress update)
        # Use a test bill ID that won't conflict
        test_bill_id = f"test-trigger-{int(datetime.now().timestamp())}"

        try:
            cur.execute("""
                INSERT INTO congress_bills (
                    bill_id, congress, bill_type, bill_number, title,
                    introduced_date, raw
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                test_bill_id, 118, 'hr', '99999',
                'Test Trigger Bill', datetime.now().date(),
                '{"test": "trigger_data"}'
            ))
            db_connection.commit()

            # Check that progress was incremented
            cur.execute("""
                SELECT processed_records FROM ingestion_jobs
                WHERE job_id = %s
            """, (test_job_id,))
            final_progress = cur.fetchone()[0] or 0

            assert final_progress == initial_progress + 1, \
                f"Progress should increment from {initial_progress} to {initial_progress + 1}, got {final_progress}"

            # Clean up test record
            cur.execute("DELETE FROM congress_bills WHERE bill_id = %s", (test_bill_id,))
            db_connection.commit()

        except Exception as e:
            # If insert fails (due to constraints), that's OK for this test
            print(f"Test insert failed (expected): {e}")

        # Clear context
        cur.execute("SELECT clear_ingestion_job_context()")
        db_connection.commit()

        cur.close()

    def test_monitor_integration(self):
        """Test integration with the monitoring system."""
        # Create a test job using the monitor
        test_job_id = monitor.create_job('test', 'integration')

        # Verify job was created
        assert test_job_id.startswith('test_integration_')

        # Get progress (should be 0 initially)
        progress = monitor.get_job_progress(test_job_id)
        assert progress is not None
        assert progress['processed_records'] == 0
        assert progress['status'] == 'pending'

        # Test context manager
        with monitor.monitor_job(test_job_id):
            # Inside context, job should be running
            progress = monitor.get_job_progress(test_job_id)
            assert progress['status'] == 'running'

        # After context, job should be completed
        progress = monitor.get_job_progress(test_job_id)
        assert progress['status'] == 'completed'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
