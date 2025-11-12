#!/bin/bash
# MCP Server Ingestion Setup Script
# This script sets up automated ingestion processes for your homelab

set -e

echo "🚀 Setting up MCP Server Ingestion Processes"

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

# Create systemd service files
echo "📝 Creating systemd service files..."

# FastAPI server service
cat > /tmp/mcp-server.service << EOF
[Unit]
Description=MCP Server FastAPI Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/cbwinslow/opendiscourse
Environment=DATABASE_URL=$DATABASE_URL
Environment=CONGRESS_API_KEY=$CONGRESS_API_KEY
Environment=GOVINFO_API_KEY=$GOVINFO_API_KEY
ExecStart=/home/cbwinslow/opendiscourse/.venv/bin/python -m uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Congress ingestion service
cat > /tmp/congress-ingestion.service << EOF
[Unit]
Description=Congress Data Ingestion Service
After=network.target postgresql.service mcp-server.service
Requires=postgresql.service

[Service]
Type=oneshot
User=$USER
WorkingDirectory=/home/cbwinslow/opendiscourse
Environment=DATABASE_URL=$DATABASE_URL
Environment=CONGRESS_API_KEY=$CONGRESS_API_KEY
ExecStart=/home/cbwinslow/opendiscourse/.venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118
EOF

# Congress ingestion timer
cat > /tmp/congress-ingestion.timer << EOF
[Unit]
Description=Run Congress Data Ingestion Daily
Requires=congress-ingestion.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# OpenStates ingestion service
cat > /tmp/openstates-ingestion.service << EOF
[Unit]
Description=OpenStates Data Ingestion Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=oneshot
User=$USER
WorkingDirectory=/home/cbwinslow/opendiscourse
Environment=DATABASE_URL=$DATABASE_URL
ExecStart=/home/cbwinslow/opendiscourse/.venv/bin/python mcp_server/scripts/openstates_ingest.py --jurisdiction us --entity bills
EOF

# OpenStates ingestion timer
cat > /tmp/openstates-ingestion.timer << EOF
[Unit]
Description=Run OpenStates Data Ingestion Daily
Requires=openstates-ingestion.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# GovInfo ingestion service
cat > /tmp/govinfo-ingestion.service << EOF
[Unit]
Description=GovInfo Data Ingestion Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=oneshot
User=$USER
WorkingDirectory=/home/cbwinslow/opendiscourse
Environment=DATABASE_URL=$DATABASE_URL
Environment=GOVINFO_API_KEY=$GOVINFO_API_KEY
ExecStart=/home/cbwinslow/opendiscourse/.venv/bin/python mcp_server/scripts/govinfo_ingest.py --collection BILLS
EOF

# GovInfo ingestion timer
cat > /tmp/govinfo-ingestion.timer << EOF
[Unit]
Description=Run GovInfo Data Ingestion Daily
Requires=govinfo-ingestion.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Copy service files to systemd
sudo cp /tmp/mcp-server.service /etc/systemd/system/
sudo cp /tmp/congress-ingestion.service /etc/systemd/system/
sudo cp /tmp/congress-ingestion.timer /etc/systemd/system/
sudo cp /tmp/openstates-ingestion.service /etc/systemd/system/
sudo cp /tmp/openstates-ingestion.timer /etc/systemd/system/
sudo cp /tmp/govinfo-ingestion.service /etc/systemd/system/
sudo cp /tmp/govinfo-ingestion.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

echo "✅ Systemd services created"

# Create cron jobs as backup
echo "📅 Creating cron jobs as backup..."

CRON_JOBS="
# MCP Server Ingestion Jobs
0 2 * * * $USER cd /home/cbwinslow/opendiscourse && export \$(cat mcp_server/.env | xargs) && .venv/bin/python mcp_server/scripts/congress_ingest.py --congress 118 >> logs/congress_ingestion.log 2>&1
0 3 * * * $USER cd /home/cbwinslow/opendiscourse && export \$(cat mcp_server/.env | xargs) && .venv/bin/python mcp_server/scripts/openstates_ingest.py --jurisdiction us --entity bills >> logs/openstates_ingestion.log 2>&1
0 4 * * * $USER cd /home/cbwinslow/opendiscourse && export \$(cat mcp_server/.env | xargs) && .venv/bin/python mcp_server/scripts/govinfo_ingest.py --collection BILLS >> logs/govinfo_ingestion.log 2>&1
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

# Check database connection
if psql "$DATABASE_URL" -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ Database: Connected"
else
    echo "❌ Database: Connection failed"
fi

# Check table counts
echo "📊 Table Counts:"
psql "$DATABASE_URL" -c "
SELECT
    'congress_bills' as table_name, COUNT(*) as count FROM congress_bills
UNION ALL
SELECT 'openstates_bills', COUNT(*) FROM openstates_bills
UNION ALL
SELECT 'govinfo_packages', COUNT(*) FROM govinfo_packages
ORDER BY table_name;" 2>/dev/null || echo "❌ Could not query table counts"

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

# Check systemd services
echo "🔧 Systemd Services:"
systemctl is-active --quiet mcp-server && echo "✅ MCP Server: Running" || echo "❌ MCP Server: Not running"
systemctl is-active --quiet congress-ingestion.timer && echo "✅ Congress Timer: Active" || echo "❌ Congress Timer: Inactive"
systemctl is-active --quiet openstates-ingestion.timer && echo "✅ OpenStates Timer: Active" || echo "❌ OpenStates Timer: Inactive"
systemctl is-active --quiet govinfo-ingestion.timer && echo "✅ GovInfo Timer: Active" || echo "❌ GovInfo Timer: Inactive"

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

echo ""
echo "🎯 Setup Complete!"
echo ""
echo "To start the services:"
echo "  sudo systemctl enable mcp-server"
echo "  sudo systemctl start mcp-server"
echo "  sudo systemctl enable congress-ingestion.timer openstates-ingestion.timer govinfo-ingestion.timer"
echo "  sudo systemctl start congress-ingestion.timer openstates-ingestion.timer govinfo-ingestion.timer"
echo ""
echo "To run manual ingestion:"
echo "  ./manual_ingest.sh"
echo ""
echo "To monitor:"
echo "  ./monitor_ingestion.sh"
echo ""
echo "API endpoints:"
echo "  FastAPI server: http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Log files are in ./logs/"