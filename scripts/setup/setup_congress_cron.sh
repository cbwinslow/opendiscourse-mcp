#!/bin/bash
# Congress Data Ingestion Cron Setup
# Creates cron jobs for ingesting all Congress data by Congress number

set -e

echo "🏛️  Setting up Congress Data Ingestion Cron Jobs"
echo "================================================"

# Configuration
SCRIPT_DIR="/home/cbwinslow/opendiscourse/mcp_server/scripts"
LOG_DIR="/home/cbwinslow/opendiscourse/logs"
VENV_PATH="/home/cbwinslow/opendiscourse/.venv/bin/activate"
DB_URL="postgresql://opendiscourse:opendiscourse123@100.90.251.120:5432/opendiscourse"
API_KEY="U71JFZEqNsiSranCdbrj4pZaobtoMtAnl18cIJc2"

# Create log directory
mkdir -p "$LOG_DIR"

# Congress numbers to process (last 20 years: 109-119)
CONGRESSES=(109 110 111 112 113 114 115 116 117 118 119)

# Data types to ingest
DATA_TYPES=("bills" "members" "committees" "votes" "bill_actions" "bill_text" "summaries" "treaties" "nominations" "hearings" "congress")

echo "📝 Creating individual ingestion scripts..."

# Create individual scripts for each Congress
for congress in "${CONGRESSES[@]}"; do
    script_name="ingest_congress_${congress}.sh"
    script_path="$SCRIPT_DIR/$script_name"

    cat > "$script_path" << EOF
#!/bin/bash
# Congress ${congress} Data Ingestion Script
# Generated on $(date)

set -e

echo "🏛️  Starting Congress ${congress} Data Ingestion - \$(date)"
echo "======================================================"

# Load environment
source "$VENV_PATH"
export DATABASE_URL="$DB_URL"
export CONGRESS_API_KEY="$API_KEY"
export PYTHONPATH="/home/cbwinslow/opendiscourse"

# Log file
LOG_FILE="$LOG_DIR/congress_${congress}_ingestion_\$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "\$LOG_FILE") 2>&1

echo "📊 Processing Congress ${congress} data..."
echo "📁 Log file: \$LOG_FILE"

# Run comprehensive ingestion for this Congress
python mcp_server/scripts/congress_comprehensive_ingest.py \\
    --congress ${congress} \\
    --max_pages 50 \\
    --list-scripts > /dev/null && \\
python mcp_server/scripts/congress_comprehensive_ingest.py \\
    --congress ${congress} \\
    --max_pages 50 \\
    --scripts bills members committees votes bill_actions bill_text summaries treaties nominations hearings congress

echo "✅ Congress ${congress} ingestion completed - \$(date)"
EOF

    chmod +x "$script_path"
    echo "  ✅ Created $script_name"
done

echo ""
echo "⏰ Setting up cron jobs..."

# Create cron job entries
CRON_ENTRIES=""

# Stagger the jobs to avoid overwhelming the API
# Run one Congress per day, starting tomorrow
day_offset=1
for congress in "${CONGRESSES[@]}"; do
    # Calculate day of month (1-28 to avoid month issues)
    day_of_month=$(( (day_offset - 1) % 28 + 1 ))

    # Run at 2 AM on the calculated day
    cron_time="0 2 $day_of_month * *"

    script_path="$SCRIPT_DIR/ingest_congress_${congress}.sh"
    cron_entry="$cron_time $script_path"

    CRON_ENTRIES+="$cron_entry\\n"

    echo "  📅 Congress $congress -> $cron_time"
    ((day_offset++))
done

echo ""
echo "📋 Cron job entries to add:"
echo "=========================="
echo -e "$CRON_ENTRIES"
echo "=========================="

# Create a script to add these to crontab
CRON_SETUP_SCRIPT="$SCRIPT_DIR/setup_congress_cron.sh"
cat > "$CRON_SETUP_SCRIPT" << EOF
#!/bin/bash
# Add Congress ingestion cron jobs to crontab

echo "Adding Congress ingestion cron jobs..."

# Backup current crontab
crontab -l > /tmp/crontab_backup_\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Add new entries
(crontab -l 2>/dev/null || true; echo "# Congress Data Ingestion Jobs"; echo -e "$CRON_ENTRIES") | crontab -

echo "✅ Cron jobs added successfully"
echo "📋 Current crontab:"
crontab -l
EOF

chmod +x "$CRON_SETUP_SCRIPT"

echo ""
echo "🎯 Setup complete!"
echo "=================="
echo "📁 Individual scripts created in: $SCRIPT_DIR"
echo "📊 Logs will be saved to: $LOG_DIR"
echo "⏰ Run this to add cron jobs: $CRON_SETUP_SCRIPT"
echo ""
echo "📈 Monitoring:"
echo "  - Check logs: tail -f $LOG_DIR/congress_*_ingestion_*.log"
echo "  - View cron jobs: crontab -l"
echo "  - Monitor database: Use the monitoring tools in the project"
echo ""
echo "🚀 Ready to ingest data for Congresses: ${CONGRESSES[*]}"