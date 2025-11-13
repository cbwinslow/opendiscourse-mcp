#!/bin/bash

# Monitoring Status Check Script

set -e

echo "📊 Personal Monitoring System Status"
echo "================================="

cd "$(dirname "$0")"

# Load environment
source .env

# Check Ollama
echo "🤖 Ollama Status:"
if curl -s http://localhost:11434/api/version > /dev/null; then
    VERSION=$(curl -s http://localhost:11434/api/version | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    echo "   ✅ Running (version: $VERSION)"
    
    # Check models
    MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ' ')
    echo "   📦 Models: $MODELS"
else
    echo "   ❌ Not running"
fi

echo ""

# Check database
echo "🗄️ Database Status:"
if psql "$MONITORING_DB" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "   ✅ Connected"
    
    # Get record counts
    ACTIVITY_COUNT=$(psql "$MONITORING_DB" -t -c "SELECT COUNT(*) FROM activity_logs;" 2>/dev/null | tr -d ' ')
    SCREEN_COUNT=$(psql "$MONITORING_DB" -t -c "SELECT COUNT(*) FROM screen_captures;" 2>/dev/null | tr -d ' ')
    AGENT_COUNT=$(psql "$MONITORING_DB" -t -c "SELECT COUNT(*) FROM agent_interactions;" 2>/dev/null | tr -d ' ')
    
    echo "   📊 Activity Logs: $ACTIVITY_COUNT records"
    echo "   📸 Screen Captures: $SCREEN_COUNT records"
    echo "   🤖 Agent Interactions: $AGENT_COUNT records"
else
    echo "   ❌ Not connected"
fi

echo ""

# Check services
echo "🔄 Service Status:"
for service in activity screen summarizer; do
    if [ -f "${service}.pid" ]; then
        PID=$(cat "${service}.pid")
        if kill -0 "$PID" 2>/dev/null; then
            echo "   ✅ $service (PID: $PID)"
        else
            echo "   ❌ $service (stale PID file)"
        fi
    else
        echo "   ⏹️ $service (not running)"
    fi
done

echo ""

# Check recent activity
echo "📈 Recent Activity:"
if psql "$MONITORING_DB" -c "SELECT 1;" > /dev/null 2>&1; then
    RECENT_ACTIVITY=$(psql "$MONITORING_DB" -t -c "
        SELECT application, COUNT(*) as count, 
               SUM(duration_seconds) as total_time
        FROM activity_logs 
        WHERE timestamp >= NOW() - INTERVAL '1 hour'
        GROUP BY application 
        ORDER BY total_time DESC 
        LIMIT 5;" 2>/dev/null | column -t -s '|' | head -10)
    
    if [ -n "$RECENT_ACTIVITY" ]; then
        echo "   Last hour activity:"
        echo "$RECENT_ACTIVITY" | sed 's/^/     /'
    else
        echo "   No recent activity in last hour"
    fi
fi

echo ""

# Check disk usage
echo "💾 Storage Usage:"
if [ -d "screenshots" ]; then
    SCREENSHOT_SIZE=$(du -sh screenshots 2>/dev/null | cut -f1)
    SCREENSHOT_COUNT=$(find screenshots -name "*.png" 2>/dev/null | wc -l)
    echo "   📸 Screenshots: $SCREENSHOT_COUNT files ($SCREENSHOT_SIZE)"
fi

if [ -d "logs" ]; then
    LOG_SIZE=$(du -sh logs 2>/dev/null | cut -f1)
    echo "   📝 Logs: $LOG_SIZE"
fi

echo ""
echo "🎯 Quick Actions:"
echo "   Start all: ./start_monitoring.sh"
echo "   Stop all: ./stop_monitoring.sh"
echo "   View activity: tail -f logs/activity.log"
echo "   Database query: psql \"\$MONITORING_DB\" -c \"SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT 10;\""