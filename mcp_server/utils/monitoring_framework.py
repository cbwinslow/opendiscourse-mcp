"""
Comprehensive monitoring and observability framework for OpenDiscourse
Includes feature flags, decorators, OpenTelemetry, Prometheus, Loki integration
"""

import os
import json
import time
import functools
import logging
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# Feature Flags Configuration
@dataclass
class FeatureFlags:
    """Central feature flag configuration"""
    enable_opentelemetry: bool = True
    enable_prometheus: bool = True
    enable_loki_logging: bool = True
    enable_alloy_observability: bool = True
    enable_detailed_triggers: bool = True
    enable_cloudflare_tunnel: bool = True
    enable_benchmarking: bool = True
    enable_telemetry: bool = True
    enable_error_tracking: bool = True
    enable_performance_metrics: bool = True

    @classmethod
    def from_env(cls) -> 'FeatureFlags':
        """Load feature flags from environment variables"""
        return cls(
            enable_opentelemetry=os.getenv('ENABLE_OPENTELEMETRY', 'true').lower() == 'true',
            enable_prometheus=os.getenv('ENABLE_PROMETHEUS', 'true').lower() == 'true',
            enable_loki_logging=os.getenv('ENABLE_LOKI_LOGGING', 'true').lower() == 'true',
            enable_alloy_observability=os.getenv('ENABLE_ALLOY_OBSERVABILITY', 'true').lower() == 'true',
            enable_detailed_triggers=os.getenv('ENABLE_DETAILED_TRIGGERS', 'true').lower() == 'true',
            enable_cloudflare_tunnel=os.getenv('ENABLE_CLOUDFLARE_TUNNEL', 'true').lower() == 'true',
            enable_benchmarking=os.getenv('ENABLE_BENCHMARKING', 'true').lower() == 'true',
            enable_telemetry=os.getenv('ENABLE_TELEMETRY', 'true').lower() == 'true',
            enable_error_tracking=os.getenv('ENABLE_ERROR_TRACKING', 'true').lower() == 'true',
            enable_performance_metrics=os.getenv('ENABLE_PERFORMANCE_METRICS', 'true').lower() == 'true',
        )

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class TelemetryEvent:
    """Structured telemetry event"""
    event_type: str
    timestamp: datetime
    congress: Optional[int] = None
    data_type: Optional[str] = None
    records_processed: int = 0
    duration_ms: float = 0.0
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MonitoringFramework:
    """Central monitoring and observability framework"""
    
    def __init__(self, feature_flags: Optional[FeatureFlags] = None):
        self.flags = feature_flags or FeatureFlags.from_env()
        self.logger = self._setup_logger()
        self.metrics = {}
        self.events = []
        self._lock = threading.Lock()
        
        # Initialize monitoring components based on feature flags
        if self.flags.enable_opentelemetry:
            self._setup_opentelemetry()
        if self.flags.enable_prometheus:
            self._setup_prometheus()
        if self.flags.enable_loki_logging:
            self._setup_loki()
        if self.flags.enable_alloy_observability:
            self._setup_alloy()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logger"""
        logger = logging.getLogger('opendiscourse')
        logger.setLevel(logging.INFO)
        
        # Create console handler with structured format
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def _setup_opentelemetry(self):
        """Initialize OpenTelemetry with remote endpoint"""
        try:
            from opentelemetry import trace, metrics
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.resources import Resource
            
            # Remote endpoint configuration
            otlp_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://cbwdellr720:4318')
            otlp_headers = os.getenv('OTEL_EXPORTER_OTLP_HEADERS', '')
            
            # Configure OpenTelemetry
            resource = Resource.create({
                "service.name": "opendiscourse-ingestion",
                "service.version": "1.0.0",
                "deployment.environment": os.getenv("ENVIRONMENT", "production"),
                "host.name": "laptop",
                "monitoring.server": "cbwdellr720"
            })
            
            # Setup tracing with remote endpoint
            trace_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers={"Authorization": otlp_headers} if otlp_headers else None
            )
            trace.set_tracer_provider(TracerProvider(resource=resource, span_exporters=[trace_exporter]))
            tracer = trace.get_tracer(__name__)
            
            # Setup metrics with remote endpoint
            metrics_exporter = OTLPMetricExporter(
                endpoint=otlp_endpoint,
                headers={"Authorization": otlp_headers} if otlp_headers else None
            )
            metrics.set_meter_provider(MeterProvider(resource=resource, metric_exporters=[metrics_exporter]))
            meter = metrics.get_meter(__name__)
            
            self.tracer = tracer
            self.meter = meter
            
            # Create metrics
            self.ingestion_counter = meter.create_counter(
                "ingestion_records_total",
                description="Total number of records ingested"
            )
            self.ingestion_duration = meter.create_histogram(
                "ingestion_duration_seconds",
                description="Duration of ingestion operations"
            )
            
            self.logger.info(f"OpenTelemetry initialized with remote endpoint: {otlp_endpoint}")
            
        except ImportError:
            self.logger.warning("OpenTelemetry packages not installed")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenTelemetry: {e}")
    
    def _setup_prometheus(self):
        """Initialize Prometheus metrics with remote gateway"""
        try:
            from prometheus_client import Counter, Histogram, Gauge, start_http_server, CollectorRegistry, push_to_gateway
            
            # Create custom registry for remote pushing
            self.prom_registry = CollectorRegistry()
            
            # Create Prometheus metrics
            self.prom_records_total = Counter(
                'opendiscourse_ingestion_records_total',
                'Total records ingested',
                ['congress', 'data_type', 'status', 'source_host'],
                registry=self.prom_registry
            )
            self.prom_duration = Histogram(
                'opendiscourse_ingestion_duration_seconds',
                'Ingestion duration in seconds',
                ['congress', 'data_type', 'source_host'],
                registry=self.prom_registry
            )
            self.prom_active_jobs = Gauge(
                'opendiscourse_active_ingestion_jobs',
                'Number of active ingestion jobs',
                ['source_host'],
                registry=self.prom_registry
            )
            
            # Remote Prometheus gateway configuration
            prometheus_gateway = os.getenv('PROMETHEUS_GATEWAY_URL', 'http://cbwdellr720:8889')
            
            # Start local Prometheus server for backup
            prometheus_port = int(os.getenv('PROMETHEUS_PORT', '8000'))
            start_http_server(prometheus_port, registry=self.prom_registry)
            
            # Setup remote pushing function
            self.prometheus_gateway = prometheus_gateway
            
            self.logger.info(f"Prometheus initialized with remote gateway: {prometheus_gateway}")
            self.logger.info(f"Local Prometheus server on port {prometheus_port}")
            
        except ImportError:
            self.logger.warning("Prometheus client not installed")
        except Exception as e:
            self.logger.error(f"Failed to initialize Prometheus: {e}")
    
    def _setup_loki(self):
        """Initialize Loki logging"""
        try:
            import requests
            from datetime import datetime
            
            self.loki_url = os.getenv('LOKI_URL', 'http://localhost:3100/loki/api/v1/push')
            self.loki_labels = {
                'service': 'opendiscourse-ingestion',
                'environment': os.getenv('ENVIRONMENT', 'development')
            }
            
            self.logger.info("Loki logging initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Loki: {e}")
    
    def _setup_alloy(self):
        """Initialize Alloy observability"""
        try:
            # Alloy configuration would go here
            self.alloy_endpoint = os.getenv('ALLOY_ENDPOINT', 'http://localhost:8080')
            self.logger.info("Alloy observability initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Alloy: {e}")
    
    def record_event(self, event: TelemetryEvent):
        """Record telemetry event"""
        with self._lock:
            self.events.append(event)
            
            # Send to various backends
            if self.flags.enable_loki_logging:
                self._send_to_loki(event)
            if self.flags.enable_alloy_observability:
                self._send_to_alloy(event)
            if self.flags.enable_prometheus:
                self._update_prometheus_metrics(event)
    
    def _send_to_loki(self, event: TelemetryEvent):
        """Send event to Loki"""
        try:
            import requests
            
            log_entry = {
                "timestamp": event.timestamp.isoformat(),
                "level": "INFO" if not event.error else "ERROR",
                "message": f"{event.event_type}: {event.data_type} for Congress {event.congress}",
                "labels": {
                    **self.loki_labels,
                    "congress": str(event.congress) if event.congress else "unknown",
                    "data_type": event.data_type or "unknown",
                    "event_type": event.event_type
                },
                "metadata": asdict(event)
            }
            
            response = requests.post(
                self.loki_url,
                json={"streams": [{"stream": log_entry["labels"], "values": [[str(int(time.time())), json.dumps(log_entry)]]}]},
                timeout=5
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send to Loki: {e}")
    
    def _send_to_alloy(self, event: TelemetryEvent):
        """Send event to Alloy"""
        try:
            import requests
            
            payload = asdict(event)
            payload['timestamp'] = event.timestamp.isoformat()
            
            response = requests.post(
                f"{self.alloy_endpoint}/events",
                json=payload,
                timeout=5
            )
            
        except Exception as e:
            self.logger.error(f"Failed to send to Alloy: {e}")
    
    def _update_prometheus_metrics(self, event: TelemetryEvent):
        """Update Prometheus metrics"""
        try:
            if hasattr(self, 'prom_records_total'):
                self.prom_records_total.labels(
                    congress=str(event.congress) if event.congress else "unknown",
                    data_type=event.data_type or "unknown",
                    status="success" if not event.error else "error"
                ).inc(event.records_processed)
            
            if hasattr(self, 'prom_duration') and event.duration_ms > 0:
                self.prom_duration.labels(
                    congress=str(event.congress) if event.congress else "unknown",
                    data_type=event.data_type or "unknown"
                ).observe(event.duration_ms / 1000.0)
                
        except Exception as e:
            self.logger.error(f"Failed to update Prometheus metrics: {e}")

# Global monitoring instance
_monitor = None

def get_monitor() -> MonitoringFramework:
    """Get global monitoring instance"""
    global _monitor
    if _monitor is None:
        _monitor = MonitoringFramework()
    return _monitor

def monitor_ingestion(data_type: str, congress: Optional[int] = None):
    """Decorator for monitoring ingestion functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            start_time = time.time()
            start_timestamp = datetime.now()
            
            # Update active jobs counter
            if hasattr(monitor, 'prom_active_jobs'):
                monitor.prom_active_jobs.inc()
            
            try:
                result = func(*args, **kwargs)
                
                # Record successful event
                duration_ms = (time.time() - start_time) * 1000
                event = TelemetryEvent(
                    event_type="ingestion_completed",
                    timestamp=start_timestamp,
                    congress=congress,
                    data_type=data_type,
                    duration_ms=duration_ms,
                    metadata={"args": str(args), "kwargs": str(kwargs)}
                )
                monitor.record_event(event)
                
                monitor.logger.info(f"Successfully completed {data_type} ingestion for Congress {congress}")
                return result
                
            except Exception as e:
                # Record error event
                duration_ms = (time.time() - start_time) * 1000
                event = TelemetryEvent(
                    event_type="ingestion_failed",
                    timestamp=start_timestamp,
                    congress=congress,
                    data_type=data_type,
                    duration_ms=duration_ms,
                    error=str(e),
                    metadata={"args": str(args), "kwargs": str(kwargs)}
                )
                monitor.record_event(event)
                
                monitor.logger.error(f"Failed {data_type} ingestion for Congress {congress}: {e}")
                raise
                
            finally:
                # Update active jobs counter
                if hasattr(monitor, 'prom_active_jobs'):
                    monitor.prom_active_jobs.dec()
        
        return wrapper
    return decorator

def benchmark_function(func: Callable) -> Callable:
    """Decorator for benchmarking functions"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        monitor = get_monitor()
        
        if not monitor.flags.enable_benchmarking:
            return func(*args, **kwargs)
        
        start_time = time.time()
        start_memory = _get_memory_usage()
        
        try:
            result = func(*args, **kwargs)
            
            # Record benchmark metrics
            end_time = time.time()
            end_memory = _get_memory_usage()
            duration_ms = (end_time - start_time) * 1000
            memory_diff = end_memory - start_memory
            
            event = TelemetryEvent(
                event_type="benchmark",
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                metadata={
                    "function": func.__name__,
                    "memory_usage_mb": memory_diff,
                    "args_count": len(args),
                    "kwargs_count": len(kwargs)
                }
            )
            monitor.record_event(event)
            
            monitor.logger.info(f"Benchmark: {func.__name__} took {duration_ms:.2f}ms, memory delta: {memory_diff:.2f}MB")
            return result
            
        except Exception as e:
            monitor.logger.error(f"Benchmark failed for {func.__name__}: {e}")
            raise
    
    return wrapper

def _get_memory_usage() -> float:
    """Get current memory usage in MB"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0

# Cloudflare Tunnel Management
class CloudflareTunnelManager:
    """Manage Cloudflare tunnels for secure access"""
    
    def __init__(self):
        self.tunnel_config = {
            "tunnel": os.getenv('CLOUDFLARE_TUNNEL_ID'),
            "credentials-file": os.getenv('CLOUDFLARE_CREDENTIALS_FILE', '/etc/cloudflared/cert.pem'),
            "ingress": []
        }
        self.tunnels = {}
    
    def create_tunnel(self, name: str, local_port: int, hostname: str = None) -> Dict[str, Any]:
        """Create a new Cloudflare tunnel"""
        tunnel_config = {
            "hostname": hostname or f"{name}.opendiscourse.com",
            "local_port": local_port,
            "local_address": f"localhost:{local_port}"
        }
        
        self.tunnels[name] = tunnel_config
        self.tunnel_config["ingress"].append({
            "hostname": tunnel_config["hostname"],
            "service": f"http://{tunnel_config['local_address']}"
        })
        
        return tunnel_config
    
    def generate_config(self) -> str:
        """Generate cloudflared configuration"""
        return json.dumps(self.tunnel_config, indent=2)
    
    def setup_tunnel(self, name: str, local_port: int, hostname: str = None):
        """Setup and start a Cloudflare tunnel"""
        try:
            tunnel_config = self.create_tunnel(name, local_port, hostname)
            
            # Generate config file
            config_path = f"/tmp/cloudflared-{name}.yml"
            with open(config_path, 'w') as f:
                f.write(f"tunnel: {self.tunnel_config['tunnel']}\n")
                f.write(f"credentials-file: {self.tunnel_config['credentials-file']}\n")
                f.write("ingress:\n")
                for ingress in self.tunnel_config["ingress"]:
                    f.write(f"  - hostname: {ingress['hostname']}\n")
                    f.write(f"    service: {ingress['service']}\n")
                f.write("  - service: http_status:404\n")
            
            # Start tunnel
            import subprocess
            subprocess.Popen([
                "cloudflared", "tunnel", "--config", config_path, "run"
            ])
            
            return tunnel_config
            
        except Exception as e:
            get_monitor().logger.error(f"Failed to setup Cloudflare tunnel {name}: {e}")
            raise

# Export main components
__all__ = [
    'FeatureFlags',
    'TelemetryEvent', 
    'MonitoringFramework',
    'get_monitor',
    'monitor_ingestion',
    'benchmark_function',
    'CloudflareTunnelManager'
]