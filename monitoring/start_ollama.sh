#!/bin/bash

# Ollama Startup Script

set -e

echo "🤖 Starting Ollama..."

cd "$(dirname "$0")"

# Set Ollama home
export OLLAMA_HOME="$(pwd)/ollama_data"
mkdir -p "$OLLAMA_HOME"

# Start Ollama in background
./bin/ollama serve > logs/ollama.log 2>&1 &
OLLAMA_PID=$!

echo "📝 Ollama started with PID: $OLLAMA_PID"
echo $OLLAMA_PID > ollama.pid

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to be ready..."
sleep 5

# Check if Ollama is responding
if curl -s http://localhost:11434/api/version > /dev/null; then
    echo "✅ Ollama is ready!"
    
    # Pull lightweight model
    echo "📥 Pulling llama3.2:1b model..."
    ./bin/ollama pull llama3.2:1b
    
    echo "🎉 Ollama setup complete!"
else
    echo "❌ Ollama failed to start"
    kill $OLLAMA_PID 2>/dev/null
    exit 1
fi