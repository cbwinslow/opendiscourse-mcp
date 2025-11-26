#!/bin/bash
# 20-Year Congress Data Ingestion Script
# Ingests comprehensive legislative data for Congresses 105-118 (1997-2025)
# Generated on $(date)

set -e

echo "🏛️  Starting 20-Year Congress Data Ingestion - $(date)"
echo "======================================================"
echo "Target Congresses: 105-118 (approximately 1997-2025)"
echo "This will ingest: bills, members, committees, votes, actions, text, summaries, treaties, nominations, hearings"
echo ""

# Load environment
source "/home/cbwinslow/opendiscourse/.venv/bin/activate"
export DATABASE_URL="postgresql://opendiscourse:opendiscourse123@100.90.251.120:5432/opendiscourse"
export CONGRESS_API_KEY="U71JFZEqNsiSranCdbrj4pZaobtoMtAnl18cIJc2"
export PYTHONPATH="/home/cbwinslow/opendiscourse"

# Create logs directory if it doesn't exist
mkdir -p logs

# Log file
LOG_FILE="logs/20_year_congress_ingestion_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "📊 Processing 20 years of Congress data..."
echo "📁 Log file: $LOG_FILE"
echo ""

# Congress numbers to process (105-118 covers ~1997-2025)
CONGRESSES=(105 106 107 108 109 110 111 112 113 114 115 116 117 118)
TOTAL_CONGRESSES=${#CONGRESSES[@]}
SUCCESS_COUNT=0

echo "🎯 Will process $TOTAL_CONGRESSES Congresses: ${CONGRESSES[*]}"
echo ""

for CONGRESS in "${CONGRESSES[@]}"; do
    echo "======================================================"
    echo "🏛️  Processing Congress $CONGRESS - $(date)"
    echo "======================================================"

    CONGRESS_START=$(( (CONGRESS-1)*2 + 1789 ))
    CONGRESS_END=$(( CONGRESS*2 + 1789 ))
    echo "📅 Approximate years: $CONGRESS_START-$CONGRESS_END"

    # Run comprehensive ingestion for this Congress
    if python mcp_server/scripts/congress_comprehensive_ingest.py \
        --congress $CONGRESS \
        --max_pages 20 \
        --scripts bills members committees votes bill_actions bill_text summaries treaties nominations hearings congress; then

        echo "✅ Congress $CONGRESS completed successfully"
        ((SUCCESS_COUNT++))
    else
        echo "❌ Congress $CONGRESS failed - continuing with next Congress"
    fi

    echo ""
    echo "📈 Progress: $SUCCESS_COUNT/$TOTAL_CONGRESSES Congresses completed"
    echo ""

    # Brief pause between Congresses to be respectful to the API
    sleep 2
done

echo "======================================================"
echo "🎉 20-Year Congress Ingestion Complete - $(date)"
echo "======================================================"
echo "Successfully processed: $SUCCESS_COUNT/$TOTAL_CONGRESSES Congresses"
echo "Log file: $LOG_FILE"
echo ""

# Final database check
echo "📊 Final Database Status:"
python check_db.py

echo ""
echo "✅ 20-year Congress data ingestion completed!"
