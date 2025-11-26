#!/bin/bash
# Comprehensive monitoring setup for OpenDiscourse
# Installs and configures Prometheus, Loki, OpenTelemetry, Cloudflare tunnels

set -e

echo "🚀 Setting up comprehensive monitoring for OpenDiscourse..."

# Configuration
MONITORING_DIR="/home/cbwinslow/opendiscourse/monitoring"
CLOUDCURIO_TOKEN="${CLOUDCURIO_TOKEN:-}"
CLOUDCURIO_OTEL_TOKEN="${CLOUDCURIO_OTEL_TOKEN:-}"
CLOUDCURIO_LOKI_TOKEN="${CLOUDCURIO_LOKI_TOKEN:-}"

# Create directories
mkdir -p "$MONITORING_DIR"/{prometheus,loki,otel,cloudflared,logs,certs}
mkdir -p ./logs

# Install monitoring tools
echo "📦 Installing monitoring tools..."

# Prometheus
if ! command -v prometheus &> /dev/null; then
    echo "Installing Prometheus..."
    wget -q https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
    tar xzf prometheus-2.40.0.linux-amd64.tar.gz
    sudo cp prometheus-2.40.0.linux-amd64/prometheus /usr/local/bin/
    sudo cp prometheus-2.40.0.linux-amd64/promtool /usr/local/bin/
    rm -rf prometheus-2.40.0.linux-amd64*
fi

# Node Exporter
if ! command -v node_exporter &> /dev/null; then
    echo "Installing Node Exporter..."
    wget -q https://github.com/prometheus/node_exporter/releases/download/v1.5.0/node_exporter-1.5.0.linux-amd64.tar.gz
    tar xzf node_exporter-1.5.0.linux-amd64.tar.gz
    sudo cp node_exporter-1.5.0.linux-amd64/node_exporter /usr/local/bin/
    rm -rf node_exporter-1.5.0.linux-amd64*
fi

# Postgres Exporter
if ! command -v postgres_exporter &> /dev/null; then
    echo "Installing Postgres Exporter..."
    wget -q https://github.com/prometheus-community/postgres_exporter/releases/download/v0.11.1/postgres_exporter-0.11.1.linux-amd64.tar.gz
    tar xzf postgres_exporter-0.11.1.linux-amd64.tar.gz
    sudo cp postgres_exporter-0.11.1.linux-amd64/postgres_exporter /usr/local/bin/
    rm -rf postgres_exporter-0.11.1.linux-amd64*
fi

# Cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo "Installing Cloudflared..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
    sudo chmod +x /usr/local/bin/cloudflared
fi

# OpenTelemetry Collector
if ! command -v otelcol &> /dev/null; then
    echo "Installing OpenTelemetry Collector..."
    wget -q https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.71.0/otelcol_0.71.0_linux_amd64.tar.gz
    tar xzf otelcol_0.71.0_linux_amd64.tar.gz
    sudo cp otelcol_0.71.0_linux_amd64/otelcol /usr/local/bin/
    rm -rf otelcol_0.71.0_linux_amd64*
fi

# Setup Prometheus configuration
echo "⚙️  Configuring Prometheus..."
cp "$MONITORING_DIR/prometheus/prometheus.yml" "$MONITORING_DIR/prometheus/prometheus.yml.bak" 2>/dev/null || true
cat > "$MONITORING_DIR/prometheus/prometheus.yml" << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'opendiscourse-ingestion'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 10s

  - job_name: 'opendiscourse-database'
    static_configs:
      - targets: ['localhost:9187']
    scrape_interval: 30s

  - job_name: 'opendiscourse-system'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 30s

remote_write:
  - url: "https://cloudcurio.cc/api/v1/write"
    headers:
      Authorization: "Bearer ${CLOUDCURIO_TOKEN}"
    queue_config:
      max_samples_per_send: 1000
EOF

# Setup AlertManager
cat > "$MONITORING_DIR/prometheus/alertmanager.yml" << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@opendiscourse.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:5001/webhooks/alerts'
        send_resolved: true
EOF

# Setup database triggers
echo "🗄️  Setting up database triggers..."
export PGPASSWORD=opendiscourse123
psql -h 100.90.251.120 -U opendiscourse -d opendiscourse -f /home/cbwinslow/opendiscourse/mcp_server/sql/monitoring_triggers.sql

# Create systemd services
echo "🔧 Creating systemd services..."

# Prometheus service
sudo tee /etc/systemd/system/prometheus.service > /dev/null << EOF
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/prometheus \\
  --config.file=$MONITORING_DIR/prometheus/prometheus.yml \\
  --storage.tsdb.path=$MONITORING_DIR/prometheus/data \\
  --web.console.libraries=/etc/prometheus/console_libraries \\
  --web.console.templates=/etc/prometheus/consoles \\
  --storage.tsdb.retention.time=30d \\
  --web.enable-lifecycle

[Install]
WantedBy=multi-user.target
EOF

# Node Exporter service
sudo tee /etc/systemd/system/node_exporter.service > /dev/null << EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/node_exporter \\
  --collector.cpu \\
  --collector.diskstats \\
  --collector.filesystem \\
  --collector.meminfo \\
  --collector.netdev

[Install]
WantedBy=multi-user.target
EOF

# Postgres Exporter service
sudo tee /etc/systemd/system/postgres_exporter.service > /dev/null << EOF
[Unit]
Description=Postgres Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/postgres_exporter \\
  --datasource="postgresql://opendiscourse:opendiscourse123@100.90.251.120:5432/opendiscourse?sslmode=disable"

[Install]
WantedBy=multi-user.target
EOF

# OpenTelemetry Collector service
sudo tee /etc/systemd/system/otelcol.service > /dev/null << EOF
[Unit]
Description=OpenTelemetry Collector
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/otelcol --config="$MONITORING_DIR/otel-collector-config.yaml"
Environment=OTEL_EXPORTER_OTLP_ENDPOINT=https://cloudcurio.cc
Environment=OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer ${CLOUDCURIO_OTEL_TOKEN}

[Install]
WantedBy=multi-user.target
EOF

# Cloudflare Tunnel service
sudo tee /etc/systemd/system/cloudflared.service > /dev/null << EOF
[Unit]
Description=Cloudflare Tunnel
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/cloudflared tunnel --config="$MONITORING_DIR/cloudflared/config.yml" run

[Install]
WantedBy=multi-user.target
EOF

# Setup environment variables
echo "🌍 Setting up environment variables..."
cat >> ~/.bashrc << 'EOF'

# OpenDiscourse Monitoring Environment
export PROMETHEUS_PORT=8000
export GRAFANA_PORT=3000
export LOKI_PORT=3100
export ALERTMANAGER_PORT=9093
export OTEL_EXPORTER_OTLP_ENDPOINT="https://cloudcurio.cc"
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer ${CLOUDCURIO_OTEL_TOKEN}"
export LOKI_URL="https://cloudcurio.cc/loki/api/v1/push"
export CLOUDCURIO_TOKEN="${CLOUDCURIO_TOKEN}"
export CLOUDCURIO_OTEL_TOKEN="${CLOUDCURIO_OTEL_TOKEN}"
export CLOUDCURIO_LOKI_TOKEN="${CLOUDCURIO_LOKI_TOKEN}"

# Feature flags for monitoring
export ENABLE_OPENTELEMETRY=true
export ENABLE_PROMETHEUS=true
export ENABLE_LOKI_LOGGING=true
export ENABLE_ALLOY_OBSERVABILITY=true
export ENABLE_DETAILED_TRIGGERS=true
export ENABLE_CLOUDFLARE_TUNNEL=true
export ENABLE_BENCHMARKING=true
export ENABLE_TELEMETRY=true
export ENABLE_ERROR_TRACKING=true
export ENABLE_PERFORMANCE_METRICS=true
EOF

# Create certificates directory
echo "🔐 Setting up certificates..."
sudo mkdir -p /etc/cloudflared
sudo chown cbwinslow:cbwinslow /etc/cloudflared

# Generate self-signed certificate for testing (replace with real certs)
if [ ! -f /etc/cloudflared/cert.pem ]; then
    openssl req -x509 -newkey rsa:4096 -keyout /etc/cloudflared/key.pem -out /etc/cloudflared/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=OpenDiscourse/CN=localhost"
fi

# Enable and start services
echo "🚀 Starting monitoring services..."
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl enable node_exporter
sudo systemctl enable postgres_exporter
sudo systemctl enable otelcol
sudo systemctl enable cloudflared

sudo systemctl start prometheus
sudo systemctl start node_exporter
sudo systemctl start postgres_exporter
sudo systemctl start otelcol

# Wait for services to start
sleep 5

# Check service status
echo "📊 Checking service status..."
for service in prometheus node_exporter postgres_exporter otelcol; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service is running"
    else
        echo "❌ $service failed to start"
        sudo systemctl status $service
    fi
done

# Setup cron jobs for monitoring
echo "⏰ Setting up cron jobs..."
(crontab -l 2>/dev/null; echo "
# OpenDiscourse monitoring cron jobs
*/5 * * * * /home/cbwinslow/opendiscourse/scripts/check_monitoring_health.sh
*/10 * * * * /home/cbwinslow/opendiscourse/scripts/cleanup_old_logs.sh
0 2 * * * /home/cbwinslow/opendiscourse/scripts/backup_monitoring_data.sh
") | crontab -

# Create health check script
cat > /home/cbwinslow/opendiscourse/scripts/check_monitoring_health.sh << 'EOF'
#!/bin/bash
# Health check for monitoring services

SERVICES=("prometheus:8000" "node_exporter:9100" "postgres_exporter:9187" "otelcol:8888")

for service in "${SERVICES[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if curl -s "http://localhost:$port/metrics" > /dev/null; then
        echo "$(date): ✅ $name is healthy"
    else
        echo "$(date): ❌ $name is unhealthy"
        # Send alert to cloudcurio.cc
        curl -X POST "https://cloudcurio.cc/api/v1/alerts" \
             -H "Authorization: Bearer ${CLOUDCURIO_TOKEN}" \
             -H "Content-Type: application/json" \
             -d "{\"alert\":\"$name down\",\"severity\":\"critical\"}"
    fi
done
EOF

chmod +x /home/cbwinslow/opendiscourse/scripts/check_monitoring_health.sh

# Create cleanup script
cat > /home/cbwinslow/opendiscourse/scripts/cleanup_old_logs.sh << 'EOF'
#!/bin/bash
# Clean up old monitoring logs

find /home/cbwinslow/opendiscourse/monitoring/logs -name "*.log" -mtime +7 -delete
find /home/cbwinslow/opendiscourse/logs -name "*.log" -mtime +7 -delete
EOF

chmod +x /home/cbwinslow/opendiscourse/scripts/cleanup_old_logs.sh

echo "🎉 Monitoring setup complete!"
echo ""
echo "📊 Monitoring endpoints:"
echo "  Prometheus: http://localhost:8000"
echo "  Node Exporter: http://localhost:9100/metrics"
echo "  Postgres Exporter: http://localhost:9187/metrics"
echo "  OpenTelemetry: http://localhost:8888/metrics"
echo ""
echo "🌐 Cloudflare tunnels (once configured):"
echo "  prometheus.opendiscourse.com"
echo "  grafana.opendiscourse.com"
echo "  otlp.opendiscourse.com"
echo "  loki.opendiscourse.com"
echo "  alerts.opendiscourse.com"
echo ""
echo "🔧 Next steps:"
echo "1. Configure Cloudflare tunnel credentials"
echo "2. Set up cloudcurio.cc tokens"
echo "3. Start Cloudflare tunnel: sudo systemctl start cloudflared"
echo "4. Access dashboards via Cloudflare tunnels"
echo ""
echo "⚠️  Don't forget to:"
echo "- Set CLOUDCURIO_TOKEN environment variable"
echo "- Set CLOUDCURIO_OTEL_TOKEN environment variable"
echo "- Set CLOUDCURIO_LOKI_TOKEN environment variable"
echo "- Configure Cloudflare tunnel ID and credentials"