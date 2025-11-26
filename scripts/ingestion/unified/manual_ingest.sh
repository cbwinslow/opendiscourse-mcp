#!/bin/bash
# Manual ingestion trigger script

set -e

echo "🔄 Starting manual ingestion..."

# Load environment
export $(cat mcp_server/.env | xargs)

# Function to run ingestion with timing
run_ingestion() {
    local name=$1
    local command=$2
    local requires_api=$3
    echo "📥 Starting $name ingestion..."
    
    # Check if API key is required and available
    if [ "$requires_api" = "true" ]; then
        if [ -z "${OPENSTATES_API_KEY:-}" ]; then
            echo "⚠️  Skipping $name ingestion - API key not configured"
            return 0
        fi
    fi
    
    local start_time=$(date +%s)
    if eval "$command"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        echo "✅ $name ingestion completed in ${duration}s"
    else
        echo "❌ $name ingestion failed"
        return 1
    fi
}

# Run all ingestions
run_ingestion "Congress" "PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python scripts/ingestion/congress/congress_ingest.py --congress 118" "false"
run_ingestion "OpenStates" "PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction us --per_page 50" "true"
run_ingestion "GovInfo" "PYTHONPATH=/home/cbwinslow/opendiscourse .venv/bin/python scripts/ingestion/govinfo/govinfo_ingest.py --collection BILLS" "false"

echo "🎉 All manual ingestions completed!"
