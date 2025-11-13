# Unified Ingestion System - Complete Workflow Documentation

## 🎯 Overview

The unified ingestion system consolidates 20+ scattered ingestion scripts into a single, production-ready interface for ingesting congressional and legislative data from multiple sources.

---

## 🏗️ System Architecture

### Data Sources
1. **Congress.gov** - Congressional bills, members, committees, votes, etc.
2. **GovInfo** - Official government publications and documents
3. **OpenStates** - State-level legislative data

### Core Components
- **`unified_ingestion_fixed.py`** - Main unified script
- **Database Layer** - PostgreSQL with optimized schemas
- **API Clients** - Standardized HTTP clients for each source
- **Monitoring Framework** - Comprehensive logging and metrics

---

## 🚀 Quick Start Guide

### Prerequisites
```bash
# Environment setup
source mcp_server/.env

# Database connectivity
export CONTAINER_IP=$(docker inspect mcp-postgres --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}')
export DATABASE_URL="postgresql://opendiscourse:opendiscourse123@${CONTAINER_IP}:5432/opendiscourse"
export PYTHONPATH=/home/cbwinslow/opendiscourse:$PYTHONPATH
```

### Basic Usage
```bash
# Ingest Congress members (118th Congress, 5 pages)
python unified_ingestion_fixed.py --source congress --data-type members --congress 118 --max-pages 5

# Ingest multiple data types
python unified_ingestion_fixed.py --source congress --data-type members committees --congress 118 --max-pages 3

# Ingest GovInfo data
python unified_ingestion_fixed.py --source govinfo --collection BILLS --year 2023

# Ingest OpenStates data
python unified_ingestion_fixed.py --source openstates --jurisdiction ca --per-page 50
```

---

## 📋 Command Line Interface Reference

### Global Parameters
```bash
python unified_ingestion_fixed.py [OPTIONS]
```

| Parameter | Type | Required | Default | Description |
|-----------|-------|----------|----------|-------------|
| `--source` | Choice | ✅ Required | - | Data source: congress, govinfo, openstates, all |
| `--data-type` | Choice[] | ❌ Optional | all | Congress data types (see below) |
| `--congress` | int[] | ❌ Optional | - | Congress number(s): 116, 117, 118, 119 |
| `--collection` | Choice | ❌ Optional | BILLS | GovInfo collection (see below) |
| `--year` | int | ❌ Optional | - | Year for GovInfo data |
| `--jurisdiction` | string | ❌ Optional | - | OpenStates jurisdiction code |
| `--query` | string | ❌ Optional | - | OpenStates search query |
| `--max-pages` | int | ❌ Optional | 10 | Maximum pages to ingest |
| `--per-page` | int | ❌ Optional | 20 | Records per page |
| `--timeout` | int | ❌ Optional | 300 | Script timeout in seconds |
| `--download-dir` | string | ❌ Optional | ./data | Download directory |
| `--dry-run` | flag | ❌ Optional | false | Show what would be executed |
| `--comprehensive` | flag | ❌ Optional | false | Run all available data types |

---

## 🏛️ Congress Data Types

### Available Data Types
```bash
--data-type {bills,members,committees,votes,bill_actions,bill_text,summaries,treaties,nominations,hearings,congress,all}
```

### Data Type Details

#### **bills**
- **Description**: Congressional bills and resolutions
- **Script**: `congress_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Bill metadata, status, sponsors, text links
- **Volume**: ~10,000+ bills per Congress

#### **members**
- **Description**: Congressional member profiles and information
- **Script**: `congress_members_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Member biographical data, party history, committees
- **Volume**: ~540 members total

#### **committees**
- **Description**: Congressional committees and subcommittees
- **Script**: `congress_committees_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Committee details, members, jurisdiction
- **Volume**: ~200+ committees

#### **votes**
- **Description**: Roll call votes and voting records
- **Script**: `congress_votes_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Vote details, positions, outcomes
- **Volume**: ~1,000+ votes per session

#### **bill_actions**
- **Description**: Legislative actions and proceedings
- **Script**: `congress_bill_actions_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Action chronology, dates, descriptions
- **Volume**: ~50,000+ actions

#### **bill_text**
- **Description**: Full text of bills and resolutions
- **Script**: `congress_bill_text_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Complete bill text, XML/HTML formats
- **Volume**: Large text data

#### **summaries**
- **Description**: Bill summaries and analyses
- **Script**: `congress_summaries_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Legislative summaries, CRS reports
- **Volume**: ~5,000+ summaries

#### **treaties**
- **Description**: International treaties and agreements
- **Script**: `congress_treaties_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Treaty text, status, parties
- **Volume**: ~100+ treaties

#### **nominations**
- **Description**: Presidential nominations
- **Script**: `congress_nominations_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Nomination details, status, votes
- **Volume**: ~1,500+ nominations

#### **hearings**
- **Description**: Committee hearing transcripts
- **Script**: `congress_hearings_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Hearing transcripts, witnesses, dates
- **Volume**: ~2,000+ hearings

#### **congress**
- **Description**: Congress metadata and sessions
- **Script**: `congress_congress_ingest.py`
- **Parameters**: `--congress`, `--max-pages`
- **Output**: Session dates, leadership, structure
- **Volume**: ~4 congresses

---

## 📚 GovInfo Collections

### Available Collections
```bash
--collection {BILLS,STATUTES,CRR,CRPT,CREC,FR,GPO}
```

### Collection Details

#### **BILLS**
- **Description**: Congressional bills from GovInfo
- **Parameters**: `--collection BILLS`, `--year`
- **Output**: Bill text, metadata, PDFs
- **Volume**: ~10,000+ bills/year

#### **STATUTES**
- **Description**: United States Code
- **Parameters**: `--collection STATUTES`, `--year`
- **Output**: Codified law, titles, sections
- **Volume**: Complete U.S. Code

#### **CRR** (Congressional Record)
- **Description**: Daily Congressional Record
- **Parameters**: `--collection CRR`, `--year`
- **Output**: Proceedings, debates, remarks
- **Volume**: Daily publications

#### **CRPT** (Committee Reports)
- **Description**: Committee reports and prints
- **Parameters**: `--collection CRPT`, `--year`
- **Output**: Report text, recommendations
- **Volume**: ~1,000+ reports/year

#### **CREC** (Congressional Record Electronic)
- **Description**: Electronic Congressional Record
- **Parameters**: `--collection CREC`, `--year`
- **Output**: Digital proceedings, searchable
- **Volume**: Daily electronic records

#### **FR** (Federal Register)
- **Description**: Federal Register publications
- **Parameters**: `--collection FR`, `--year`
- **Output**: Regulations, notices, proposed rules
- **Volume**: Daily publications

#### **GPO** (Government Publishing Office)
- **Description**: GPO publications
- **Parameters**: `--collection GPO`, `--year`
- **Output**: Various government documents
- **Volume**: Variable by year

---

## 🏛️ OpenStates Parameters

### Jurisdiction Codes
```bash
--jurisdiction {ca,ny,tx,fl,il,pa,oh,ga,nc,mj,...}
```

### Common Jurisdictions
| Code | State | Full Name |
|------|-------|-----------|
| ca | California | State of California |
| ny | New York | State of New York |
| tx | Texas | State of Texas |
| fl | Florida | State of Florida |
| il | Illinois | State of Illinois |
| pa | Pennsylvania | Commonwealth of Pennsylvania |
| oh | Ohio | State of Ohio |
| ga | Georgia | State of Georgia |
| nc | North Carolina | State of North Carolina |
| nj | New Jersey | State of New Jersey |

### Search Parameters
```bash
--query "healthcare"           # Search for healthcare bills
--query "budget 2024"         # Search for budget-related bills
--query "education funding"     # Search for education funding
```

---

## 🔄 Bulk Ingestion Workflows

### Single Congress, Multiple Data Types
```bash
# Ingest all data for 118th Congress (limited pages for testing)
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members committees votes \
  --congress 118 \
  --max-pages 5

# Comprehensive ingestion of 118th Congress
python unified_ingestion_fixed.py \
  --source congress \
  --congress 118 \
  --comprehensive \
  --max-pages 10
```

### Multiple Congresses
```bash
# Ingest members from recent congresses
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 116 117 118 \
  --max-pages 10

# Bulk ingestion across congresses
python unified_ingestion_fixed.py \
  --source congress \
  --congress 116 117 118 119 \
  --comprehensive \
  --max-pages 5
```

### Time-Based Ingestion
```bash
# Ingest by year for GovInfo
python unified_ingestion_fixed.py \
  --source govinfo \
  --collection BILLS \
  --year 2023 \
  --year 2024

# Multi-year ingestion
for year in 2020 2021 2022 2023 2024; do
  python unified_ingestion_fixed.py \
    --source govinfo \
    --collection BILLS \
    --year $year \
    --max-pages 5
done
```

### State-Level Data
```bash
# Ingest data for multiple states
for state in ca ny tx fl; do
  python unified_ingestion_fixed.py \
    --source openstates \
    --jurisdiction $state \
    --per-page 100 \
    --max-pages 10
done

# Search across states
python unified_ingestion_fixed.py \
  --source openstates \
  --jurisdiction ca \
  --query "climate change" \
  --per-page 50
```

---

## 📊 Output and Results

### Success Indicators
```bash
✅ CONGRESS - members_118
   📊 Records: 540
   ⏱️ Duration: 12.45s

📈 TOTALS:
   📊 Records Processed: 540
   ⏱️ Total Duration: 12.45s
   ❌ Total Errors: 0

🎉 All ingestions completed successfully!
```

### Error Handling
```bash
❌ CONGRESS - bills_118
   📊 Records: 0
   ⏱️ Duration: 2.15s
   ❌ Errors: 2
      - Script failed with return code 1
      - API rate limit exceeded
```

### Database Verification
```bash
# Check ingested records
psql "$DATABASE_URL" -c "
SELECT COUNT(*) as total_records,
       MIN(created_at) as first_record,
       MAX(created_at) as last_record
FROM congress_members
WHERE congress_id = 118;"

# Verify data quality
psql "$DATABASE_URL" -c "
SELECT bioguide_id, first_name, last_name, state, party_name
FROM congress_members
WHERE congress_id = 118
LIMIT 10;"
```

---

## ⚡ Performance Optimization

### Pagination Strategies
```bash
# Fast testing (small pages)
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 118 \
  --max-pages 1 \
  --per-page 10

# Production ingestion (larger pages)
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 118 \
  --max-pages 50 \
  --per-page 100
```

### Parallel Processing
```bash
# Run multiple data types in parallel
python unified_ingestion_fixed.py --source congress --data-type members --congress 118 &
PID1=$!
python unified_ingestion_fixed.py --source congress --data-type committees --congress 118 &
PID2=$!
python unified_ingestion_fixed.py --source congress --data-type votes --congress 118 &
PID3=$!

wait $PID1 $PID2 $PID3
```

### Resource Management
```bash
# Monitor system resources during ingestion
htop &                          # CPU/memory monitoring
iotop &                          # Disk I/O monitoring
nethogs &                         # Network monitoring

# Run ingestion with resource limits
timeout 3600 python unified_ingestion_fixed.py \
  --source congress \
  --comprehensive \
  --congress 118
```

---

## 🔧 Troubleshooting Guide

### Common Issues

#### Database Connection Errors
```bash
# Error: relation "congress_members" does not exist
# Solution: Create database schema
cd mcp_server/sql
psql "$DATABASE_URL" -f congress_schema.sql

# Error: could not connect to server
# Solution: Check container and IP
docker ps | grep postgres
docker inspect mcp-postgres --format='{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

#### API Rate Limiting
```bash
# Error: 429 Too Many Requests
# Solution: Reduce page size and add delays
python unified_ingestion_fixed.py \
  --source congress \
  --data-type bills \
  --congress 118 \
  --max-pages 1 \
  --per-page 10

# Add delay between requests
sleep 5  # Between batch requests
```

#### Environment Variable Issues
```bash
# Error: API key not found
# Solution: Source environment file
source mcp_server/.env
echo $CONGRESS_API_KEY  # Verify key exists

# Error: PYTHONPATH issues
# Solution: Set correct path
export PYTHONPATH=/home/cbwinslow/opendiscourse:$PYTHONPATH
python unified_ingestion_fixed.py --help
```

### Debug Mode
```bash
# Dry run to test parameters
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 118 \
  --dry-run

# Verbose logging
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 118 \
  --max-pages 1 2>&1 | tee ingestion.log
```

### Recovery Procedures
```bash
# Resume interrupted ingestion
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 118 \
  --max-pages 20 \
  --per-page 50

# Clean up partial data
psql "$DATABASE_URL" -c "
DELETE FROM congress_members 
WHERE congress_id = 118 
AND created_at < NOW() - INTERVAL '1 hour';"
```

---

## 📈 Monitoring and Metrics

### Real-time Monitoring
```bash
# Monitor ingestion progress
tail -f /var/log/ingestion.log

# Database activity monitoring
watch "psql '$DATABASE_URL' -c 'SELECT COUNT(*) FROM congress_members;'"

# System resource monitoring
watch -n 5 'ps aux | grep python | grep unified_ingestion'
```

### Performance Metrics
```bash
# Ingestion rate calculation
python -c "
start_time = '2024-01-01 10:00:00'
end_time = '2024-01-01 10:05:00'
records = 540
duration = 300  # seconds
rate = records / duration
print(f'Ingestion rate: {rate:.2f} records/second')
"

# Storage requirements
du -sh data/  # Download directory
psql "$DATABASE_URL" -c "pg_size_estimate('congress_members');"
```

---

## 🎯 Best Practices

### Production Deployment
1. **Environment Setup**
   ```bash
   # Use production database
   export DATABASE_URL="postgresql://user:pass@prod-host:5432/db"
   
   # Use production API keys
   source /etc/opendiscourse/production.env
   ```

2. **Error Handling**
   ```bash
   # Use screen sessions for long-running jobs
   screen -S congress_ingestion
   python unified_ingestion_fixed.py --source congress --comprehensive --congress 118
   ```

3. **Backup Strategy**
   ```bash
   # Database backup before bulk ingestion
   pg_dump "$DATABASE_URL" > backup_$(date +%Y%m%d_%H%M%S).sql
   
   # Verify backup integrity
   psql "$DATABASE_URL" < backup_20241113_120000.sql
   ```

### Data Quality
1. **Validation**
   ```bash
   # Check for duplicates
   psql "$DATABASE_URL" -c "
   SELECT bioguide_id, COUNT(*) 
   FROM congress_members 
   GROUP BY bioguide_id 
   HAVING COUNT(*) > 1;"
   
   # Check data completeness
   psql "$DATABASE_URL" -c "
   SELECT COUNT(*) as missing_state 
   FROM congress_members 
   WHERE state IS NULL;"
   ```

2. **Consistency Checks**
   ```bash
   # Cross-reference data sources
   psql "$DATABASE_URL" -c "
   SELECT c.bioguide_id, c.first_name, c.last_name
   FROM congress_members c
   LEFT JOIN congress_votes v ON c.bioguide_id = v.bioguide_id
   WHERE v.bioguide_id IS NULL
   LIMIT 10;"
   ```

---

## 📚 API Reference

### UnifiedIngester Class
```python
class UnifiedIngester:
    def __init__(self, dry_run: bool = False):
        """Initialize unified ingestion system"""
        
    def ingest(self, source: DataSource, **kwargs) -> List[IngestionResult]:
        """Main ingestion method"""
        
    def print_summary(self):
        """Print ingestion summary"""
```

### DataSource Enum
```python
class DataSource(Enum):
    CONGRESS = "congress"
    GOVINFO = "govinfo"
    OPENSTATES = "openstates"
    ALL = "all"
```

### IngestionResult Class
```python
@dataclass
class IngestionResult:
    source: str
    data_type: str
    success: bool
    records_processed: int
    duration: float
    errors: List[str]
    parameters: Dict[str, Any]
```

---

## 🔄 Advanced Workflows

### Automated Scheduling
```bash
# Crontab for daily updates
0 2 * * * cd /home/cbwinslow/opendiscourse && \
  python unified_ingestion_fixed.py \
    --source congress \
    --data-type members \
    --congress 118 \
    --max-pages 1

# Weekly comprehensive updates
0 3 * * 0 cd /home/cbwinslow/opendiscourse && \
  python unified_ingestion_fixed.py \
    --source congress \
    --comprehensive \
    --congress 118 \
    --max-pages 5
```

### Pipeline Integration
```bash
# CI/CD pipeline script
#!/bin/bash
set -e

echo "Starting automated ingestion..."

# Environment setup
source mcp_server/.env
export DATABASE_URL="postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME"

# Run ingestion
python unified_ingestion_fixed.py \
  --source $DATA_SOURCE \
  --data-type $DATA_TYPE \
  --congress $CONGRESS \
  --max-pages $MAX_PAGES

# Verify results
RECORDS=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM $TARGET_TABLE;")
echo "Ingested $RECORDS records"

# Notify on completion
curl -X POST "$WEBHOOK_URL" -d "Ingestion completed: $RECORDS records"
```

---

## 📞 Support and Resources

### Getting Help
```bash
# Command line help
python unified_ingestion_fixed.py --help

# Check system status
./monitoring_status.sh

# Database diagnostics
psql "$DATABASE_URL" -c "\dt"
```

### Log Locations
```bash
# Application logs
tail -f logs/ingestion.log

# Database logs
docker logs mcp-postgres

# System logs
journalctl -u opendiscourse -f
```

### Documentation
- **Complete API Reference**: `/docs/api-reference/`
- **Code Examples**: `/docs/examples/`
- **Troubleshooting**: `/docs/troubleshooting/`
- **Monitoring Guide**: `/docs/monitoring/`

---

*This documentation covers the complete unified ingestion system workflow from basic usage to advanced production deployment.*