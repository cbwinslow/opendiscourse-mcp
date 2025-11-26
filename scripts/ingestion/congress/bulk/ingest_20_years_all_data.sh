#!/bin/bash
# 20-Year Congress Comprehensive Data Ingestion
# Runs congress_comprehensive_ingest.py for each Congress session 105-118
# Ingests ALL available data types for each Congress

set -e

echo "🏛️  Starting 20-Year Comprehensive Congress Data Ingestion - $(date)"
echo "================================================================"
echo "Congress Sessions: 105-118 (approximately 1997-2025)"
echo "Data Types: ALL (bills, members, committees, votes, actions, text, summaries, treaties, nominations, hearings, congress)"
echo ""

# Load environment
source "/home/cbwinslow/opendiscourse/.venv/bin/activate"
export DATABASE_URL="postgresql://opendiscourse:opendiscourse123@100.90.251.120:5432/opendiscourse"
export CONGRESS_API_KEY="U71JFZEqNsiSranCdbrj4pZaobtoMtAnl18cIJc2"
export PYTHONPATH="/home/cbwinslow/opendiscourse"

# Create logs directory
mkdir -p logs

# Congress sessions to process (105-118 covers ~1997-2025)
CONGRESSES=(105 106 107 108 109 110 111 112 113 114 115 116 117 118)
TOTAL_CONGRESSES=${#CONGRESSES[@]}

echo "🎯 Processing $TOTAL_CONGRESSES Congress sessions: ${CONGRESSES[*]}"
echo "📊 Each session will ingest ALL available data types"
echo ""

SUCCESS_COUNT=0

for CONGRESS in "${CONGRESSES[@]}"; do
    echo "======================================================"
    echo "🏛️  Congress $CONGRESS - $(date)"
    echo "======================================================"

    CONGRESS_START=$(( (CONGRESS-1)*2 + 1789 ))
    CONGRESS_END=$(( CONGRESS*2 + 1789 ))
    echo "📅 Approximate years: $CONGRESS_START-$CONGRESS_END"
    echo ""

    # Log file for this Congress
    LOG_FILE="logs/congress_${CONGRESS}_comprehensive_$(date +%Y%m%d_%H%M%S).log"

    # Run comprehensive ingestion for this Congress
    # This runs ALL data types for the Congress session
    if python mcp_server/scripts/congress_comprehensive_ingest.py \
        --congress $CONGRESS \
        --max_pages 50 \
        --scripts all > "$LOG_FILE" 2>&1; then

        echo "✅ Congress $CONGRESS completed successfully"
        ((SUCCESS_COUNT++))
    else
        echo "❌ Congress $CONGRESS failed"
        echo "📄 Check log: $LOG_FILE"
    fi

    echo "📈 Progress: $SUCCESS_COUNT/$TOTAL_CONGRESSES Congresses completed"
    echo ""

    # Brief pause between Congresses to be respectful to the API
    sleep 5
done

echo "======================================================"
echo "🎉 20-Year Comprehensive Ingestion Complete - $(date)"
echo "======================================================"
echo "Successfully processed: $SUCCESS_COUNT/$TOTAL_CONGRESSES Congresses"
echo "Each Congress ingested: bills, members, committees, votes, actions, text, summaries, treaties, nominations, hearings, congress"
echo ""

# Final database check
echo "📊 Final Database Status:"
python check_db.py

echo ""
echo "✅ 20-year comprehensive Congress data ingestion completed!"
