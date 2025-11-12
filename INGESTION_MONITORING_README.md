# Data Ingestion Monitoring and Deduplication

This document describes the enhanced data ingestion system with remote monitoring and duplicate prevention capabilities.

## Overview

The MCP Legislative Data Server now includes comprehensive monitoring and deduplication features to ensure reliable, efficient data ingestion processes.

## Features

### 🔍 Duplicate Prevention

**Content-Based Deduplication**: Uses SHA-256 hashing of record content to prevent duplicate data insertion.

**Database-Level Deduplication**: Leverages PostgreSQL `ON CONFLICT DO UPDATE` for efficient handling of duplicate keys.

**Hash Storage**: Maintains a `record_hashes` table to track processed content and prevent re-ingestion.

### 📊 Remote Monitoring

**Job Tracking**: Each ingestion job is tracked with unique IDs, status, progress, and metadata.

**Real-Time Progress**: Monitor ingestion progress through API endpoints.

**Error Logging**: Comprehensive error tracking and reporting.

**Performance Metrics**: Track processing speed, duplicate counts, and completion status.

## Architecture

### Monitoring System (`mcp_server/utils/monitoring.py`)

```python
from mcp_server.utils.monitoring import monitor, deduplicator

# Create a monitoring job
job_id = monitor.create_job(
    source='congress',
    collection='bills_118_hr',
    api_key='your_key',
    congress=118,
    bill_type='hr'
)

# Use context manager for automatic job lifecycle management
with monitor.monitor_job(job_id):
    # Your ingestion logic here
    monitor.update_progress(job_id, processed_count, duplicates_count)
```

### Deduplication System

```python
# Check for duplicates before insertion
content_hash = deduplicator.get_content_hash(record_data, exclude_fields=['raw'])
if deduplicator.is_duplicate('table_name', content_hash, record_id):
    # Skip duplicate
    continue

# Insert record
# ...
```

## API Endpoints

### Monitoring Endpoints

#### Get All Jobs
```
GET /mcp/ingestion/jobs?status=running
```
Returns list of ingestion jobs, optionally filtered by status.

#### Get Specific Job
```
GET /mcp/ingestion/jobs/{job_id}
```
Returns detailed information about a specific job.

#### Start New Job
```
POST /mcp/ingestion/start
Content-Type: application/json

{
  "source": "congress",
  "collection": "bills",
  "metadata": {
    "congress": 118,
    "bill_type": "hr"
  }
}
```

#### Cleanup Old Data
```
DELETE /mcp/ingestion/cleanup?days=30
```
Removes old ingestion data and hash records.

### Health Check
```
GET /mcp/health
```
Returns system health status and timestamp.

## Database Schema

### Ingestion Jobs Table
```sql
CREATE TABLE ingestion_jobs (
    job_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,           -- congress, openstates, govinfo
    collection TEXT NOT NULL,       -- specific collection being ingested
    status TEXT NOT NULL,           -- pending, running, completed, failed
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    duplicates_found INTEGER DEFAULT 0,
    errors JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Record Hashes Table
```sql
CREATE TABLE record_hashes (
    table_name TEXT NOT NULL,
    record_id TEXT,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(table_name, content_hash)
);
```

## Usage Examples

### Running Monitored Ingestion

```bash
# Congress bills ingestion with monitoring
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
export CONGRESS_API_KEY=your_api_key

python mcp_server/scripts/congress_ingest.py --congress 118 --billType hr
```

The script will automatically:
1. Create a monitoring job
2. Track progress in real-time
3. Prevent duplicate insertions
4. Log completion status

### Monitoring Active Jobs

```bash
# Check running jobs
curl http://localhost:8000/mcp/ingestion/jobs?status=running

# Get specific job details
curl http://localhost:8000/mcp/ingestion/jobs/congress_bills_118_hr_1731420000
```

### Sample Job Response

```json
{
  "job_id": "congress_bills_118_hr_1731420000",
  "source": "congress",
  "collection": "bills_118_hr",
  "status": "running",
  "start_time": "2025-11-12T16:30:00.000Z",
  "total_records": 0,
  "processed_records": 245,
  "duplicates_found": 12,
  "errors": [],
  "metadata": {
    "api_key": "abc12345...",
    "congress": 118,
    "bill_type": "hr"
  }
}
```

## Configuration

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (required)
- `USE_COPY`: Enable PostgreSQL COPY for bulk inserts (optional)
- `USE_SQLALCHEMY`: Use SQLAlchemy instead of raw psycopg2 (optional)

### Monitoring Configuration

The monitoring system automatically:
- Creates required database tables
- Handles connection errors gracefully
- Logs warnings for database issues
- Continues operation even if monitoring fails

## Benefits

### Data Quality
- **No Duplicates**: Content-based hashing prevents duplicate records
- **Data Integrity**: Upsert operations ensure latest data is preserved
- **Audit Trail**: Complete history of ingestion operations

### Operational Visibility
- **Real-Time Monitoring**: Track ingestion progress remotely
- **Error Tracking**: Detailed error logging and reporting
- **Performance Metrics**: Monitor processing speed and efficiency

### Reliability
- **Fault Tolerance**: Jobs continue even if monitoring fails
- **Automatic Cleanup**: Remove old hash records to save space
- **Graceful Degradation**: System works without monitoring if needed

## Troubleshooting

### Common Issues

**Monitoring database not available**: The system will log warnings but continue ingestion without monitoring.

**High duplicate counts**: Check if you're re-running ingestion on the same data source.

**Slow performance**: Consider using `USE_COPY=true` for bulk operations.

### Logs

Ingestion scripts provide detailed logging:
```
Created ingestion job: congress_bills_118_hr_1731420000
Started monitoring job: congress_bills_118_hr_1731420000
Ingested 50 bills (total: 245, duplicates: 12)
Job congress_bills_118_hr_1731420000 completed successfully
Ingestion complete. Total bills processed: 245, duplicates found: 12
```

### API Error Responses

```json
{
  "detail": "Job congress_bills_118_hr_1731420000 not found",
  "status_code": 404
}
```

## Integration with Existing Scripts

All existing ingestion scripts have been updated to include monitoring and deduplication:

- `congress_ingest.py`: Federal legislative data
- `openstates_ingest.py`: State legislative data
- `govinfo_ingest.py`: Official government publications

No changes to command-line interfaces - monitoring is automatic.

## Future Enhancements

- Web dashboard for job monitoring
- Email/Slack notifications for job completion
- Advanced analytics and reporting
- Distributed ingestion coordination
- Automatic retry mechanisms
