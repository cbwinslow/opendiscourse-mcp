#!/bin/bash

# Stop Monitoring Services Script

set -e

echo "⏹️ Stopping Personal Monitoring System..."

cd "$(dirname "$0")"

# Stop services
for service in activity screen summarizer ollama; do
    if [ -f "${service}.pid" ]; then
        PID=$(cat "${service}.pid")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🛑 Stopping $service (PID: $PID)..."
            kill "$PID"
            sleep 2
            
            # Force kill if still running
            if kill -0 "$PID" 2>/dev/null; then
                echo "⚡ Force stopping $service..."
                kill -9 "$PID"
            fi
        fi
        rm -f "${service}.pid"
    fi
done

# Additional cleanup for Ollama
if pgrep -f "ollama serve" > /dev/null; then
    echo "🛑 Stopping Ollama service..."
    pkill -f "ollama serve"
fi

echo "✅ All monitoring services stopped!"