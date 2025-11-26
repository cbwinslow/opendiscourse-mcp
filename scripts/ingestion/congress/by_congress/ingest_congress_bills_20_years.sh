#!/bin/bash
# 20-Year Congress Bills Data Ingestion Script
# Focuses on bills data first, which we know works
# Generated on $(date)

set -e

echo "🏛️  Starting 20-Year Congress Bills Ingestion - $(date)"
echo "======================================================"
echo "Target Congresses: 105-118 (approximately 1997-2025)"
echo "Focus: Bills data (known working)"
echo ""

# Load environment
source "/home/cbwinslow/opendiscourse/.venv/bin/activate"
export DATABASE_URL="postgresql://opendiscourse:opendiscourse123@100.90.251.120:5432/opendiscourse"
export CONGRESS_API_KEY="U71JFZEqNsiSranCdbrj4pZaobtoMtAnl18cIJc2"
export PYTHONPATH="/home/cbwinslow/opendiscourse"

# Create logs directory if it doesn't exist
mkdir -p logs

# Log file
LOG_FILE="logs/20_year_bills_ingestion_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "📊 Processing bills data for 20 years..."
echo "📁 Log file: $LOG_FILE"
echo ""

# Congress numbers to process (105-118 covers ~1997-2025)
CONGRESSES=(105 106 107 108 109 110 111 112 113 114 115 116 117 118)
TOTAL_CONGRESSES=${#CONGRESSES[@]}
SUCCESS_COUNT=0

echo "🎯 Will process bills for $TOTAL_CONGRESSES Congresses: ${CONGRESSES[*]}"
echo ""

for CONGRESS in "${CONGRESSES[@]}"; do
    echo "======================================================"
    echo "🏛️  Processing Congress $CONGRESS Bills - $(date)"
    echo "======================================================"

    CONGRESS_START=$(( (CONGRESS-1)*2 + 1789 ))
    CONGRESS_END=$(( CONGRESS*2 + 1789 ))
    echo "📅 Approximate years: $CONGRESS_START-$CONGRESS_END"

    # Run bills ingestion for this Congress (limit pages to avoid timeouts)
    if python mcp_server/scripts/congress_ingest.py \
        --congress $CONGRESS \
        --max_pages 10; then

        echo "✅ Congress $CONGRESS bills completed successfully"
        ((SUCCESS_COUNT++))
    else
        echo "❌ Congress $CONGRESS bills failed - continuing with next Congress"
    fi

    echo ""
    echo "📈 Progress: $SUCCESS_COUNT/$TOTAL_CONGRESSES Congresses completed"
    echo ""

    # Brief pause between Congresses to be respectful to the API
    sleep 3
done

echo "======================================================"
echo "🎉 20-Year Bills Ingestion Complete - $(date)"
echo "======================================================"
echo "Successfully processed bills for: $SUCCESS_COUNT/$TOTAL_CONGRESSES Congresses"
echo "Log file: $LOG_FILE"
echo ""

# Final database check
echo "📊 Final Database Status:"
python check_db.py

echo ""
echo "✅ 20-year Congress bills data ingestion completed!"
