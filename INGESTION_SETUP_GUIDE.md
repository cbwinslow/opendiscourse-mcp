# OpenDiscourse Ingestion Setup Guide

## Overview
Your homelab PostgreSQL database ingestion processes are now configured! This guide explains how to run and manage the automated data ingestion from Congress.gov, OpenStates, and GovInfo APIs.

## Current Setup

### Database
- **Location**: `postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse`
- **Schemas**: Congress, GovInfo, OpenStates (all initialized ✅)
- **Status**: Connected and ready ✅

### Automated Processes
- **Congress Data**: Daily at 2:00 AM
- **OpenStates Data**: Daily at 3:00 AM
- **GovInfo Data**: Daily at 4:00 AM
- **Health Checks**: Every 6 hours

### API Keys Status
- **Congress API**: ❌ Invalid/expired (needs update)
- **GovInfo API**: ✅ Working
- **OpenStates API**: ❓ Not tested (no API key required)

## Quick Start

### 1. Start the MCP Server
```bash
./start_server.sh
```
Server will be available at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 2. Run Manual Ingestion Test
```bash
./manual_ingest.sh
```

### 3. Monitor System
```bash
./monitor_ingestion.sh
```

## API Key Management

### Getting New API Keys

#### Congress.gov API
1. Visit: https://api.congress.gov/
2. Sign up for an API key
3. Update `mcp_server/.env`:
```bash
CONGRESS_API_KEY="your_new_api_key_here"
```

#### GovInfo API
1. Visit: https://www.govinfo.gov/developers
2. Request an API key
3. Update `mcp_server/.env`:
```bash
GOVINFO_API_KEY="your_new_api_key_here"
```

#### OpenStates API
- No API key required (rate limited)
- Uses OpenCivicData API endpoints

### Testing API Keys
```bash
# Test Congress API
curl "https://api.congress.gov/bill?page=1&congress=118&api_key=YOUR_KEY"

# Test GovInfo API
curl "https://api.govinfo.gov/collections?api_key=YOUR_KEY"
```

## Ingestion Management

### Manual Ingestion
Run specific ingestion scripts:

```bash
# Congress bills
PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118

# OpenStates data
PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python mcp_server/scripts/openstates_ingest.py --jurisdiction us --entity bills

# GovInfo documents
PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python mcp_server/scripts/govinfo_ingest.py --collection BILLS
```

### API-Based Ingestion
When the server is running, trigger ingestion via REST API:

```bash
# Congress ingestion
curl -X POST "http://localhost:8000/mcp/ingest_data" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "admin",
    "site": "congress",
    "database_url": "postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse",
    "ingestion_mode": "incremental"
  }'

# GovInfo ingestion
curl -X POST "http://localhost:8000/mcp/ingest_data" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "admin",
    "site": "govinfo",
    "database_url": "postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse",
    "ingestion_mode": "incremental"
  }'
```

### Querying Data
```bash
# Get recent bills
curl "http://localhost:8000/mcp/query_data?user_id=admin&database_url=postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse&table=congress_bills&limit=5"

# Get GovInfo packages
curl "http://localhost:8000/mcp/query_data?user_id=admin&database_url=postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse&table=govinfo_packages&limit=5"
```

## Monitoring & Troubleshooting

### Log Files
- `logs/congress_ingestion.log`
- `logs/openstates_ingestion.log`
- `logs/govinfo_ingestion.log`
- `logs/health_check.log`

### Common Issues

#### 1. API Key Expired
**Symptoms**: HTTP 403/404 errors
**Solution**: Get new API keys and update `.env` file

#### 2. Database Connection Failed
**Symptoms**: Connection timeout errors
**Solution**: Check PostgreSQL server status and network connectivity

#### 3. Module Import Errors
**Symptoms**: `ModuleNotFoundError`
**Solution**: Ensure `PYTHONPATH` is set correctly

#### 4. NumPy Compatibility
**Symptoms**: NumPy version conflicts
**Solution**: Run `pip install "numpy<2"` in virtual environment

### Health Checks
```bash
# Check database connectivity
psql "postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse" -c "SELECT 1;"

# Check table counts
psql "postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse" -c "
SELECT 'congress_bills' as table, COUNT(*) FROM congress_bills
UNION ALL
SELECT 'openstates_bills', COUNT(*) FROM openstates_bills
UNION ALL
SELECT 'govinfo_packages', COUNT(*) FROM govinfo_packages;
"
```

## Advanced Configuration

### Customizing Ingestion Parameters
Edit the cron jobs in `crontab -e`:
```bash
# Current: Congress 118th congress
0 2 * * * cd /home/cbwinslow/opendiscourse && export $(cat mcp_server/.env | xargs) && PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118

# Change to different congress
0 2 * * * cd /home/cbwinslow/opendiscourse && export $(cat mcp_server/.env | xargs) && PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python mcp_server/scripts/congress_ingest.py --congress 119
```

### Adding New Data Sources
1. Create new ingestion script in `mcp_server/scripts/`
2. Add API client in `mcp_server/clients/`
3. Update `main.py` endpoints
4. Add to cron jobs

### Backup Strategy
```bash
# Database backup
pg_dump "postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse" > opendiscourse_backup_$(date +%Y%m%d).sql

# Restore backup
psql "postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse" < opendiscourse_backup_20241201.sql
```

## Performance Tuning

### Database Optimization
```sql
-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_congress_bills_congress ON congress_bills(congress);
CREATE INDEX IF NOT EXISTS idx_congress_bills_bill_type ON congress_bills(bill_type);
CREATE INDEX IF NOT EXISTS idx_govinfo_packages_date ON govinfo_packages(date_issued DESC);
```

### Rate Limiting
- Congress API: 5,000 requests/hour
- GovInfo API: 1,000 requests/hour
- OpenStates: No specific limits

### Memory Management
- Monitor memory usage with `htop` or `ps aux`
- Adjust batch sizes in ingestion scripts if needed
- Consider distributed processing for large datasets

## Next Steps

1. **Update API Keys**: Get valid Congress.gov API key
2. **Test Ingestion**: Run `./manual_ingest.sh` after key updates
3. **Monitor Daily**: Check logs and run `./monitor_ingestion.sh`
4. **Scale Up**: Consider adding more data sources or increasing frequency
5. **Backup**: Set up automated database backups

## Support

- Check logs in `./logs/` directory
- Run `./monitor_ingestion.sh` for system status
- Test API endpoints at http://localhost:8000/docs
- Verify database connectivity with psql commands

Your ingestion system is ready! Just update the API keys and you'll be collecting legislative data automatically. 🎯