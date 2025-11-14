"""
Monitoring utilities for data ingestion processes.
Provides remote monitoring, progress tracking, and deduplication.
"""
import os
import json
import hashlib
import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager, asynccontextmanager
import psycopg2
from psycopg2.extras import Json
from psycopg2 import pool
import threading
from collections import defaultdict

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

    def __init__(self, db_url: Optional[str] = None, pool_size: int = 5):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.jobs: Dict[str, IngestionJob] = {}
        self._connection_pool = None
        self._pool_size = pool_size
        self._batch_updates = defaultdict(dict)  # job_id -> updates
        self._batch_lock = threading.Lock()
        self._last_batch_time = time.time()
        self._batch_interval = 5.0  # Batch updates every 5 seconds
        self._batch_thread = None
        self._shutdown = False
        
        if self.db_url:
            self._init_connection_pool()
            self._start_batch_thread()

    def _init_connection_pool(self):
        """Initialize connection pool for better performance."""
        try:
            self._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self._pool_size,
                dsn=self.db_url
            )
            logger.debug(f"Initialized connection pool with {self._pool_size} connections")
        except Exception as e:
            logger.warning(f"Failed to initialize connection pool: {e}")
            self._connection_pool = None

    def _start_batch_thread(self):
        """Start background thread for batch updates."""
        if self._batch_thread is None:
            self._batch_thread = threading.Thread(target=self._batch_worker, daemon=True)
            self._batch_thread.start()
            logger.debug("Started batch update worker thread")

    def _batch_worker(self):
        """Background worker for batch database updates."""
        while not self._shutdown:
            time.sleep(1.0)  # Check every second
            current_time = time.time()
            
            if current_time - self._last_batch_time >= self._batch_interval:
                self._flush_batch_updates()
                self._last_batch_time = current_time

    def _flush_batch_updates(self):
        """Flush all batched updates to database."""
        if not self._batch_updates or not self._connection_pool:
            return

        with self._batch_lock:
            updates_to_process = dict(self._batch_updates)
            self._batch_updates.clear()

        if not updates_to_process:
            return

        conn = None
        try:
            conn = self._connection_pool.getconn()
            cur = conn.cursor()

            for job_id, updates in updates_to_process.items():
                if updates:
                    # Build dynamic UPDATE query
                    set_clauses = []
                    values = []
                    
                    for field, value in updates.items():
                        if field in ['status', 'end_time', 'total_records', 'processed_records', 'duplicates_found']:
                            set_clauses.append(f"{field} = %s")
                            values.append(value)
                        elif field in ['errors', 'metadata']:
                            set_clauses.append(f"{field} = %s")
                            values.append(Json(value))
                    
                    if set_clauses:
                        set_clauses.append("updated_at = NOW()")
                        values.append(job_id)
                        
                        query = f"""
                            UPDATE ingestion_jobs SET
                                {', '.join(set_clauses)}
                            WHERE job_id = %s
                        """
                        cur.execute(query, values)

            conn.commit()
            logger.debug(f"Flushed batch updates for {len(updates_to_process)} jobs")

        except Exception as e:
            logger.warning(f"Failed to flush batch updates: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self._connection_pool.putconn(conn)

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
        self._save_job_to_db(job)  # Still do this synchronously for job creation
        logger.info(f"Created ingestion job: {job_id}")
        return job_id

    @contextmanager
    def monitor_job(self, job_id: str):
        """Context manager for monitoring a job with automatic trigger-based progress tracking."""
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = 'running'
        self._update_job_in_db(job)
        self._set_job_context(job_id)  # Set session context for triggers
        logger.info(f"Started monitoring job: {job_id}")

        try:
            yield job
        except Exception as e:
            job.status = 'failed'
            job.errors.append(str(e))
            job.end_time = datetime.now()
            self._clear_job_context()  # Clear session context
            self._update_job_in_db(job)
            logger.error(f"Job {job_id} failed: {e}")
            raise
        else:
            job.status = 'completed'
            job.end_time = datetime.now()
            self._clear_job_context()  # Clear session context
            self._update_job_in_db(job)
            logger.info(f"Job {job_id} completed successfully")

    def update_progress(self, job_id: str, processed: int, duplicates: int = 0):
        """Update job progress with batching for performance."""
        job = self.jobs.get(job_id)
        if job:
            job.processed_records = processed
            job.duplicates_found = duplicates
            
            # Batch the update instead of immediate DB write
            if self._connection_pool:
                with self._batch_lock:
                    self._batch_updates[job_id].update({
                        'processed_records': processed,
                        'duplicates_found': duplicates
                    })
            else:
                # Fallback to immediate update if no pool
                self._update_job_in_db(job)

    def _set_job_context(self, job_id: str):
        """Set the active job context for database triggers."""
        if not self._connection_pool:
            return

        conn = None
        try:
            conn = self._connection_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT set_ingestion_job_context(%s)", (job_id,))
            conn.commit()
            logger.debug(f"Set job context: {job_id}")
        except Exception as e:
            logger.warning(f"Failed to set job context: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    def _clear_job_context(self):
        """Clear the active job context."""
        if not self._connection_pool:
            return

        conn = None
        try:
            conn = self._connection_pool.getconn()
            cur = conn.cursor()
            cur.execute("SELECT clear_ingestion_job_context()")
            conn.commit()
            logger.debug("Cleared job context")
        except Exception as e:
            logger.warning(f"Failed to clear job context: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    def get_job_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time job progress from database."""
        if not self._connection_pool:
            return None

        conn = None
        try:
            conn = self._connection_pool.getconn()
            cur = conn.cursor()
            cur.execute("""
                SELECT processed_records, status, updated_at, total_records, duplicates_found
                FROM ingestion_jobs
                WHERE job_id = %s
            """, (job_id,))
            row = cur.fetchone()

            if row:
                processed, status, updated_at, total, duplicates = row
                return {
                    'job_id': job_id,
                    'processed_records': processed or 0,
                    'status': status,
                    'total_records': total or 0,
                    'duplicates_found': duplicates or 0,
                    'last_updated': updated_at.isoformat() if updated_at else None
                }
        except Exception as e:
            logger.warning(f"Failed to get job progress: {e}")
        finally:
            if conn:
                self._connection_pool.putconn(conn)

        return None

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
        """Save job to database using connection pool."""
        if not self._connection_pool:
            return

        conn = None
        try:
            conn = self._connection_pool.getconn()
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

        except Exception as e:
            logger.warning(f"Failed to save job to database: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    def _update_job_in_db(self, job: IngestionJob):
        """Update job in database using connection pool."""
        if not self._connection_pool:
            return

        conn = None
        try:
            conn = self._connection_pool.getconn()
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

        except Exception as e:
            logger.warning(f"Failed to update job in database: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    def force_update_job(self, job_id: str):
        """Force immediate update of job from batched changes."""
        if job_id in self._batch_updates:
            with self._batch_lock:
                updates = self._batch_updates.pop(job_id, {})
            
            if updates and self._connection_pool:
                conn = None
                try:
                    conn = self._connection_pool.getconn()
                    cur = conn.cursor()
                    
                    set_clauses = []
                    values = []
                    
                    for field, value in updates.items():
                        if field in ['status', 'end_time', 'total_records', 'processed_records', 'duplicates_found']:
                            set_clauses.append(f"{field} = %s")
                            values.append(value)
                        elif field in ['errors', 'metadata']:
                            set_clauses.append(f"{field} = %s")
                            values.append(Json(value))
                    
                    if set_clauses:
                        set_clauses.append("updated_at = NOW()")
                        values.append(job_id)
                        
                        query = f"""
                            UPDATE ingestion_jobs SET
                                {', '.join(set_clauses)}
                            WHERE job_id = %s
                        """
                        cur.execute(query, values)
                        conn.commit()
                        logger.debug(f"Force updated job {job_id}")
                        
                except Exception as e:
                    logger.warning(f"Failed to force update job {job_id}: {e}")
                    if conn:
                        conn.rollback()
                finally:
                    if conn:
                        self._connection_pool.putconn(conn)

    def shutdown(self):
        """Cleanup resources and flush remaining updates."""
        logger.info("Shutting down monitoring system...")
        self._shutdown = True
        
        # Flush any remaining batched updates
        self._flush_batch_updates()
        
        # Close connection pool
        if self._connection_pool:
            self._connection_pool.closeall()
            logger.debug("Closed connection pool")
        
        # Wait for batch thread to finish
        if self._batch_thread and self._batch_thread.is_alive():
            self._batch_thread.join(timeout=5.0)
            logger.debug("Batch thread stopped")

class DeduplicationManager:
    """Manages deduplication of records using content hashing with caching and batching."""

    def __init__(self, db_url: Optional[str] = None, cache_size: int = 10000):
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self._hash_cache = {}  # In-memory cache for recent hashes
        self._cache_size = cache_size
        self._batch_operations = []  # Batch operations for later processing
        self._batch_lock = threading.Lock()
        self._last_batch_time = time.time()
        self._batch_interval = 10.0  # Batch every 10 seconds
        self._batch_thread = None
        self._shutdown = False
        
        # Start batch processing thread
        self._start_batch_thread()

    def _start_batch_thread(self):
        """Start background thread for batch deduplication operations."""
        if self._batch_thread is None:
            self._batch_thread = threading.Thread(target=self._batch_worker, daemon=True)
            self._batch_thread.start()
            logger.debug("Started deduplication batch worker thread")

    def _batch_worker(self):
        """Background worker for batch deduplication operations."""
        while not self._shutdown:
            time.sleep(2.0)  # Check every 2 seconds
            current_time = time.time()
            
            if current_time - self._last_batch_time >= self._batch_interval:
                self._process_batch_operations()
                self._last_batch_time = current_time

    def _process_batch_operations(self):
        """Process batched deduplication operations."""
        if not self._batch_operations:
            return

        with self._batch_lock:
            operations_to_process = list(self._batch_operations)
            self._batch_operations.clear()

        if not operations_to_process:
            return

        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            # Create table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS record_hashes (
                    table_name TEXT NOT NULL,
                    record_id TEXT,
                    content_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(table_name, content_hash)
                )
            """)

            # Batch insert new hashes
            insert_data = []
            for op_type, table, record_id, content_hash in operations_to_process:
                if op_type == 'insert' and content_hash not in self._hash_cache:
                    insert_data.append((table, record_id, content_hash))

            if insert_data:
                cur.executemany("""
                    INSERT INTO record_hashes (table_name, record_id, content_hash)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (table_name, content_hash) DO NOTHING
                """, insert_data)

            conn.commit()
            logger.debug(f"Processed {len(insert_data)} batch deduplication operations")

        except Exception as e:
            logger.warning(f"Failed to process batch deduplication operations: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                cur.close()
                conn.close()

    def get_content_hash(self, data: Dict[str, Any], exclude_fields: List[str] = None) -> str:
        """Generate a content hash for deduplication with optimizations."""
        if exclude_fields:
            data = {k: v for k, v in data.items() if k not in exclude_fields}

        # Use more efficient JSON serialization
        content_str = json.dumps(data, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _add_to_cache(self, content_hash: str, is_duplicate: bool):
        """Add hash to cache with LRU eviction."""
        if len(self._hash_cache) >= self._cache_size:
            # Remove oldest entries (simple LRU)
            oldest_keys = list(self._hash_cache.keys())[:self._cache_size // 4]
            for key in oldest_keys:
                del self._hash_cache[key]
        
        self._hash_cache[content_hash] = is_duplicate

    def is_duplicate(self, table: str, content_hash: str, record_id: str = None) -> bool:
        """Check if a record is a duplicate with caching and batching."""
        # Check cache first
        if content_hash in self._hash_cache:
            return self._hash_cache[content_hash]

        if not self.db_url:
            return False

        conn = None
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

            # Cache the result
            self._add_to_cache(content_hash, exists)

            if not exists:
                # Batch the insert operation instead of immediate insert
                with self._batch_lock:
                    self._batch_operations.append(('insert', table, record_id, content_hash))

            conn.commit()
            return exists

        except Exception as e:
            logger.warning(f"Failed to check deduplication: {e}")
            return False
        finally:
            if conn:
                cur.close()
                conn.close()

    def batch_check_duplicates(self, records: List[tuple]) -> Dict[str, bool]:
        """Check multiple records for duplicates in batch for better performance.
        
        Args:
            records: List of (table, content_hash, record_id) tuples
            
        Returns:
            Dict mapping content_hash to is_duplicate boolean
        """
        results = {}
        uncached_records = []

        # Check cache first
        for table, content_hash, record_id in records:
            if content_hash in self._hash_cache:
                results[content_hash] = self._hash_cache[content_hash]
            else:
                uncached_records.append((table, content_hash, record_id))

        if not uncached_records:
            return results

        # Batch check uncached records
        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            # Create table if needed
            cur.execute("""
                CREATE TABLE IF NOT EXISTS record_hashes (
                    table_name TEXT NOT NULL,
                    record_id TEXT,
                    content_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(table_name, content_hash)
                )
            """)

            # Batch query
            for table, content_hash, record_id in uncached_records:
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
                results[content_hash] = exists
                self._add_to_cache(content_hash, exists)

                if not exists:
                    with self._batch_lock:
                        self._batch_operations.append(('insert', table, record_id, content_hash))

            conn.commit()

        except Exception as e:
            logger.warning(f"Failed to batch check duplicates: {e}")
        finally:
            if conn:
                cur.close()
                conn.close()

        return results

    def force_process_batch(self):
        """Force immediate processing of batched operations."""
        self._process_batch_operations()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            'cache_size': len(self._hash_cache),
            'max_cache_size': self._cache_size,
            'batch_operations_pending': len(self._batch_operations),
            'cache_hit_ratio': getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_checks', 1), 1)
        }

    def shutdown(self):
        """Cleanup deduplication resources."""
        logger.info("Shutting down deduplication manager...")
        self._shutdown = True
        
        # Process remaining batch operations
        self._process_batch_operations()
        
        # Wait for batch thread to finish
        if self._batch_thread and self._batch_thread.is_alive():
            self._batch_thread.join(timeout=5.0)
            logger.debug("Deduplication batch thread stopped")

    def cleanup_old_hashes(self, days: int = 30):
        """Clean up old hash records."""
        if not self.db_url:
            return

        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cur = conn.cursor()

            cur.execute("""
                DELETE FROM record_hashes
                WHERE created_at < NOW() - INTERVAL '%s days'
            """, (days,))

            deleted_count = cur.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old hash records")

        except Exception as e:
            logger.warning(f"Failed to cleanup old hashes: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                cur.close()
                conn.close()

# Global instances - lazy loaded to ensure environment is available
_monitor = None
_deduplicator = None

def _get_monitor():
    global _monitor
    if _monitor is None:
        _monitor = IngestionMonitor()
    return _monitor

def _get_deduplicator():
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = DeduplicationManager()
    return _deduplicator

# For backward compatibility, create proxy objects that lazy-load
class LazyMonitor:
    def __getattr__(self, name):
        return getattr(_get_monitor(), name)

class LazyDeduplicator:
    def __getattr__(self, name):
        return getattr(_get_deduplicator(), name)

monitor = LazyMonitor()
deduplicator = LazyDeduplicator()

# Cleanup function for graceful shutdown
import atexit
def cleanup_monitoring():
    """Cleanup monitoring resources on exit."""
    if _monitor is not None:
        _monitor.shutdown()
    if _deduplicator is not None:
        _deduplicator.shutdown()

atexit.register(cleanup_monitoring)
