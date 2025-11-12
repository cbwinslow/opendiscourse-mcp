# Enhanced MCP Legislative Data Ingestion System

This system provides advanced capabilities for ingesting legislative data from Congress.gov, OpenStates, and GovInfo APIs with GPU acceleration, parallel processing, async operations, scheduling, and distributed execution.

## Features

### 🚀 Performance Enhancements
- **GPU Acceleration**: Uses CuDF and CuML for GPU-accelerated data processing
- **Parallel Processing**: Multi-threaded and multi-process execution
- **Async Operations**: Asynchronous I/O and processing with asyncio
- **Batch Processing**: Optimized batch operations for large datasets

### 📅 Scheduling & Monitoring
- **Automated Scheduling**: Cron-based and interval-based job scheduling
- **Progress Tracking**: Real-time progress monitoring with Redis backend
- **Job Execution History**: Detailed execution logs and performance metrics
- **Alerting System**: Configurable alerts for job failures and performance issues

### 🔄 Deduplication & Optimization
- **Hash-based Deduplication**: Prevents duplicate data ingestion
- **Database Optimization**: Automatic indexing and query optimization
- **Data Compression**: Optional compression for storage efficiency

### 🌐 Distributed Execution
- **SSH-based Remote Execution**: Run ingestion jobs on remote servers
- **Multi-host Distribution**: Distribute workloads across multiple machines
- **Codebase Synchronization**: Automatic code deployment to remote hosts

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
export CONGRESS_API_KEY=your_congress_api_key
export OPENSTATES_API_KEY=your_openstates_api_key
export GOVINFO_API_KEY=your_govinfo_api_key
export REDIS_URL=redis://localhost:6379  # Optional, for distributed features
```

## Quick Start

### Basic Ingestion

```bash
# Enhanced Congress ingestion with GPU and parallel processing
python mcp_server/scripts/enhanced_congress_ingest.py \
  --congress 118 \
  --use-gpu \
  --use-parallel \
  --enable-progress

# Traditional ingestion (backward compatible)
python mcp_server/scripts/congress_ingest.py --congress 118
```

### Using the CLI

```bash
# Create and run a one-time ingestion job
python mcp_server/scripts/ingestion_cli.py create congress bills --congress 118

# Schedule a recurring job
python mcp_server/scripts/ingestion_cli.py schedule congress bills daily_update \
  --cron "0 2 * * *" \
  --congress 118

# List scheduled jobs
python mcp_server/scripts/ingestion_cli.py list

# Check job status
python mcp_server/scripts/ingestion_cli.py status congress_bills_daily_update

# Distributed ingestion across multiple hosts
python mcp_server/scripts/ingestion_cli.py distributed congress \
  --hosts user@host1:22 user@host2:22 \
  --congress 118
```

## Configuration

### IngestionConfig

```python
from mcp_server.utils.enhanced_ingestion import IngestionConfig

config = IngestionConfig(
    use_gpu=True,                    # Enable GPU processing
    use_parallel=True,               # Enable parallel processing
    use_async=True,                  # Enable async operations
    max_workers=8,                   # Maximum parallel workers
    batch_size=1000,                 # Batch size for processing
    enable_progress_tracking=True,   # Enable progress tracking
    enable_deduplication=True,       # Enable deduplication
    redis_url="redis://localhost:6379"  # Redis for distributed features
)
```

### Remote Host Configuration

```python
from mcp_server.utils.remote_execution import RemoteHost

host = RemoteHost(
    host="remote-server.com",
    user="mcp_user",
    key_file="~/.ssh/id_rsa_mcp",
    remote_path="/opt/mcp_ingestion",
    database_url="postgresql://user:pass@remote-db:5432/dbname"
)
```

## Advanced Usage

### GPU-Accelerated Processing

The system automatically detects GPU availability and uses CuDF for accelerated DataFrame operations:

```python
from mcp_server.utils.enhanced_ingestion import GPUDataProcessor

processor = GPUDataProcessor()
df = processor.process_dataframe(pandas_df)  # Returns CuDF DataFrame if GPU available
```

### Scheduling Jobs

```python
from mcp_server.utils.scheduler import get_scheduler, ScheduledJob

scheduler = get_scheduler()

job = ScheduledJob(
    job_id="congress_118_daily",
    name="Congress 118 Daily Update",
    source="congress",
    collection="bills",
    schedule_type="cron",
    schedule_config={"expression": "0 2 * * *"},  # Daily at 2 AM
    parameters={"congress": 118}
)

scheduler.add_scheduled_job(job)
await scheduler.start()  # Runs indefinitely
```

### Distributed Execution

```python
from mcp_server.utils.remote_execution import DistributedIngestionManager, RemoteHost

hosts = [
    RemoteHost(host="server1.com", user="mcp", port=22),
    RemoteHost(host="server2.com", user="mcp", port=22),
]

async with DistributedIngestionManager(hosts) as manager:
    result = await manager.distribute_ingestion_job({
        "type": "congress",
        "parameters": {"congress": 118},
        "database_url": "postgresql://..."
    })
```

### SSH Setup

```bash
# Generate SSH key pair
python mcp_server/scripts/ingestion_cli.py ssh-setup

# Setup passwordless SSH to a specific host
python mcp_server/scripts/ingestion_cli.py ssh-setup \
  --setup-host remote-server.com \
  --setup-user mcp_user
```

### Progress Monitoring

```python
from mcp_server.utils.enhanced_ingestion import get_ingestion_manager

manager = get_ingestion_manager()
progress = manager.progress_tracker.get_progress("job_123")
print(f"Progress: {progress['progress']}%, Processed: {progress['processed']}")
```

## API Reference

### EnhancedIngestionManager

Main manager class for enhanced ingestion operations.

#### Methods

- `create_job(source, collection, parameters)`: Create a new ingestion job
- `execute_job_async(job_id)`: Execute a job asynchronously
- `schedule_job(job_id, cron_expression)`: Schedule a job
- `execute_remote_ingestion(job_id, remote_config)`: Execute on remote server

### IngestionScheduler

Scheduler for automated job execution.

#### Methods

- `add_scheduled_job(job)`: Add a scheduled job
- `remove_scheduled_job(job_id)`: Remove a scheduled job
- `get_scheduled_jobs()`: Get all scheduled jobs
- `get_job_executions(job_id, limit)`: Get job execution history

### RemoteExecutor

SSH-based remote execution manager.

#### Methods

- `connect_all()`: Connect to all configured hosts
- `execute_on_host(host, command, env_vars)`: Execute command on specific host
- `execute_parallel(commands, env_vars)`: Execute commands in parallel
- `upload_file(host, local_path, remote_path)`: Upload file to host
- `download_file(host, remote_path, local_path)`: Download file from host

## Database Schema

The system uses the following tables:

### congress_bills
```sql
CREATE TABLE congress_bills (
    id TEXT PRIMARY KEY,
    congress SMALLINT,
    bill_type TEXT,
    bill_number INTEGER,
    title TEXT,
    latest_action_date DATE,
    latest_action_description TEXT,
    subjects TEXT[],
    sponsors JSONB,
    raw JSONB,
    updated_on TIMESTAMP DEFAULT NOW()
);
```

### openstates_bills
```sql
CREATE TABLE openstates_bills (
    id TEXT PRIMARY KEY,
    session TEXT,
    jurisdiction TEXT,
    identifier TEXT,
    title TEXT,
    classification TEXT[],
    subjects TEXT[],
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    first_action_date DATE,
    latest_action_date DATE,
    latest_action_description TEXT,
    openstates_url TEXT,
    raw JSONB,
    updated_on TIMESTAMP DEFAULT NOW()
);
```

### govinfo_documents
```sql
CREATE TABLE govinfo_documents (
    id TEXT PRIMARY KEY,
    collection TEXT,
    date DATE,
    title TEXT,
    url TEXT,
    metadata JSONB,
    raw JSONB,
    created_on TIMESTAMP DEFAULT NOW()
);
```

## Performance Tuning

### GPU Configuration

Ensure CUDA is properly installed and configured:

```bash
# Check GPU availability
nvidia-smi

# Install CuDF/CuML (if not using pip)
conda install -c rapidsai -c nvidia -c conda-forge cudf cuml
```

### Memory Optimization

```python
# Configure batch sizes based on available memory
config = IngestionConfig(
    batch_size=500,  # Smaller batches for limited memory
    chunk_size=50000,
    enable_compression=True
)
```

### Parallel Processing

```python
# Adjust workers based on CPU cores
import multiprocessing
config = IngestionConfig(
    max_workers=min(16, multiprocessing.cpu_count() * 2)
)
```

## Monitoring & Alerting

### System Metrics

The system tracks:
- CPU usage
- Memory usage
- Disk I/O
- Network I/O
- Job execution times
- Error rates

### Alert Configuration

```python
from mcp_server.utils.scheduler import get_monitor

monitor = get_monitor()

async def alert_handler(alert):
    print(f"Alert: {alert['type']} - {alert}")

monitor.add_alert_callback(alert_handler)
await monitor.monitor_jobs()
```

## Troubleshooting

### Common Issues

1. **GPU not detected**: Ensure CUDA drivers are installed and CuDF is properly configured
2. **SSH connection fails**: Check SSH keys, firewall settings, and host accessibility
3. **Redis connection errors**: Verify Redis is running and accessible
4. **Memory errors**: Reduce batch sizes or enable compression

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Performance Profiling

```python
from mcp_server.utils.scheduler import IngestionScheduler
import cProfile

scheduler = IngestionScheduler()
cProfile.runctx('scheduler.add_scheduled_job(job)', globals(), locals())
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.