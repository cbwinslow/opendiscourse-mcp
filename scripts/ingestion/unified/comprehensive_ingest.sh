#!/bin/bash
# Comprehensive Ingestion Control Script
# Handles deduplication, monitoring, and robust execution

set -e

echo "🚀 Starting Comprehensive Legislative Data Ingestion"
echo "=================================================="

# Load environment
if [ -f "mcp_server/.env" ]; then
    export $(cat mcp_server/.env | xargs)
    echo "✅ Environment variables loaded"
else
    log "❌ Error: mcp_server/.env file not found"
    exit 1
fi

# Configuration
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/ingestion_master.log"
}

# Function to check for duplicates
check_duplicates() {
    local table=$1
    local desc=$2
    DB_URL="$DATABASE_URL" python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DB_URL'])
cur = conn.cursor()
try:
    if '$table' == 'congress_bills':
        cur.execute('SELECT COUNT(*) FROM (SELECT bill_id, COUNT(*) as cnt FROM congress_bills GROUP BY bill_id HAVING COUNT(*) > 1) as dupes;')
    elif '$table' == 'govinfo_packages':
        cur.execute('SELECT COUNT(*) FROM (SELECT id, COUNT(*) as cnt FROM govinfo_packages GROUP BY id HAVING COUNT(*) > 1) as dupes;')
    elif '$table' == 'opencivicdata_bill':
        cur.execute('SELECT COUNT(*) FROM (SELECT id, COUNT(*) as cnt FROM opencivicdata_bill GROUP BY id HAVING COUNT(*) > 1) as dupes;')
    duplicates = cur.fetchone()[0]
    print(duplicates)
except Exception as e:
    print(f'Error: {e}')
finally:
    cur.close()
    conn.close()
" 2>/dev/null
}

# Function to get table count
get_count() {
    local table=$1
    DB_URL="$DATABASE_URL" python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DB_URL'])
cur = conn.cursor()
try:
    cur.execute('SELECT COUNT(*) FROM $table;')
    count = cur.fetchone()[0]
    print(count)
except Exception as e:
    print('0')
finally:
    cur.close()
    conn.close()
" 2>/dev/null
}

# Function to run ingestion with monitoring
run_ingestion() {
    local name=$1
    local command=$2
    local table=$3
    local requires_api=$4
    
    log "📥 Starting $name ingestion..."
    
    # Check if API key is required and available
    if [ "$requires_api" = "true" ]; then
        if [ -z "${OPENSTATES_API_KEY:-}" ]; then
            log "⚠️  Skipping $name ingestion - API key not configured"
            return 0
        fi
    fi
    
    # Get count before
    local count_before=$(get_count "$table")
    
    local start_time=$(date +%s)
    if eval "$command" >> "$LOG_DIR/${name,,}_ingestion.log" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Get count after
        local count_after=$(get_count "$table")
        local new_records=$((count_after - count_before))
        
        # Check for duplicates
        local duplicates=$(check_duplicates "$table" "$name")
        
        log "✅ $name ingestion completed in ${duration}s"
        log "   📊 Records: $count_before → $count_after (added: $new_records)"
        if [ "$duplicates" -gt 0 ]; then
            log "   ⚠️  Duplicates found: $duplicates"
        else
            log "   ✅ No duplicates detected"
        fi
    else
        log "❌ $name ingestion failed"
        return 1
    fi
}

# Pre-ingestion health check
log "🔍 Running pre-ingestion health checks..."

# Test database connection
if DB_URL="$DATABASE_URL" python -c "
import psycopg2, os
try:
    conn = psycopg2.connect(os.environ['DB_URL'])
    conn.close()
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    exit(1)
" 2>/dev/null | grep -q "OK"; then
    log "✅ Database connection OK"
else
    log "❌ Database connection failed"
    exit 1
fi
log "✅ Database connection OK"

# Test API keys
log "🔑 Testing API keys..."
if python -c "
import requests
response = requests.get('https://api.congress.gov/v3/bill', params={'api_key': '$CONGRESS_API_KEY', 'limit': 1}, timeout=10)
print(response.status_code)
" | grep -q "200"; then
    log "✅ Congress API key valid"
else
    log "❌ Congress API key invalid"
    exit 1
fi

if python -c "
import requests
response = requests.get('https://api.govinfo.gov/collections', params={'api_key': '$GOVINFO_API_KEY'}, timeout=10)
print(response.status_code)
" | grep -q "200"; then
    log "✅ GovInfo API key valid"
else
    log "❌ GovInfo API key invalid"
    exit 1
fi

if [ -n "${OPENSTATES_API_KEY:-}" ]; then
    if python -c "
import requests
response = requests.get('https://v3.openstates.org/bills', params={'apikey': '$OPENSTATES_API_KEY', 'per_page': 1, 'jurisdiction': 'us'}, timeout=30)
print(response.status_code)
" | grep -q "200"; then
        log "✅ OpenStates API key valid"
    else
        log "❌ OpenStates API key invalid"
        exit 1
    fi
else
    log "⚠️  OpenStates API key not configured - will skip OpenStates ingestion"
fi

# Run ingestions
log ""
log "🏃 Running data ingestions..."

run_ingestion "Congress" "PYTHONPATH=/home/cbwinslow/opendiscourse timeout 300 .venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118 --page 1 --max_pages 2" "congress_bills" "false"
# run_ingestion "Congress Summaries" "PYTHONPATH=/home/cbwinslow/opendiscourse timeout 300 .venv/bin/python mcp_server/scripts/congress_summaries_ingest.py --congress 118 --max_pages 2" "congress_summaries" "false"
run_ingestion "Congress Treaties" "PYTHONPATH=/home/cbwinslow/opendiscourse timeout 300 .venv/bin/python mcp_server/scripts/congress_treaties_ingest.py --congress 118 --max_pages 2" "congress_treaties" "false"
run_ingestion "Congress Nominations" "PYTHONPATH=/home/cbwinslow/opendiscourse timeout 300 .venv/bin/python scripts/ingestion/congress/congress_nominations_ingest.py --congress 118 --max_pages 2" "congress_nominations" "false"
run_ingestion "Congress Hearings" "PYTHONPATH=/home/cbwinslow/opendiscourse timeout 300 .venv/bin/python scripts/ingestion/congress/congress_hearings_ingest.py --congress 118 --max_pages 2" "congress_hearings" "false"
run_ingestion "Congress Info" "PYTHONPATH=/home/cbwinslow/opendiscourse timeout 300 .venv/bin/python scripts/ingestion/congress/congress_congress_ingest.py --congress 118" "congress_congress" "false"
run_ingestion "OpenStates" "PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction us --per_page 50" "opencivicdata_bill" "true"
run_ingestion "GovInfo" "PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python scripts/ingestion/govinfo/govinfo_ingest.py --collection BILLS" "govinfo_packages" "false"

# Post-ingestion validation
log ""
log "🔍 Running post-ingestion validation..."

# Check for any new duplicates
python -c "
import psycopg2
import os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

tables = [
    ('congress_bills', 'bill_id'),
    ('govinfo_packages', 'id'),
    ('opencivicdata_bill', 'id')
]

total_duplicates = 0
for table, id_col in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM (SELECT {id_col}, COUNT(*) as cnt FROM {table} GROUP BY {id_col} HAVING COUNT(*) > 1) as dupes;')
        duplicates = cur.fetchone()[0]
        if duplicates > 0:
            print(f'⚠️  {table}: {duplicates} duplicates found')
            total_duplicates += duplicates
    except Exception as e:
        print(f'Error checking {table}: {e}')

if total_duplicates == 0:
    print('✅ No duplicates detected in any table')
else:
    print(f'⚠️  Total duplicates found: {total_duplicates}')

cur.close()
conn.close()
" >> "$LOG_DIR/ingestion_master.log"

log ""
log "🎉 Comprehensive ingestion completed!"
log "📋 Check logs in ./logs/ directory"
log "📊 Run './monitor_ingestion.sh' for current status"