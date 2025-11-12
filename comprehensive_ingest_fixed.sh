#!/bin/bash
# Comprehensive Ingestion Control Script - FIXED VERSION
# Handles deduplication, monitoring, and robust execution with timeout protection

set -e

echo "🚀 Starting Comprehensive Legislative Data Ingestion - FIXED VERSION"
echo "=================================================================="

# Load environment
if [ -f "mcp_server/.env" ]; then
    export $(cat mcp_server/.env | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ Error: mcp_server/.env file not found"
    exit 1
fi

# Configuration
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
MAX_PROC_TIME=3600  # 1 hour max per ingestion
MAX_PAGES=10        # Limit pages to prevent infinite loops
TIMEOUT=300         # 5 minutes timeout per API call

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" | tee -a "$LOG_DIR/ingestion_master_fixed.log"
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

# Function to run ingestion with timeout protection
run_ingestion() {
    local name=$1
    local command=$2
    local table=$3
    local requires_api=$4
    
    log "📥 Starting $name ingestion with timeout protection..."
    
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
    
    # Run with timeout and progress tracking
    log "⏰ Starting $name ingestion with $MAX_PROC_TIME second timeout..."
    log "🔍 Process monitoring enabled - will auto-kill if stuck"
    
    # Create a wrapper script for timeout and monitoring
    local wrapper_script="$LOG_DIR/${name,,}_wrapper.sh"
    cat > "$wrapper_script" << WRAPPER_EOF
#!/bin/bash
echo "Starting ingestion wrapper..."
cd /home/cbwinslow/opendiscourse
export PYTHONPATH=/home/cbwinslow/opendiscourse
$command
WRAPPER_EOF
    chmod +x "$wrapper_script"
    
    # Run with timeout and monitor
    local pid_file="$LOG_DIR/${name,,}_pid.txt"
    timeout $MAX_PROC_TIME bash "$wrapper_script" > "$LOG_DIR/${name,,}_ingestion.log" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"
    
    log "🔄 $name ingestion started (PID: $pid)"
    
    # Monitor the process
    local elapsed=0
    local last_size=0
    local stuck_count=0
    
    while kill -0 $pid 2>/dev/null; do
        elapsed=$((elapsed + 5))
        
        # Check if log file is growing
        local current_size=0
        if [ -f "$LOG_DIR/${name,,}_ingestion.log" ]; then
            current_size=\$(wc -c < "$LOG_DIR/${name,,}_ingestion.log" 2>/dev/null || echo 0)
        fi
        
        if [ $current_size -eq $last_size ]; then
            stuck_count=\$((stuck_count + 1))
            log "⏳ $name seems stuck (no log growth for \$((stuck_count * 5))s)"
            if [ $stuck_count -ge 12 ]; then  # 1 minute of no activity
                log "❌ $name appears to be stuck - killing process"
                kill -9 $pid 2>/dev/null || true
                break
            fi
        else
            stuck_count=0
            last_size=$current_size
        fi
        
        # Show progress
        local runtime=\$((elapsed / 60))
        log "⏱️  $name running for \${runtime}m... (PID: $pid)"
        
        sleep 5
    done
    
    # Check if process finished successfully
    if wait $pid 2>/dev/null; then
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
        log "❌ $name ingestion failed or timed out"
        return 1
    fi
    
    # Cleanup
    rm -f "$pid_file" "$wrapper_script"
}

# Pre-ingestion health check with timeout
log "🔍 Running pre-ingestion health checks..."

# Test database connection with timeout
if timeout 30 DB_URL="$DATABASE_URL" python -c "
import psycopg2, os, signal
def timeout_handler(signum, frame):
    print('TIMEOUT')
    exit(1)
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(25)
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

# Test API keys with timeout
log "🔑 Testing API keys..."
if timeout 30 python -c "
import requests, signal
def timeout_handler(signum, frame):
    print('TIMEOUT')
    exit(1)
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(25)
response = requests.get('https://api.congress.gov/v3/bill', params={'api_key': '$CONGRESS_API_KEY', 'limit': 1}, timeout=20)
print(response.status_code)
" | grep -q "200"; then
    log "✅ Congress API key valid"
else
    log "❌ Congress API key invalid"
    exit 1
fi

if timeout 30 python -c "
import requests, signal
def timeout_handler(signum, frame):
    print('TIMEOUT')
    exit(1)
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(25)
response = requests.get('https://api.govinfo.gov/collections', params={'api_key': '$GOVINFO_API_KEY'}, timeout=20)
print(response.status_code)
" | grep -q "200"; then
    log "✅ GovInfo API key valid"
else
    log "❌ GovInfo API key invalid"
    exit 1
fi

if [ -n "${OPENSTATES_API_KEY:-}" ]; then
    if timeout 60 python -c "
import requests, signal
def timeout_handler(signum, frame):
    print('TIMEOUT')
    exit(1)
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(55)
response = requests.get('https://v3.openstates.org/bills', params={'apikey': '$OPENSTATES_API_KEY', 'per_page': 1, 'jurisdiction': 'us'}, timeout=50)
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

# Run ingestions with safeguards
log ""
log "🏃 Running data ingestions with safeguards..."

# Clean up any existing stuck processes
pkill -f "mcp_server/scripts/congress_ingest.py" || true
pkill -f "mcp_server/scripts/openstates_ingest.py" || true
pkill -f "mcp_server/scripts/govinfo_ingest.py" || true

# Run with limited pages and safety timeouts
run_ingestion "Congress" "timeout 600 .venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118 --page 1 --max-pages $MAX_PAGES --timeout $TIMEOUT" "congress_bills" "false" || log "⚠️  Congress ingestion had issues but continuing..."
run_ingestion "OpenStates" "timeout 600 .venv/bin/python mcp_server/scripts/openstates_ingest.py --jurisdiction us --per_page 25 --max-pages 5 --timeout $TIMEOUT" "opencivicdata_bill" "true" || log "⚠️  OpenStates ingestion had issues but continuing..."
run_ingestion "GovInfo" "timeout 600 .venv/bin/python mcp_server/scripts/govinfo_ingest.py --collection BILLS --max-pages 3 --timeout $TIMEOUT" "govinfo_documents" "false" || log "⚠️  GovInfo ingestion had issues but continuing..."

# Post-ingestion validation
log ""
log "🔍 Running post-ingestion validation..."

# Check for any new duplicates
python -c "
import psycopg2
import os
import signal

def timeout_handler(signum, frame):
    print('TIMEOUT in validation')
    exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

tables = [
    ('congress_bills', 'bill_id'),
    ('govinfo_documents', 'id'),
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
" >> "$LOG_DIR/ingestion_master_fixed.log"

log ""
log "🎉 Comprehensive ingestion completed (FIXED VERSION)!"
log "📋 Check logs in ./logs/ directory"
log "📊 Run './monitor_ingestion.sh' for current status"
log "🔍 This version includes timeout protection and progress monitoring"
