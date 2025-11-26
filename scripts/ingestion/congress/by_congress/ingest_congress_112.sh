#!/bin/bash
# Congress 112 Data Ingestion Script
# Generated on Wed Nov 12 05:18:54 PM EST 2025

set -e

echo "🏛️  Starting Congress 112 Data Ingestion - $(date)"
echo "======================================================"

# Load environment
source "/home/cbwinslow/opendiscourse/.venv/bin/activate"
export DATABASE_URL="postgresql://opendiscourse:opendiscourse123@100.90.251.120:5432/opendiscourse"
export CONGRESS_API_KEY="U71JFZEqNsiSranCdbrj4pZaobtoMtAnl18cIJc2"
export PYTHONPATH="/home/cbwinslow/opendiscourse"

# Log file
LOG_FILE="/home/cbwinslow/opendiscourse/logs/congress_112_ingestion_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "📊 Processing Congress 112 data..."
echo "📁 Log file: $LOG_FILE"

# Run comprehensive ingestion for this Congress
python mcp_server/scripts/congress_comprehensive_ingest.py \
    --congress 112 \
    --max_pages 50 \
    --list-scripts > /dev/null && \
python mcp_server/scripts/congress_comprehensive_ingest.py \
    --congress 112 \
    --max_pages 50 \
    --scripts bills members committees votes bill_actions bill_text summaries treaties nominations hearings congress

echo "✅ Congress 112 ingestion completed - $(date)"
