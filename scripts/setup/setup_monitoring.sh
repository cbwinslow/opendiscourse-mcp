#!/bin/bash

# Personal Monitoring System Setup Script
# This script sets up comprehensive personal monitoring with Ollama and screen capture

set -e

echo "🚀 Setting up Personal Monitoring System..."

# Create directories
mkdir -p monitoring/{screenshots,logs,data,scripts}
mkdir -p monitoring/database

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install --user -q \
    pynput \
    psutil \
    pillow \
    opencv-python \
    mss \
    requests \
    psycopg2-binary \
    schedule

# Create monitoring database
echo "🗄️ Setting up monitoring database..."
createdb monitoring_db 2>/dev/null || echo "Database already exists"

# Download Ollama (local installation)
echo "🤖 Setting up Ollama..."
cd monitoring
curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama.tgz
tar -xzf ollama.tgz
rm ollama.tgz

# Create environment file
echo "⚙️ Creating configuration..."
cat > monitoring/.env <<EOF
# Monitoring Configuration
MONITORING_DB=postgresql://cbwinslow@localhost:5432/monitoring_db
OLLAMA_HOST=http://localhost:11434
SCREEN_CAPTURE_INTERVAL=30
ACTIVITY_LOG_INTERVAL=60
SYNC_INTERVAL=300
HOMELAB_URL=http://100.90.23.60:8080
DATA_RETENTION_DAYS=90
EOF

echo "✅ Setup complete!"
echo "🎯 Next steps:"
echo "   1. cd monitoring"
echo "   2. ./start_ollama.sh"
echo "   3. ./start_monitoring.sh"
echo "   4. ./create_tables.sh"