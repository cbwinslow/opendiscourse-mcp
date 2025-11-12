"""
Monitoring utilities for data ingestion processes.
Provides remote monitoring, progress tracking, and deduplication.
"""
import os
import json
import hashlib
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import Json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class IngestionJob:
    """Represents an ingestion job with monitoring data."""
    job_id: str
    source: str  # congress, openstates, govinfo
    collection: str
    status: str  # pending, running, completed, failed
    start_time: datetime
    end_time: Optional[datetime] = None
    total_records: int = 0
    processed_records: int = 0
    duplicates_found: int = 0
    errors: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        if isinstance(data['start_time'], datetime):
            data['start_time'] = data['start_time'].isoformat()
        if data['end_time'] and isinstance(data['end_time'], datetime):
            data['end_time'] = data['end_time'].isoformat()
        return data

class IngestionMonitor:
    """Monitors data ingestion processes with remote access capabilities."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.jobs: Dict[str, IngestionJob] = {}

    def create_job(self, source: str, collection: str, **metadata) -> str:
        """Create a new ingestion job."""
        job_id = f"{source}_{collection}_{int(time.time())}"
        job = IngestionJob(
            job_id=job_id,
            source=source,
            collection=collection,
            status='pending',
            start_time=datetime.now(),
            metadata=metadata
        )
        self.jobs[job_id] = job
        self._save_job_to_db(job)
        logger.info(f"Created ingestion job: {job_id}")
        return job_id

    @contextmanager
    def monitor_job(self, job_id: str):
        """Context manager for monitoring a job."""
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = 'running'
        self._update_job_in_db(job)
        logger.info(f"Started monitoring job: {job_id}")

        try:
            yield job
        except Exception as e:
            job.status = 'failed'
            job.errors.append(str(e))
            job.end_time = datetime.now()
            self._update_job_in_db(job)
            logger.error(f"Job {job_id} failed: {e}")
            raise
        else:
            job.status = 'completed'
            job.end_time = datetime.now()
            self._update_job_in_db(job)
            logger.info(f"Job {job_id} completed successfully")

    def update_progress(self, job_id: str, processed: int, duplicates: int = 0):
        """Update job progress."""
        job = self.jobs.get(job_id)
        if job:
            job.processed_records = processed
            job.duplicates_found = duplicates
            self._update_job_in_db(job)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        job = self.jobs.get(job_id)
        return job.to_dict() if job else None

    def get_all_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all jobs, optionally filtered by status."""
        jobs = list(self.jobs.values())
        if status:
            jobs = [j for j in jobs if j.status == status]
        return [job.to_dict() for job in jobs]

    def _save_job_to_db(self, job: IngestionJob):
        """Save job to database."""
        if not self.db_url:
            return

        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            # Create table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    job_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    total_records INTEGER DEFAULT 0,
                    processed_records INTEGER DEFAULT 0,
                    duplicates_found INTEGER DEFAULT 0,
                    errors JSONB DEFAULT '[]'::jsonb,
                    metadata JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Insert job
            cur.execute("""
                INSERT INTO ingestion_jobs
                (job_id, source, collection, status, start_time, end_time,
                 total_records, processed_records, duplicates_found, errors, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    end_time = EXCLUDED.end_time,
                    total_records = EXCLUDED.total_records,
                    processed_records = EXCLUDED.processed_records,
                    duplicates_found = EXCLUDED.duplicates_found,
                    errors = EXCLUDED.errors,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, (
                job.job_id, job.source, job.collection, job.status,
                job.start_time, job.end_time, job.total_records,
                job.processed_records, job.duplicates_found,
                Json(job.errors), Json(job.metadata)
            ))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            logger.warning(f"Failed to save job to database: {e}")

    def _update_job_in_db(self, job: IngestionJob):
        """Update job in database."""
        if not self.db_url:
            return

        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            cur.execute("""
                UPDATE ingestion_jobs SET
                    status = %s,
                    end_time = %s,
                    total_records = %s,
                    processed_records = %s,
                    duplicates_found = %s,
                    errors = %s,
                    metadata = %s,
                    updated_at = NOW()
                WHERE job_id = %s
            """, (
                job.status, job.end_time, job.total_records,
                job.processed_records, job.duplicates_found,
                Json(job.errors), Json(job.metadata), job.job_id
            ))

            conn.commit()
            cur.close()
            conn.close()

        except Exception as e:
            logger.warning(f"Failed to update job in database: {e}")

class DeduplicationManager:
    """Manages deduplication of records using content hashing."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv('DATABASE_URL')

    def get_content_hash(self, data: Dict[str, Any], exclude_fields: List[str] = None) -> str:
        """Generate a content hash for deduplication."""
        if exclude_fields:
            data = {k: v for k, v in data.items() if k not in exclude_fields}

        # Convert to JSON string and hash
        content_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def is_duplicate(self, table: str, content_hash: str, record_id: str = None) -> bool:
        """Check if a record is a duplicate."""
        if not self.db_url:
            return False

        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            # Create deduplication table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS record_hashes (
                    table_name TEXT NOT NULL,
                    record_id TEXT,
                    content_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(table_name, content_hash)
                )
            """)

            # Check if hash exists
            if record_id:
                cur.execute("""
                    SELECT 1 FROM record_hashes
                    WHERE table_name = %s AND content_hash = %s AND record_id != %s
                """, (table, content_hash, record_id))
            else:
                cur.execute("""
                    SELECT 1 FROM record_hashes
                    WHERE table_name = %s AND content_hash = %s
                """, (table, content_hash))

            exists = cur.fetchone() is not None

            if not exists:
                # Insert hash if it doesn't exist
                cur.execute("""
                    INSERT INTO record_hashes (table_name, record_id, content_hash)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (table_name, content_hash) DO NOTHING
                """, (table, record_id, content_hash))

            conn.commit()
            cur.close()
            conn.close()

            return exists

        except Exception as e:
            logger.warning(f"Failed to check deduplication: {e}")
            return False

    def cleanup_old_hashes(self, days: int = 30):
        """Clean up old hash records."""
        if not self.db_url:
            return

        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            cur.execute("""
                DELETE FROM record_hashes
                WHERE created_at < NOW() - INTERVAL '%s days'
            """, (days,))

            deleted_count = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()

            logger.info(f"Cleaned up {deleted_count} old hash records")

        except Exception as e:
            logger.warning(f"Failed to cleanup old hashes: {e}")

# Global instances
monitor = IngestionMonitor()
deduplicator = DeduplicationManager()
