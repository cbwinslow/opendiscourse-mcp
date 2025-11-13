"""Comprehensive performance monitoring and benchmarking utilities."""

import time
import psutil
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance metrics."""
    timestamp: float
    cpu_percent: float
    memory_used_mb: float
    memory_percent: float
    disk_read_mb: float
    disk_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    thread_count: int
    open_files: int

@dataclass
class IngestionMetrics:
    """Comprehensive metrics for data ingestion operations."""
    operation_id: str
    congress: int
    data_type: str
    start_time: float
    end_time: Optional[float] = None
    duration: float = 0.0

    # API metrics
    api_calls_made: int = 0
    api_calls_successful: int = 0
    api_response_times: List[float] = field(default_factory=list)
    api_errors: List[str] = field(default_factory=list)

    # Data metrics
    records_received: int = 0
    records_processed: int = 0
    records_stored: int = 0
    records_failed: int = 0
    duplicate_records: int = 0

    # Performance snapshots
    performance_snapshots: List[PerformanceSnapshot] = field(default_factory=list)

    # Status
    status: str = "running"
    error_message: Optional[str] = None

    def start_operation(self):
        """Mark the operation as started."""
        self.start_time = time.time()
        self.status = "running"

    def complete_operation(self, success: bool = True, error: Optional[str] = None):
        """Mark the operation as completed."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status = "completed" if success else "failed"
        if error:
            self.error_message = error

    def add_api_call(self, response_time: float, success: bool, error: Optional[str] = None):
        """Record an API call."""
        self.api_calls_made += 1
        if success:
            self.api_calls_successful += 1
            self.api_response_times.append(response_time)
        else:
            if error:
                self.api_errors.append(error)

    def add_records(self, received: int = 0, processed: int = 0, stored: int = 0,
                   failed: int = 0, duplicates: int = 0):
        """Update record counts."""
        self.records_received += received
        self.records_processed += processed
        self.records_stored += stored
        self.records_failed += failed
        self.duplicate_records += duplicates

    def take_performance_snapshot(self):
        """Take a current performance snapshot."""
        process = psutil.Process(os.getpid())

        # Get disk I/O
        disk_io = psutil.disk_io_counters()
        disk_read_mb = disk_io.read_bytes / 1024 / 1024 if disk_io else 0
        disk_write_mb = disk_io.write_bytes / 1024 / 1024 if disk_io else 0

        # Get network I/O
        net_io = psutil.net_io_counters()
        network_sent_mb = net_io.bytes_sent / 1024 / 1024 if net_io else 0
        network_recv_mb = net_io.bytes_recv / 1024 / 1024 if net_io else 0

        # Get memory info
        memory_info = process.memory_info()
        memory_used_mb = memory_info.rss / 1024 / 1024

        # Get thread and file counts
        thread_count = len(process.threads())
        try:
            open_files = len(process.open_files())
        except:
            open_files = 0

        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_used_mb=memory_used_mb,
            memory_percent=process.memory_percent(),
            disk_read_mb=disk_read_mb,
            disk_write_mb=disk_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            thread_count=thread_count,
            open_files=open_files
        )

        self.performance_snapshots.append(snapshot)
        return snapshot

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get comprehensive summary statistics."""
        if not self.end_time:
            self.end_time = time.time()
            self.duration = self.end_time - self.start_time

        # API stats
        api_success_rate = (self.api_calls_successful / self.api_calls_made * 100) if self.api_calls_made > 0 else 0
        avg_response_time = sum(self.api_response_times) / len(self.api_response_times) if self.api_response_times else 0

        # Data processing stats
        data_success_rate = (self.records_stored / self.records_processed * 100) if self.records_processed > 0 else 0
        records_per_second = self.records_processed / self.duration if self.duration > 0 else 0

        # Performance stats
        if self.performance_snapshots:
            avg_cpu = sum(s.cpu_percent for s in self.performance_snapshots) / len(self.performance_snapshots)
            avg_memory = sum(s.memory_used_mb for s in self.performance_snapshots) / len(self.performance_snapshots)
            peak_memory = max(s.memory_used_mb for s in self.performance_snapshots)
        else:
            avg_cpu = avg_memory = peak_memory = 0

        return {
            'operation_id': self.operation_id,
            'congress': self.congress,
            'data_type': self.data_type,
            'duration': self.duration,
            'status': self.status,

            'api_metrics': {
                'calls_made': self.api_calls_made,
                'calls_successful': self.api_calls_successful,
                'success_rate': api_success_rate,
                'avg_response_time': avg_response_time,
                'errors': len(self.api_errors)
            },

            'data_metrics': {
                'records_received': self.records_received,
                'records_processed': self.records_processed,
                'records_stored': self.records_stored,
                'records_failed': self.records_failed,
                'duplicate_records': self.duplicate_records,
                'success_rate': data_success_rate,
                'records_per_second': records_per_second
            },

            'performance_metrics': {
                'avg_cpu_percent': avg_cpu,
                'avg_memory_mb': avg_memory,
                'peak_memory_mb': peak_memory,
                'snapshots_taken': len(self.performance_snapshots)
            },

            'error_message': self.error_message
        }

class PerformanceMonitor:
    """Comprehensive performance monitoring system."""

    def __init__(self, log_directory: str = "logs/performance"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

        # Active metrics tracking
        self.active_metrics: Dict[str, IngestionMetrics] = {}
        self.metrics_lock = threading.Lock()

        # Global performance snapshots
        self.global_snapshots: List[PerformanceSnapshot] = []
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None

    def start_global_monitoring(self, interval: float = 5.0):
        """Start global system monitoring."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._global_monitor_loop,
            args=(interval,),
            daemon=True,
            name="PerformanceMonitor"
        )
        self.monitor_thread.start()
        logger.info(f"Started global performance monitoring (interval: {interval}s)")

    def stop_global_monitoring(self):
        """Stop global system monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        logger.info("Stopped global performance monitoring")

    def _global_monitor_loop(self, interval: float):
        """Global monitoring loop."""
        while self.monitoring_active:
            try:
                # Take global snapshot
                process = psutil.Process(os.getpid())

                disk_io = psutil.disk_io_counters()
                disk_read_mb = disk_io.read_bytes / 1024 / 1024 if disk_io else 0
                disk_write_mb = disk_io.write_bytes / 1024 / 1024 if disk_io else 0

                net_io = psutil.net_io_counters()
                network_sent_mb = net_io.bytes_sent / 1024 / 1024 if net_io else 0
                network_recv_mb = net_io.bytes_recv / 1024 / 1024 if net_io else 0

                memory_info = process.memory_info()
                memory_used_mb = memory_info.rss / 1024 / 1024

                thread_count = len(process.threads())
                try:
                    open_files = len(process.open_files())
                except:
                    open_files = 0

                snapshot = PerformanceSnapshot(
                    timestamp=time.time(),
                    cpu_percent=psutil.cpu_percent(interval=0.1),
                    memory_used_mb=memory_used_mb,
                    memory_percent=process.memory_percent(),
                    disk_read_mb=disk_read_mb,
                    disk_write_mb=disk_write_mb,
                    network_sent_mb=network_sent_mb,
                    network_recv_mb=network_recv_mb,
                    thread_count=thread_count,
                    open_files=open_files
                )

                self.global_snapshots.append(snapshot)

            except Exception as e:
                logger.error(f"Error in global monitoring: {e}")

            time.sleep(interval)

    def start_operation(self, congress: int, data_type: str) -> str:
        """Start tracking a new operation."""
        operation_id = f"{congress}_{data_type}_{int(time.time())}"

        metrics = IngestionMetrics(
            operation_id=operation_id,
            congress=congress,
            data_type=data_type
        )
        metrics.start_operation()

        with self.metrics_lock:
            self.active_metrics[operation_id] = metrics

        logger.info(f"Started operation: {operation_id}")
        return operation_id

    def update_operation(self, operation_id: str, **updates):
        """Update operation metrics."""
        with self.metrics_lock:
            if operation_id in self.active_metrics:
                metrics = self.active_metrics[operation_id]

                # Handle different update types
                if 'api_call' in updates:
                    call_info = updates['api_call']
                    metrics.add_api_call(
                        call_info.get('response_time', 0),
                        call_info.get('success', False),
                        call_info.get('error')
                    )

                if 'records' in updates:
                    record_info = updates['records']
                    metrics.add_records(
                        received=record_info.get('received', 0),
                        processed=record_info.get('processed', 0),
                        stored=record_info.get('stored', 0),
                        failed=record_info.get('failed', 0),
                        duplicates=record_info.get('duplicates', 0)
                    )

                if 'performance_snapshot' in updates:
                    metrics.take_performance_snapshot()

    def complete_operation(self, operation_id: str, success: bool = True, error: Optional[str] = None):
        """Complete an operation and log results."""
        with self.metrics_lock:
            if operation_id in self.active_metrics:
                metrics = self.active_metrics[operation_id]
                metrics.complete_operation(success, error)

                # Save detailed log
                self._save_operation_log(metrics)

                # Remove from active tracking
                del self.active_metrics[operation_id]

                logger.info(f"Completed operation: {operation_id} ({'SUCCESS' if success else 'FAILED'})")

    def _save_operation_log(self, metrics: IngestionMetrics):
        """Save detailed operation log to file."""
        timestamp = datetime.fromtimestamp(metrics.start_time).strftime("%Y%m%d_%H%M%S")
        filename = f"{metrics.operation_id}_{timestamp}.json"
        filepath = self.log_directory / filename

        log_data = {
            'metadata': {
                'operation_id': metrics.operation_id,
                'congress': metrics.congress,
                'data_type': metrics.data_type,
                'start_time': metrics.start_time,
                'end_time': metrics.end_time,
                'duration': metrics.duration,
                'status': metrics.status,
                'error_message': metrics.error_message
            },
            'api_metrics': {
                'calls_made': metrics.api_calls_made,
                'calls_successful': metrics.api_calls_successful,
                'response_times': metrics.api_response_times,
                'errors': metrics.api_errors
            },
            'data_metrics': {
                'records_received': metrics.records_received,
                'records_processed': metrics.records_processed,
                'records_stored': metrics.records_stored,
                'records_failed': metrics.records_failed,
                'duplicate_records': metrics.duplicate_records
            },
            'performance_snapshots': [
                {
                    'timestamp': s.timestamp,
                    'cpu_percent': s.cpu_percent,
                    'memory_used_mb': s.memory_used_mb,
                    'memory_percent': s.memory_percent,
                    'disk_read_mb': s.disk_read_mb,
                    'disk_write_mb': s.disk_write_mb,
                    'network_sent_mb': s.network_sent_mb,
                    'network_recv_mb': s.network_recv_mb,
                    'thread_count': s.thread_count,
                    'open_files': s.open_files
                } for s in metrics.performance_snapshots
            ]
        }

        try:
            with open(filepath, 'w') as f:
                json.dump(log_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save operation log {filepath}: {e}")

    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get summary of all active operations."""
        with self.metrics_lock:
            return [
                {
                    'operation_id': metrics.operation_id,
                    'congress': metrics.congress,
                    'data_type': metrics.data_type,
                    'duration': time.time() - metrics.start_time,
                    'api_calls': metrics.api_calls_made,
                    'records_processed': metrics.records_processed
                }
                for metrics in self.active_metrics.values()
            ]

    def generate_benchmark_report(self, operations: List[IngestionMetrics]) -> Dict[str, Any]:
        """Generate comprehensive benchmark report."""
        if not operations:
            return {'error': 'No operations to analyze'}

        total_duration = sum(op.duration for op in operations)
        total_api_calls = sum(op.api_calls_made for op in operations)
        total_records = sum(op.records_processed for op in operations)

        # Calculate averages
        avg_api_response_time = []
        for op in operations:
            avg_api_response_time.extend(op.api_response_times)
        avg_response_time = sum(avg_api_response_time) / len(avg_api_response_time) if avg_api_response_time else 0

        # Performance analysis
        all_cpu_usage = []
        all_memory_usage = []
        for op in operations:
            for snapshot in op.performance_snapshots:
                all_cpu_usage.append(snapshot.cpu_percent)
                all_memory_usage.append(snapshot.memory_used_mb)

        avg_cpu = sum(all_cpu_usage) / len(all_cpu_usage) if all_cpu_usage else 0
        avg_memory = sum(all_memory_usage) / len(all_memory_usage) if all_memory_usage else 0
        peak_memory = max(all_memory_usage) if all_memory_usage else 0

        return {
            'summary': {
                'total_operations': len(operations),
                'total_duration': total_duration,
                'total_api_calls': total_api_calls,
                'total_records_processed': total_records,
                'operations_per_second': len(operations) / total_duration if total_duration > 0 else 0,
                'records_per_second': total_records / total_duration if total_duration > 0 else 0,
                'api_calls_per_second': total_api_calls / total_duration if total_duration > 0 else 0
            },
            'api_performance': {
                'avg_response_time': avg_response_time,
                'total_successful_calls': sum(op.api_calls_successful for op in operations),
                'total_failed_calls': sum(len(op.api_errors) for op in operations)
            },
            'system_performance': {
                'avg_cpu_percent': avg_cpu,
                'avg_memory_mb': avg_memory,
                'peak_memory_mb': peak_memory
            },
            'data_quality': {
                'total_records_stored': sum(op.records_stored for op in operations),
                'total_duplicates': sum(op.duplicate_records for op in operations),
                'total_failed_records': sum(op.records_failed for op in operations)
            }
        }

# Global monitor instance
performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return performance_monitor
