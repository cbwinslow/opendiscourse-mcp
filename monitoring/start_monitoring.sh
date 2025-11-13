#!/bin/bash

# Main Monitoring Startup Script

set -e

echo "🚀 Starting Personal Monitoring System..."

cd "$(dirname "$0")"

# Load environment
source .env

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/version > /dev/null; then
    echo "🤖 Starting Ollama..."
    ./start_ollama.sh
    sleep 10
fi

# Create database tables if they don't exist
echo "🗄️ Ensuring database tables exist..."
./create_tables.sh

# Start monitoring components in background

echo "📊 Starting activity logger..."
python3 activity_logger.py > logs/activity.log 2>&1 &
ACTIVITY_PID=$!
echo $ACTIVITY_PID > activity.pid

echo "📸 Starting screen capture..."
python3 screen_capture.py > logs/screen.log 2>&1 &
SCREEN_PID=$!
echo $SCREEN_PID > screen.pid

echo "🤖 Starting Ollama summarizer..."
python3 ollama_summarizer.py > logs/summarizer.log 2>&1 &
SUMMARIZER_PID=$!
echo $SUMMARIZER_PID > summarizer.pid

echo "✅ All monitoring services started!"
echo ""
echo "📊 Service Status:"
echo "   Activity Logger: PID $ACTIVITY_PID"
echo "   Screen Capture: PID $SCREEN_PID"
echo "   Ollama Summarizer: PID $SUMMARIZER_PID"
echo ""
echo "📋 Management Commands:"
echo "   View logs: tail -f logs/activity.log"
echo "   Stop all: ./stop_monitoring.sh"
echo "   Check status: ./monitoring_status.sh"
echo ""
echo "🎯 Monitoring is now active!"