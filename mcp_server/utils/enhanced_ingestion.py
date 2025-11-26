"""Enhanced ingestion framework with GPU, parallel, and async capabilities."""
import asyncio
import concurrent.futures
import multiprocessing
import os
import hashlib
import json
import logging
import time
import functools
import random
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
import pandas as pd

# Optional imports with fallbacks
try:
    from tqdm.asyncio import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

try:
    import fabric
    from fabric import Connection
    FABRIC_AVAILABLE = True
except ImportError:
    FABRIC_AVAILABLE = False

# GPU Enhancement Disabled - Not useful for web data ingestion
# try:
#     import cudf
#     CUDF_AVAILABLE = True
# except ImportError:
#     CUDF_AVAILABLE = False
CUDF_AVAILABLE = False  # Force disable GPU processing

try:
    import dask
    import dask.dataframe as dd
    from dask.distributed import Client, LocalCluster
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import aiomultiprocess
    AIOMULTIPROCESS_AVAILABLE = True
except ImportError:
    AIOMULTIPROCESS_AVAILABLE = False

try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

try:
    from concurrent_log_handler import ConcurrentRotatingFileHandler
    CONCURRENT_LOG_HANDLER_AVAILABLE = True
except ImportError:
    CONCURRENT_LOG_HANDLER_AVAILABLE = False
    ConcurrentRotatingFileHandler = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== ENHANCED DECORATORS =====

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: tuple = (Exception,)):
    """Retry decorator with exponential backoff for API calls."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            
            raise last_exception
        return wrapper
    return decorator

def cache(ttl_seconds: int = 300, max_size: int = 1000):
    """Simple in-memory cache decorator for API responses."""
    cache_store = {}
    cache_times = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            current_time = time.time()
            
            # Check if cached result exists and is not expired
            if (cache_key in cache_store and 
                cache_key in cache_times and 
                current_time - cache_times[cache_key] < ttl_seconds):
                logger.debug(f"Cache hit for {func.__name__}")
                return cache_store[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            
            # Implement simple LRU eviction if cache is full
            if len(cache_store) >= max_size:
                oldest_key = min(cache_times.keys(), key=lambda k: cache_times[k])
                del cache_store[oldest_key]
                del cache_times[oldest_key]
            
            cache_store[cache_key] = result
            cache_times[cache_key] = current_time
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        return wrapper
    return decorator

def rate_limit(calls_per_second: float = 1.0):
    """Rate limiting decorator for API calls."""
    def decorator(func: Callable) -> Callable:
        last_called = [0.0]  # Use list to make it mutable in nested function
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            min_interval = 1.0 / calls_per_second
            
            time_since_last = current_time - last_called[0]
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                logger.debug(f"Rate limiting {func.__name__}: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)
            
            last_called[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def monitor_performance(func: Callable) -> Callable:
    """Performance monitoring decorator."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = func(*args, **kwargs)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            duration = end_time - start_time
            memory_delta = end_memory - start_memory
            
            logger.info(f"Performance: {func.__name__} took {duration:.2f}s, memory delta: {memory_delta:+.1f}MB")
            return result
            
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error(f"Performance: {func.__name__} failed after {duration:.2f}s: {e}")
            raise
    return wrapper

@dataclass
class IngestionJob:
    """Represents an ingestion job with metadata."""
    job_id: str
    source: str
    collection: str
    parameters: Dict[str, Any]
    status: str = "pending"
    progress: float = 0.0
    total_records: int = 0
    processed_records: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class IngestionConfig:
    """Configuration for enhanced ingestion."""
    use_gpu: bool = False  # Disabled - not useful for web ingestion
    use_parallel: bool = True
    use_async: bool = True
    max_workers: int = None
    batch_size: int = 1000
    chunk_size: int = 10000
    enable_retry: bool = True
    max_retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_caching: bool = True
    cache_ttl: int = 300  # 5 minutes
    rate_limit_calls: float = 10.0  # 10 calls per second
    enable_progress_tracking: bool = True
    enable_deduplication: bool = True
    enable_compression: bool = True
    redis_url: Optional[str] = None
    scheduler_enabled: bool = False
    remote_execution: bool = False
    ssh_config: Optional[Dict[str, Any]] = None

class ProgressTracker:
    """Tracks ingestion progress with Redis backend."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = redis.from_url(redis_url or "redis://localhost:6379") if redis_url else None
        self.local_progress = {}

    def update_progress(self, job_id: str, progress: float, processed: int, total: int):
        """Update progress for a job."""
        data = {
            'progress': progress,
            'processed': processed,
            'total': total,
            'updated_at': datetime.now().isoformat()
        }

        if self.redis_client:
            self.redis_client.hset(f"ingestion:{job_id}", mapping=data)
        else:
            self.local_progress[job_id] = data

    def get_progress(self, job_id: str) -> Dict[str, Any]:
        """Get progress for a job."""
        if self.redis_client:
            return self.redis_client.hgetall(f"ingestion:{job_id}")
        return self.local_progress.get(job_id, {})

class DeduplicationManager:
    """Manages deduplication using hash-based approach."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = redis.from_url(redis_url or "redis://localhost:6379") if redis_url else None
        self.local_hashes = set()

    def get_record_hash(self, record: Dict[str, Any]) -> str:
        """Generate hash for a record."""
        # Create a normalized version for hashing
        normalized = json.dumps(record, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def is_duplicate(self, record: Dict[str, Any], collection: str) -> bool:
        """Check if record is a duplicate."""
        record_hash = self.get_record_hash(record)

        if self.redis_client:
            key = f"dedup:{collection}:{record_hash}"
            return bool(self.redis_client.exists(key))
        else:
            return record_hash in self.local_hashes

    def mark_processed(self, record: Dict[str, Any], collection: str):
        """Mark record as processed."""
        record_hash = self.get_record_hash(record)

        if self.redis_client:
            key = f"dedup:{collection}:{record_hash}"
            self.redis_client.set(key, "1", ex=86400*30)  # Expire after 30 days
        else:
            self.local_hashes.add(record_hash)

# GPU Data Processing Disabled - Not beneficial for web ingestion workloads
# class GPUDataProcessor:
#     """GPU-accelerated data processing using CuDF."""
# 
#     def __init__(self):
#         self.gpu_available = self._check_gpu_availability()
# 
#     def _check_gpu_availability(self) -> bool:
#         """Check if GPU is available."""
#         return CUDF_AVAILABLE
# 
#     def process_dataframe(self, df: pd.DataFrame) -> Union[pd.DataFrame, Any]:
#         """Process dataframe with GPU acceleration if available."""
#         if not self.gpu_available:
#             return df
# 
#         try:
#             import cudf
#             # Convert to CuDF for GPU processing
#             cudf_df = cudf.DataFrame.from_pandas(df)
# 
#             # Perform GPU-accelerated operations here
#             # For example: filtering, sorting, aggregations
#             if 'date' in cudf_df.columns:
#                 cudf_df['date'] = cudf.to_datetime(cudf_df['date'])
# 
#             return cudf_df.to_pandas()
#         except Exception as e:
#             logger.warning(f"GPU processing failed, falling back to CPU: {e}")
#             return df

# Fallback CPU-only processor
class CPUDataProcessor:
    """CPU-only data processing - optimized for web ingestion workloads."""
    
    def __init__(self):
        self.cpu_available = True
    
    @monitor_performance
    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process dataframe with CPU optimization."""
        try:
            # CPU-optimized date processing
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Basic data cleaning and optimization
            return df
        except Exception as e:
            logger.warning(f"CPU processing failed: {e}")
            return df

class ParallelProcessor:
    """Parallel processing manager."""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(32, multiprocessing.cpu_count() * 2)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)

    @monitor_performance
    async def process_batch_async(self, items: List[Any], processor_func: Callable,
                                batch_size: int = 100) -> List[Any]:
        """Process items in parallel batches asynchronously."""
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tasks = []

            for item in batch:
                task = asyncio.get_event_loop().run_in_executor(
                    self.executor, processor_func, item
                )
                tasks.append(task)

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

        return results

    def process_batch_sync(self, items: List[Any], processor_func: Callable,
                          batch_size: int = 100) -> List[Any]:
        """Process items in parallel batches synchronously."""
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                batch_results = list(executor.map(processor_func, batch))
                results.extend(batch_results)

        return results

class AsyncDataLoader:
    """Asynchronous data loading and processing."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        # GPU processing disabled - use CPU processor instead
        self.cpu_processor = CPUDataProcessor()  # Always use CPU for web ingestion
        self.parallel_processor = ParallelProcessor(config.max_workers) if config.use_parallel else None

    async def load_and_process_data(self, data_source: str, processor_func: Callable,
                                  **kwargs) -> List[Dict[str, Any]]:
        """Load and process data asynchronously."""
        # This would be implemented for each specific data source
        # For now, return empty list as placeholder
        return []

class IngestionScheduler:
    """Scheduler for automated ingestion jobs."""

    def __init__(self):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler not available. Install with: pip install apscheduler")
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_jobstore(MemoryJobStore(), "default")
        self.scheduler.add_executor(AsyncIOExecutor())

    def add_cron_job(self, func: Callable, cron_expression: str, job_id: str, **kwargs):
        """Add a cron-scheduled job."""
        trigger = CronTrigger.from_crontab(cron_expression)
        self.scheduler.add_job(func, trigger=trigger, id=job_id, **kwargs)

    def add_interval_job(self, func: Callable, interval_seconds: int, job_id: str, **kwargs):
        """Add an interval-based job."""
        from apscheduler.triggers.interval import IntervalTrigger
        trigger = IntervalTrigger(seconds=interval_seconds)
        self.scheduler.add_job(func, trigger=trigger, id=job_id, **kwargs)

    async def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            self.scheduler.shutdown()

class RemoteExecutor:
    """SSH-based remote execution for database operations."""

    def __init__(self, ssh_config: Dict[str, Any]):
        if not PARAMIKO_AVAILABLE or not FABRIC_AVAILABLE:
            raise ImportError("Paramiko and Fabric required for remote execution. Install with: pip install paramiko fabric")
        self.ssh_config = ssh_config
        self.connection = None

    def connect(self):
        """Establish SSH connection."""
        try:
            from fabric import Config
            config = Config(
                overrides={
                    'connect_kwargs': {
                        'key_filename': self.ssh_config.get('key_file'),
                        'password': self.ssh_config.get('password')
                    }
                }
            )

            self.connection = Connection(
                host=f"{self.ssh_config['user']}@{self.ssh_config['host']}:{self.ssh_config.get('port', 22)}",
                config=config
            )

            # Test connection
            self.connection.run("echo 'Connection test'", hide=True)
        except Exception as e:
            logger.error(f"Failed to connect via SSH: {e}")
            raise

    def execute_db_command(self, command: str, database_url: str) -> str:
        """Execute database command on remote server."""
        if not self.connection:
            self.connect()

        # Set environment variable and execute command
        full_command = f"DATABASE_URL='{database_url}' {command}"
        result = self.connection.run(full_command, hide=True)

        return result.stdout

    async def execute_async_db_command(self, command: str, database_url: str) -> str:
        """Execute database command asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.execute_db_command, command, database_url
        )

    def close(self):
        """Close SSH connection."""
        if self.connection:
            self.connection.close()

class EnhancedIngestionManager:
    """Main manager for enhanced ingestion operations."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        self.progress_tracker = ProgressTracker(config.redis_url)
        self.deduplication_manager = DeduplicationManager(config.redis_url) if config.enable_deduplication else None
        self.async_loader = AsyncDataLoader(config)
        self.scheduler = IngestionScheduler() if config.scheduler_enabled else None
        self.remote_executor = RemoteExecutor(config.ssh_config) if config.remote_execution and config.ssh_config else None
        self.jobs: Dict[str, IngestionJob] = {}

    def create_job(self, source: str, collection: str, parameters: Dict[str, Any]) -> str:
        """Create a new ingestion job."""
        job_id = f"{source}_{collection}_{int(time.time())}"
        job = IngestionJob(
            job_id=job_id,
            source=source,
            collection=collection,
            parameters=parameters
        )
        self.jobs[job_id] = job
        return job_id

    async def execute_job_async(self, job_id: str) -> Dict[str, Any]:
        """Execute a job asynchronously."""
        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        job = self.jobs[job_id]
        job.status = "running"
        job.start_time = datetime.now()

        try:
            # Execute based on source
            if job.source == "congress":
                result = await self._execute_congress_ingestion(job)
            elif job.source == "openstates":
                result = await self._execute_openstates_ingestion(job)
            elif job.source == "govinfo":
                result = await self._execute_govinfo_ingestion(job)
            else:
                raise ValueError(f"Unknown source: {job.source}")

            job.status = "completed"
            job.end_time = datetime.now()
            return result

        except Exception as e:
            job.status = "failed"
            job.errors.append(str(e))
            job.end_time = datetime.now()
            raise

    async def _execute_congress_ingestion(self, job: IngestionJob) -> Dict[str, Any]:
        """Execute Congress data ingestion."""
        # Implementation would go here
        # This is a placeholder for the actual implementation
        return {"status": "completed", "records_processed": 0}

    async def _execute_openstates_ingestion(self, job: IngestionJob) -> Dict[str, Any]:
        """Execute OpenStates data ingestion."""
        # Implementation would go here
        return {"status": "completed", "records_processed": 0}

    async def _execute_govinfo_ingestion(self, job: IngestionJob) -> Dict[str, Any]:
        """Execute GovInfo data ingestion."""
        # Implementation would go here
        return {"status": "completed", "records_processed": 0}

    def schedule_job(self, job_id: str, cron_expression: str):
        """Schedule a job using cron expression."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not enabled")

        async def scheduled_execution():
            await self.execute_job_async(job_id)

        self.scheduler.add_cron_job(
            scheduled_execution,
            cron_expression,
            f"scheduled_{job_id}"
        )

    async def execute_remote_ingestion(self, job_id: str, remote_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute ingestion on remote server via SSH."""
        if not self.remote_executor:
            raise RuntimeError("Remote execution not configured")

        job = self.jobs[job_id]

        # Generate command for remote execution
        command = self._generate_remote_command(job, remote_config)

        # Execute on remote server
        result = await self.remote_executor.execute_async_db_command(
            command,
            remote_config['database_url']
        )

        return {"status": "completed", "remote_output": result}

    def _generate_remote_command(self, job: IngestionJob, remote_config: Dict[str, Any]) -> str:
        """Generate command for remote execution."""
        base_cmd = f"cd {remote_config.get('remote_path', '/app')} && python"

        if job.source == "congress":
            script = "scripts/ingestion/congress/congress_ingest.py"
            params = f"--congress {job.parameters.get('congress', '')}"
        elif job.source == "openstates":
            script = "scripts/ingestion/openstates/openstates_ingest.py"
            params = f"--jurisdiction {job.parameters.get('jurisdiction', '')}"
        elif job.source == "govinfo":
            script = "scripts/ingestion/govinfo/govinfo_ingest.py"
            params = f"--collection {job.parameters.get('collection', '')}"
        else:
            raise ValueError(f"Unknown source: {job.source}")

        return f"{base_cmd} {script} {params}"

# Global instance for easy access
ingestion_manager = None

def get_ingestion_manager(config: Optional[IngestionConfig] = None) -> EnhancedIngestionManager:
    """Get or create the global ingestion manager."""
    global ingestion_manager
    if ingestion_manager is None:
        if config is None:
            config = IngestionConfig()
        ingestion_manager = EnhancedIngestionManager(config)
    return ingestion_manager