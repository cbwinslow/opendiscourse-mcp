#!/bin/bash

# Database Table Creation Script

set -e

echo "🗄️ Creating monitoring database tables..."

cd "$(dirname "$0")"

# Load environment
source .env

# Create tables using psql
psql "$MONITORING_DB" << 'EOF'
-- Activity Logs Table
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activity_type VARCHAR(50),
    application VARCHAR(100),
    website VARCHAR(255),
    duration_seconds INTEGER,
    keystrokes INTEGER,
    mouse_clicks INTEGER,
    window_title VARCHAR(255),
    agent_interaction TEXT,
    summary TEXT,
    raw_data JSONB,
    synced_to_homelab BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Screen Captures Table
CREATE TABLE IF NOT EXISTS screen_captures (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(500),
    file_size INTEGER,
    resolution VARCHAR(20),
    analysis_result TEXT,
    summary TEXT,
    synced_to_homelab BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Interactions Table
CREATE TABLE IF NOT EXISTS agent_interactions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100),
    interaction_type VARCHAR(50),
    conversation_text TEXT,
    summary TEXT,
    context JSONB,
    synced_to_homelab BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System Metrics Table
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    disk_usage_gb DECIMAL(10,2),
    network_bytes_sent BIGINT,
    network_bytes_recv BIGINT,
    active_processes INTEGER,
    uptime_seconds INTEGER,
    synced_to_homelab BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_screen_captures_timestamp ON screen_captures(timestamp);
CREATE INDEX IF NOT EXISTS idx_agent_interactions_timestamp ON agent_interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_logs_synced ON activity_logs(synced_to_homelab);
CREATE INDEX IF NOT EXISTS idx_screen_captures_synced ON screen_captures(synced_to_homelab);

EOF

echo "✅ Database tables created successfully!"