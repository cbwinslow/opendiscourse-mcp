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
tables = [
    ('congress_bills', 'Congress bills'),
    ('govinfo_packages', 'GovInfo packages'),
    ('opencivicdata_bill', 'OpenStates bills')
]
for table, desc in tables:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table};')
        count = cur.fetchone()[0]
        
        # Check for duplicates based on primary key
        if table == 'congress_bills':
            cur.execute('SELECT COUNT(*) FROM (SELECT bill_id, COUNT(*) as cnt FROM congress_bills GROUP BY bill_id HAVING COUNT(*) > 1) as dupes;')
            duplicates = cur.fetchone()[0]
        elif table == 'govinfo_packages':
            cur.execute('SELECT COUNT(*) FROM (SELECT id, COUNT(*) as cnt FROM govinfo_packages GROUP BY id HAVING COUNT(*) > 1) as dupes;')
            duplicates = cur.fetchone()[0]
        elif table == 'opencivicdata_bill':
            cur.execute('SELECT COUNT(*) FROM (SELECT id, COUNT(*) as cnt FROM opencivicdata_bill GROUP BY id HAVING COUNT(*) > 1) as dupes;')
            duplicates = cur.fetchone()[0]
        else:
            duplicates = 0
            
        status = f'{count} rows'
        if duplicates > 0:
            status += f' ⚠️  {duplicates} duplicates'
        print(f'  {desc}: {status}')
    except Exception as e:
        print(f'  {desc}: Error - {str(e)[:50]}')
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
