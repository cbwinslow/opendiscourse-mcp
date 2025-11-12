#!/bin/bash
# Test Congress Data Ingestion Script
# Tests ingestion with minimal data to verify API connectivity

set -e

echo "🧪 Testing Congress Data Ingestion - $(date)"
echo "==========================================="

# Load environment
source "/home/cbwinslow/opendiscourse/.venv/bin/activate"
export DATABASE_URL="postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse"
export CONGRESS_API_KEY="U71JFZEqNsiSranCdbrj4pZaobtoMtAnl18cIJc2"
export PYTHONPATH="/home/cbwinslow/opendiscourse"

echo "📊 Testing with Congress 118, minimal data..."
echo ""

# Test just bills first (should work)
echo "Testing bills ingestion..."
if python mcp_server/scripts/congress_ingest.py --congress 118 --max_pages 1; then
    echo "✅ Bills ingestion test passed"
else
    echo "❌ Bills ingestion test failed"
    exit 1
fi

echo ""

# Check database status
echo "📊 Database status after test:"
python check_db.py

echo ""
echo "✅ Congress ingestion test completed successfully!"
