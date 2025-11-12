# OpenDiscourse MCP System - AI Agent Guidelines

## Architecture Overview

OpenDiscourse is a Model Context Protocol (MCP) server that reverse-engineers legislative data APIs from three sources:
- **Congress.gov API** - Federal legislative data (bills, members, votes, committees)
- **OpenStates API** - State legislative data (50+ state legislatures)  
- **GovInfo API** - Government publications and official documents

The system uses **PostgreSQL triggers for automatic progress monitoring** - data ingestion progress is tracked in real-time without manual updates.

## Critical Agent Rules

### Database Trigger System
- **Never manually update `processed_records`** - PostgreSQL triggers handle this automatically
- **Always use `monitor.monitor_job(job_id)` context manager** for ingestion operations
- **Check trigger health** before starting large ingestion jobs
- **Job context is per-database-session** - multiple agents can run concurrently

### Ingestion Workflow Pattern
```python
from mcp_server.utils.monitoring import monitor

# 1. Create job
job_id = monitor.create_job('congress', 'bills_118_hr')

# 2. Use context manager (sets/clears session context automatically)
with monitor.monitor_job(job_id):
    for bill in congress_api.get_bills():
        db.insert_bill(bill)  # Triggers fire automatically
        # NO manual progress updates needed!

# 3. Job automatically marked as completed
```

### Database Health Checks
```python
# Verify triggers exist before ingestion
cur.execute("SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE 'trg_%_progress'")
trigger_count = cur.fetchone()[0]
assert trigger_count >= 15  # Should have triggers on all main tables

# Check job context is set
cur.execute("SELECT current_setting('ingestion.active_job_id', TRUE)")
active_job = cur.fetchone()[0]
```

## Key Files & Components

- `mcp_server/main.py` - FastAPI MCP server with function execution endpoints
- `mcp_server/utils/monitoring.py` - Trigger-based monitoring system
- `mcp_server/clients/` - API client libraries (congress, openstates, govinfo)
- `mcp_server/scripts/` - Ingestion scripts for each data source
- `mcp_server/sql/monitoring_triggers.sql` - Database triggers setup
- `tests/` - Comprehensive test suite with database/API markers

## Developer Workflows

### Setup & Run
```bash
# Environment setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Database setup
export DATABASE_URL=postgresql://user:pass@localhost:5432/opendiscourse
python mcp_server/db_init.py --all

# Run server
uvicorn mcp_server.main:app --reload --port 8080
```

### Testing
```bash
# Full test suite with coverage
pytest tests/ --cov=mcp_server --cov-report=term-missing --cov-fail-under=80

# Specific test categories
pytest -m "db"        # Database tests
pytest -m "api"       # External API tests  
pytest -m "unit"      # Unit tests
pytest -m "integration"  # Integration tests
```

### Ingestion Scripts
```bash
# Congress bills
python mcp_server/scripts/congress_ingest.py --congress 118 --per_page 50

# OpenStates data
python mcp_server/scripts/openstates_ingest.py --jurisdiction nc

# GovInfo documents
python mcp_server/scripts/govinfo_ingest.py --collection BILLS
```

## API Integration Limits

- **Congress.gov**: 5000 requests/hour, API key required
- **OpenStates**: 300 requests/minute, API key optional but recommended
- **GovInfo**: 1000 requests/hour, API key required

## Database Schema Patterns

### Key Tables
- `ingestion_jobs` - Job metadata and progress tracking
- `record_hashes` - Deduplication using content hashing
- `congress_*` - Federal legislative data
- `opencivicdata_*` - State legislative data  
- `govinfo_*` - Government publications

### Indexing Strategy
- GIN indexes on JSONB fields for fast searching
- Partial indexes for active records
- Composite indexes for common query patterns

## Error Handling Patterns

### Context Cleanup
```python
# Always clear job context on errors
try:
    with monitor.monitor_job(job_id):
        # ingestion code
except Exception as e:
    monitor._clear_job_context()  # Manual cleanup if needed
    raise
```

### Transaction Safety
- Failed inserts don't count toward progress (triggers only fire on successful INSERT)
- Use database transactions for multi-table operations
- Handle API rate limits with exponential backoff

## Common Pitfalls

1. **Forgetting context manager** - Leads to untracked progress
2. **Manual progress updates** - Conflicts with trigger system
3. **Missing trigger installation** - Progress won't be tracked
4. **Shared database connections** - Job context isolation issues
5. **API rate limit violations** - Respect documented limits

## Performance Optimization

- Batch database operations for bulk inserts
- Use connection pooling for concurrent operations
- Monitor trigger performance during long-running ingestions
- Index awareness when querying large tables (100M+ records possible)</content>
<parameter name="filePath">/home/cbwinslow/opendiscourse/.github/copilot-instructions.md