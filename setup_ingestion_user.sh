#!/bin/bash
# MCP Server Ingestion Setup Script (User Level)
# This script sets up automated ingestion processes for your homelab

set -e

echo "🚀 Setting up MCP Server Ingestion Processes (User Level)"

# Load environment variables
if [ -f "mcp_server/.env" ]; then
    export $(cat mcp_server/.env | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ Error: mcp_server/.env file not found"
    exit 1
fi

# Test database connection
echo "🔍 Testing database connection..."
python -c "
import psycopg2
try:
    conn = psycopg2.connect('$DATABASE_URL')
    conn.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

# Create logs directory
mkdir -p logs
echo "📁 Created logs directory"

# Create cron jobs for automated ingestion
echo "📅 Setting up cron jobs for automated ingestion..."

CRON_JOBS="
# MCP Server Ingestion Jobs - Run daily at 2AM, 3AM, 4AM
0 2 * * * cd /home/cbwinslow/opendiscourse && export \$(cat mcp_server/.env | xargs) && .venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118 >> logs/congress_ingestion.log 2>&1
0 3 * * * cd /home/cbwinslow/opendiscourse && export \$(cat mcp_server/.env | xargs) && .venv/bin/python mcp_server/scripts/openstates_ingest.py --jurisdiction us --entity bills >> logs/openstates_ingestion.log 2>&1
0 4 * * * cd /home/cbwinslow/opendiscourse && export \$(cat mcp_server/.env | xargs) && .venv/bin/python mcp_server/scripts/govinfo_ingest.py --collection BILLS >> logs/govinfo_ingestion.log 2>&1
# Health check every 6 hours
0 */6 * * * cd /home/cbwinslow/opendiscourse && export \$(cat mcp_server/.env | xargs) && .venv/bin/python -c \"import psycopg2; psycopg2.connect('$DATABASE_URL').close(); print('DB OK')\" >> logs/health_check.log 2>&1
"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_JOBS") | crontab -

echo "✅ Cron jobs added"

# Create monitoring script
cat > monitor_ingestion.sh << 'EOF'
#!/bin/bash
# Monitor ingestion processes and database health

echo "=== MCP Ingestion Monitor ==="
echo "Timestamp: $(date)"

# Load environment
export $(cat mcp_server/.env | xargs)

# Check database connection
if python -c "
import psycopg2
try:
    conn = psycopg2.connect('$DATABASE_URL')
    conn.close()
    print('Connected')
except Exception as e:
    print(f'Failed: {e}')
    exit(1)
" >/dev/null 2>&1; then
    echo "✅ Database: Connected"
else
    echo "❌ Database: Connection failed"
fi

# Check table counts
echo "📊 Table Counts:"
python -c "
import psycopg2
import os
conn = psycopg2.connect('$DATABASE_URL')
cur = conn.cursor()
cur.execute('''
SELECT
    'congress_bills' as table_name, COUNT(*) as count FROM congress_bills
UNION ALL
SELECT 'openstates_bills', COUNT(*) FROM openstates_bills
UNION ALL
SELECT 'govinfo_packages', COUNT(*) FROM govinfo_packages
ORDER BY table_name;
''')
rows = cur.fetchall()
for row in rows:
    print(f'  {row[0]}: {row[1]}')
cur.close()
conn.close()
" 2>/dev/null || echo "❌ Could not query table counts"

# Check recent logs
echo "📝 Recent Log Activity:"
echo "Congress ingestion:"
tail -5 logs/congress_ingestion.log 2>/dev/null || echo "No congress logs found"
echo ""
echo "OpenStates ingestion:"
tail -5 logs/openstates_ingestion.log 2>/dev/null || echo "No openstates logs found"
echo ""
echo "GovInfo ingestion:"
tail -5 logs/govinfo_ingestion.log 2>/dev/null || echo "No govinfo logs found"

# Check running processes
echo "🔧 Running Processes:"
pgrep -f "congress_ingest" >/dev/null && echo "✅ Congress ingestion: Running" || echo "⏸️  Congress ingestion: Not running"
pgrep -f "openstates_ingest" >/dev/null && echo "✅ OpenStates ingestion: Running" || echo "⏸️  OpenStates ingestion: Not running"
pgrep -f "govinfo_ingest" >/dev/null && echo "✅ GovInfo ingestion: Running" || echo "⏸️  GovInfo ingestion: Not running"
pgrep -f "uvicorn.*mcp_server" >/dev/null && echo "✅ MCP Server: Running" || echo "⏸️  MCP Server: Not running"

echo "=== End Monitor ==="
EOF

chmod +x monitor_ingestion.sh

echo "✅ Monitor script created"

# Create manual ingestion script
cat > manual_ingest.sh << 'EOF'
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
    echo "📥 Starting $name ingestion..."
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
run_ingestion "Congress" ".venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118"
run_ingestion "OpenStates" ".venv/bin/python mcp_server/scripts/openstates_ingest.py --jurisdiction us --entity bills"
run_ingestion "GovInfo" ".venv/bin/python mcp_server/scripts/govinfo_ingest.py --collection BILLS"

echo "🎉 All manual ingestions completed!"
EOF

chmod +x manual_ingest.sh

echo "✅ Manual ingestion script created"

# Create FastAPI server startup script
cat > start_server.sh << 'EOF'
#!/bin/bash
# Start the MCP FastAPI server

echo "🚀 Starting MCP Server..."

# Load environment
export $(cat mcp_server/.env | xargs)

# Start server in background
.venv/bin/python -m uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

echo "✅ MCP Server started with PID: $SERVER_PID"
echo "🌐 API available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo ""
echo "To stop the server: kill $SERVER_PID"

# Save PID for later
echo $SERVER_PID > .server_pid
EOF

chmod +x start_server.sh

echo "✅ Server startup script created"

# Create stop server script
cat > stop_server.sh << 'EOF'
#!/bin/bash
# Stop the MCP FastAPI server

if [ -f ".server_pid" ]; then
    SERVER_PID=$(cat .server_pid)
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo "🛑 Stopping MCP Server (PID: $SERVER_PID)..."
        kill $SERVER_PID
        rm .server_pid
        echo "✅ MCP Server stopped"
    else
        echo "⚠️  Server process not found"
        rm .server_pid
    fi
else
    echo "⚠️  No server PID file found"
    # Try to find and kill any uvicorn processes
    UVICORN_PIDS=$(pgrep -f "uvicorn.*mcp_server")
    if [ -n "$UVICORN_PIDS" ]; then
        echo "🛑 Killing uvicorn processes: $UVICORN_PIDS"
        kill $UVICORN_PIDS
    fi
fi
EOF

chmod +x stop_server.sh

echo "✅ Server stop script created"

echo ""
echo "🎯 Setup Complete!"
echo ""
echo "To start the MCP server:"
echo "  ./start_server.sh"
echo ""
echo "To stop the MCP server:"
echo "  ./stop_server.sh"
echo ""
echo "To run manual ingestion:"
echo "  ./manual_ingest.sh"
echo ""
echo "To monitor:"
echo "  ./monitor_ingestion.sh"
echo ""
echo "Automated ingestion will run daily via cron:"
echo "  - Congress: 2:00 AM"
echo "  - OpenStates: 3:00 AM"
echo "  - GovInfo: 4:00 AM"
echo "  - Health checks: Every 6 hours"
echo ""
echo "API endpoints when server is running:"
echo "  FastAPI server: http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Log files are in ./logs/"
echo ""
echo "To trigger ingestion via API:"
echo '  curl -X POST "http://localhost:8000/mcp/ingest_data" -H "Content-Type: application/json" -d "{\"user_id\": \"admin\", \"site\": \"congress\", \"database_url\": \"'"$DATABASE_URL"'\", \"ingestion_mode\": \"incremental\"}"'
echo ""
echo "To query data via API:"
echo '  curl "http://localhost:8000/mcp/query_data?user_id=admin&database_url='"$DATABASE_URL"'&table=congress_bills&limit=5"'