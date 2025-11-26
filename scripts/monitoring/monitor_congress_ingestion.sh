#!/bin/bash
# Congress Ingestion Progress Monitor
# Monitors the progress of automated Congress data ingestion jobs

set -e

echo "📊 Congress Data Ingestion Progress Monitor"
echo "==========================================="

# Configuration
LOG_DIR="/home/cbwinslow/opendiscourse/logs"
SCRIPT_DIR="/home/cbwinslow/opendiscourse/mcp_server/scripts"
DB_URL="postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse"

# Congress numbers
CONGRESSES=(109 110 111 112 113 114 115 116 117 118 119)

echo "🔍 Checking ingestion status..."
echo ""

# Function to get job status from database
get_job_status() {
    local congress=$1
    local data_type=$2

    # Query database for job status
    python3 -c "
import psycopg2
import os
os.environ['DATABASE_URL'] = '$DB_URL'

try:
    conn = psycopg2.connect('$DB_URL')
    cur = conn.cursor()

    # Try different collection name patterns
    patterns = [
        f'{data_type}_{congress}',           # bills_118
        f'{data_type}_{congress}_all',       # bills_118_all, committees_118_all
        f'{data_type}_{congress}_all_all'    # members_118_all_all
    ]

    result = None
    for pattern in patterns:
        cur.execute('''
            SELECT status, processed_records, total_records, created_at, updated_at
            FROM ingestion_jobs
            WHERE source = 'congress' AND collection = %s
            ORDER BY created_at DESC
            LIMIT 1
        ''', (pattern,))

        result = cur.fetchone()
        if result:
            break

    if result:
        status, processed, total, created, updated = result
        print(f'{status}|{processed or 0}|{total or 0}|{created.strftime(\"%Y-%m-%d %H:%M\")}|{updated.strftime(\"%Y-%m-%d %H:%M\")}')
    else:
        print('not_started|0|0|never|never')

    cur.close()
    conn.close()
except Exception as e:
    print(f'error|0|0|error|error')
" 2>/dev/null || echo "db_error|0|0|error|error"
}

# Function to check if cron job ran today
check_cron_execution() {
    local congress=$1
    local script_name="ingest_congress_${congress}.sh"
    local log_pattern="${LOG_DIR}/congress_${congress}_ingestion_$(date +%Y%m%d)_*.log"

    if ls $log_pattern 1> /dev/null 2>&1; then
        echo "✅ Ran today"
        # Get the latest log file
        latest_log=$(ls -t $log_pattern | head -1)
        echo "   📄 Latest log: $(basename $latest_log)"
        # Check if completed successfully
        if tail -5 "$latest_log" | grep -q "ingestion completed"; then
            echo "   ✅ Completed successfully"
        elif tail -5 "$latest_log" | grep -q "error\|Error\|ERROR"; then
            echo "   ❌ Completed with errors"
        else
            echo "   ⏳ Still running or incomplete"
        fi
    else
        echo "❌ Not run today"
    fi
}

# Display progress for each Congress
for congress in "${CONGRESSES[@]}"; do
    echo "🏛️  Congress $congress ($(date -d "01/01/$((1789 + 2*(congress-1)))" +%Y)-$(date -d "01/01/$((1789 + 2*congress - 1))" +%Y))"
    echo "   ──────────────────────────────────────────────────────────"

    # Check cron execution
    echo "   📅 Cron Status: $(check_cron_execution $congress)"

    # Check database status for key data types
    data_types=("bills" "members" "committees" "votes")
    for data_type in "${data_types[@]}"; do
        status_info=$(get_job_status $congress $data_type)
        IFS='|' read -r status processed total created updated <<< "$status_info"

        case $status in
            "completed")
                echo "   📊 $data_type: ✅ $processed records ($updated)"
                ;;
            "running")
                echo "   📊 $data_type: ⏳ $processed/$total records ($updated)"
                ;;
            "failed")
                echo "   📊 $data_type: ❌ Failed ($updated)"
                ;;
            "not_started")
                echo "   📊 $data_type: ⏸️  Not started"
                ;;
            "db_error")
                echo "   📊 $data_type: 🔌 Database connection error"
                ;;
            *)
                echo "   📊 $data_type: ❓ Unknown status"
                ;;
        esac
    done

    echo ""
done

echo "📈 Summary Statistics"
echo "===================="

# Calculate overall progress
total_jobs=0
completed_jobs=0
running_jobs=0
failed_jobs=0

for congress in "${CONGRESSES[@]}"; do
    for data_type in "${data_types[@]}"; do
        ((total_jobs++))
        status_info=$(get_job_status $congress $data_type)
        IFS='|' read -r status processed total created updated <<< "$status_info"

        case $status in
            "completed") ((completed_jobs++)) ;;
            "running") ((running_jobs++)) ;;
            "failed") ((failed_jobs++)) ;;
        esac
    done
done

echo "📊 Total Jobs: $total_jobs"
echo "✅ Completed: $completed_jobs"
echo "⏳ Running: $running_jobs"
echo "❌ Failed: $failed_jobs"
echo "📈 Progress: $(( (completed_jobs * 100) / total_jobs ))%"

echo ""
echo "🔍 Recent Activity (last 24 hours)"
echo "==================================="

# Show recent log files
echo "📄 Latest ingestion logs:"
find "$LOG_DIR" -name "congress_*_ingestion_$(date +%Y%m%d)_*.log" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -5 | while read -r timestamp filepath; do
    printf "   %s: %s\n" "$(date -d "@$timestamp" +%H:%M)" "$(basename "$filepath" .log)"
done

echo ""
echo "💡 Tips:"
echo "   • Check individual logs: tail -f $LOG_DIR/congress_*_ingestion_*.log"
echo "   • View cron jobs: crontab -l"
echo "   • Monitor database: Use the MCP server monitoring endpoints"
echo "   • Run manually: bash $SCRIPT_DIR/ingest_congress_<number>.sh"