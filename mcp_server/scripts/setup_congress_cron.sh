#!/bin/bash
# Add Congress ingestion cron jobs to crontab

echo "Adding Congress ingestion cron jobs..."

# Backup current crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Add new entries
(crontab -l 2>/dev/null || true; echo "# Congress Data Ingestion Jobs"; echo -e "0 2 1 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_109.sh\n0 2 2 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_110.sh\n0 2 3 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_111.sh\n0 2 4 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_112.sh\n0 2 5 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_113.sh\n0 2 6 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_114.sh\n0 2 7 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_115.sh\n0 2 8 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_116.sh\n0 2 9 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_117.sh\n0 2 10 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_118.sh\n0 2 11 * * /home/cbwinslow/opendiscourse/mcp_server/scripts/ingest_congress_119.sh\n") | crontab -

echo "✅ Cron jobs added successfully"
echo "📋 Current crontab:"
crontab -l
