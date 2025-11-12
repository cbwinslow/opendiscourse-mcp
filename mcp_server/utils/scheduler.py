"""Scheduling and monitoring utilities for ingestion jobs."""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import psutil

# Optional imports with fallbacks
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.jobstores.redis import RedisJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None
    MemoryJobStore = None
    RedisJobStore = None
    AsyncIOExecutor = None
    CronTrigger = None
    IntervalTrigger = None

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    schedule = None

try:
    import memory_profiler
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    memory_profiler = None

try:
    from line_profiler import LineProfiler
    LINE_PROFILER_AVAILABLE = True
except ImportError:
    LINE_PROFILER_AVAILABLE = False
    LineProfiler = None

logger = logging.getLogger(__name__)

@dataclass
class ScheduledJob:
    """Represents a scheduled ingestion job."""
    job_id: str
    name: str
    source: str
    collection: str
    schedule_type: str  # 'cron', 'interval', 'daily', 'weekly'
    schedule_config: Dict[str, Any]
    parameters: Dict[str, Any]
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

@dataclass
class JobExecution:
    """Represents a job execution instance."""
    execution_id: str
    job_id: str
    status: str  # 'running', 'completed', 'failed'
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    records_processed: int = 0
    errors: List[str] = None
    performance_metrics: Dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

class IngestionScheduler:
    """Advanced scheduler for ingestion jobs with monitoring."""

    def __init__(self, redis_url: Optional[str] = None, use_redis: bool = False):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler not available. Install with: pip install apscheduler")
        
        self.redis_client = redis.from_url(redis_url or "redis://localhost:6379") if redis_url and REDIS_AVAILABLE else None
        self.use_redis = use_redis and self.redis_client is not None

        # Initialize APScheduler
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_executor(AsyncIOExecutor())

        if self.use_redis:
            jobstore = RedisJobStore(host=self.redis_client.connection_pool.connection_kwargs['host'])
            self.scheduler.add_jobstore(jobstore, "redis")
        else:
            self.scheduler.add_jobstore(MemoryJobStore(), "memory")

        self.scheduled_jobs: Dict[str, ScheduledJob] = {}
        self.active_executions: Dict[str, JobExecution] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

        # Performance monitoring
        self.profiler = LineProfiler() if LINE_PROFILER_AVAILABLE else None
        self.memory_monitoring = {}

    async def start(self):
        """Start the scheduler."""
        self.scheduler.start()
        logger.info("Ingestion scheduler started")

        # Start monitoring thread
        monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitoring_thread.start()

        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            await self.shutdown()

    async def shutdown(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown()
        self.executor.shutdown()
        logger.info("Ingestion scheduler shutdown")

    def add_scheduled_job(self, job: ScheduledJob) -> str:
        """Add a scheduled job."""
        self.scheduled_jobs[job.job_id] = job

        # Create the actual APScheduler job
        if job.schedule_type == 'cron':
            trigger = CronTrigger.from_crontab(job.schedule_config['expression'])
        elif job.schedule_type == 'interval':
            trigger = IntervalTrigger(seconds=job.schedule_config['seconds'])
        else:
            raise ValueError(f"Unsupported schedule type: {job.schedule_type}")

        async def job_wrapper():
            await self._execute_scheduled_job(job.job_id)

        self.scheduler.add_job(
            job_wrapper,
            trigger=trigger,
            id=job.job_id,
            name=job.name,
            max_instances=1,
            replace_existing=True
        )

        # Calculate next run time
        try:
            apscheduler_job = self.scheduler.get_job(job.job_id)
            job.next_run = apscheduler_job.next_run_time if hasattr(apscheduler_job, 'next_run_time') else None
        except:
            job.next_run = None
        self._save_job(job)

        logger.info(f"Added scheduled job: {job.name} ({job.job_id})")
        return job.job_id

    async def _execute_scheduled_job(self, job_id: str):
        """Execute a scheduled job with monitoring."""
        if job_id not in self.scheduled_jobs:
            logger.error(f"Job {job_id} not found")
            return

        job = self.scheduled_jobs[job_id]
        execution_id = f"{job_id}_{int(time.time())}"

        # Create execution record
        execution = JobExecution(
            execution_id=execution_id,
            job_id=job_id,
            status='running',
            start_time=datetime.now()
        )

        self.active_executions[execution_id] = execution
        job.last_run = execution.start_time
        job.run_count += 1

        try:
            # Start performance monitoring
            self.profiler.enable()

            # Execute the job
            result = await self._run_ingestion_job(job)

            # Stop performance monitoring
            self.profiler.disable()

            # Update execution record
            execution.status = 'completed'
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.records_processed = result.get('records_processed', 0)
            execution.performance_metrics = self._collect_performance_metrics()

            job.success_count += 1

            logger.info(f"Job {job.name} completed successfully. Processed {execution.records_processed} records in {execution.duration:.2f}s")

        except Exception as e:
            execution.status = 'failed'
            execution.end_time = datetime.now()
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            execution.errors.append(str(e))

            job.failure_count += 1

            logger.error(f"Job {job.name} failed: {e}")

        finally:
            # Update job metadata
            job.updated_at = datetime.now()
            try:
                apscheduler_job = self.scheduler.get_job(job_id)
                job.next_run = apscheduler_job.next_run_time if hasattr(apscheduler_job, 'next_run_time') else None
            except:
                job.next_run = None
            self._save_job(job)
            self._save_execution(execution)

    async def _run_ingestion_job(self, job: ScheduledJob) -> Dict[str, Any]:
        """Run the actual ingestion job."""
        # Import here to avoid circular imports
        from mcp_server.utils.enhanced_ingestion import get_ingestion_manager

        manager = get_ingestion_manager()

        # Create and execute the job
        job_id = manager.create_job(job.source, job.collection, job.parameters)
        result = await manager.execute_job_async(job_id)

        return result

    def remove_scheduled_job(self, job_id: str):
        """Remove a scheduled job."""
        if job_id in self.scheduled_jobs:
            self.scheduler.remove_job(job_id)
            del self.scheduled_jobs[job_id]
            self._delete_job(job_id)
            logger.info(f"Removed scheduled job: {job_id}")

    def get_scheduled_jobs(self) -> List[ScheduledJob]:
        """Get all scheduled jobs."""
        return list(self.scheduled_jobs.values())

    def get_job_executions(self, job_id: str, limit: int = 10) -> List[JobExecution]:
        """Get execution history for a job."""
        executions = []
        if self.use_redis:
            # Get from Redis
            pattern = f"execution:{job_id}:*"
            keys = self.redis_client.keys(pattern)
            for key in keys[-limit:]:  # Get last N executions
                data = self.redis_client.get(key)
                if data:
                    exec_data = json.loads(data)
                    executions.append(JobExecution(**exec_data))
        else:
            # Filter from active executions
            executions = [exec for exec in self.active_executions.values()
                         if exec.job_id == job_id][-limit:]

        return sorted(executions, key=lambda x: x.start_time, reverse=True)

    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics."""
        metrics = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used_mb': psutil.virtual_memory().used / 1024 / 1024,
            'timestamp': datetime.now().isoformat()
        }

        # Get profiler stats if available
        if hasattr(self.profiler, 'get_stats'):
            try:
                stats = self.profiler.get_stats()
                metrics['profiler_stats'] = {
                    'total_time': sum(stat.total_time for stat in stats),
                    'function_count': len(stats)
                }
            except:
                pass

        return metrics

    def _monitoring_loop(self):
        """Background monitoring loop."""
        while True:
            try:
                # Update system metrics
                self._update_system_metrics()

                # Check for failed jobs and retry if configured
                self._check_failed_jobs()

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)

    def _update_system_metrics(self):
        """Update system performance metrics."""
        metrics = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }

        if self.use_redis:
            self.redis_client.set('system_metrics', json.dumps(metrics), ex=300)  # Expire in 5 minutes

    def _check_failed_jobs(self):
        """Check for failed jobs and handle retries."""
        # Implementation for retry logic would go here
        pass

    def _save_job(self, job: ScheduledJob):
        """Save job to storage."""
        if self.use_redis:
            self.redis_client.set(f"job:{job.job_id}", json.dumps(asdict(job)))

    def _save_execution(self, execution: JobExecution):
        """Save execution to storage."""
        if self.use_redis:
            key = f"execution:{execution.job_id}:{execution.execution_id}"
            self.redis_client.set(key, json.dumps(asdict(execution)), ex=86400*30)  # Keep for 30 days

    def _delete_job(self, job_id: str):
        """Delete job from storage."""
        if self.use_redis:
            self.redis_client.delete(f"job:{job_id}")

class JobMonitor:
    """Real-time job monitoring and alerting."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = redis.from_url(redis_url or "redis://localhost:6379") if redis_url else None
        self.alerts = []
        self.alert_callbacks = []

    def add_alert_callback(self, callback: Callable):
        """Add a callback for alerts."""
        self.alert_callbacks.append(callback)

    async def monitor_jobs(self):
        """Monitor jobs and trigger alerts."""
        while True:
            try:
                # Check for failed jobs
                failed_jobs = await self._check_failed_jobs()

                # Check performance thresholds
                performance_alerts = await self._check_performance_thresholds()

                # Trigger alerts
                for alert in failed_jobs + performance_alerts:
                    for callback in self.alert_callbacks:
                        await callback(alert)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Job monitoring error: {e}")
                await asyncio.sleep(30)

    async def _check_failed_jobs(self) -> List[Dict[str, Any]]:
        """Check for recently failed jobs."""
        alerts = []

        if self.redis_client:
            # Get recent failed executions
            pattern = "execution:*:*"
            keys = self.redis_client.keys(pattern)

            for key in keys[-100:]:  # Check last 100 executions
                data = self.redis_client.get(key)
                if data:
                    exec_data = json.loads(data)
                    if exec_data['status'] == 'failed':
                        execution_time = datetime.fromisoformat(exec_data['start_time'])
                        if datetime.now() - execution_time < timedelta(hours=1):
                            alerts.append({
                                'type': 'job_failure',
                                'job_id': exec_data['job_id'],
                                'execution_id': exec_data['execution_id'],
                                'error': exec_data.get('errors', []),
                                'timestamp': datetime.now().isoformat()
                            })

        return alerts

    async def _check_performance_thresholds(self) -> List[Dict[str, Any]]:
        """Check performance thresholds."""
        alerts = []

        if self.redis_client:
            metrics_data = self.redis_client.get('system_metrics')
            if metrics_data:
                metrics = json.loads(metrics_data)

                # Check CPU usage
                if metrics['cpu_percent'] > 90:
                    alerts.append({
                        'type': 'high_cpu',
                        'value': metrics['cpu_percent'],
                        'threshold': 90,
                        'timestamp': datetime.now().isoformat()
                    })

                # Check memory usage
                if metrics['memory_percent'] > 85:
                    alerts.append({
                        'type': 'high_memory',
                        'value': metrics['memory_percent'],
                        'threshold': 85,
                        'timestamp': datetime.now().isoformat()
                    })

        return alerts

# Global instances
scheduler = None
monitor = None

def get_scheduler(redis_url: Optional[str] = None) -> IngestionScheduler:
    """Get or create the global scheduler."""
    global scheduler
    if scheduler is None:
        scheduler = IngestionScheduler(redis_url)
    return scheduler

def get_monitor(redis_url: Optional[str] = None) -> JobMonitor:
    """Get or create the global monitor."""
    global monitor
    if monitor is None:
        monitor = JobMonitor(redis_url)
    return monitor