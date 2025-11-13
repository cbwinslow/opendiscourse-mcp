#!/bin/bash
# Remote monitoring setup for OpenDiscourse on cbwdellr720
# Deploys monitoring stack to remote server with SSH websocket connections

set -e

REMOTE_SERVER="100.90.23.60"
REMOTE_USER="cbwinslow"
REMOTE_DIR="/home/cbwinslow/opendiscourse-monitoring"
SSH_KEY="$HOME/.ssh/id_ed25519"

echo "🚀 Deploying monitoring stack to $REMOTE_SERVER..."

# Create remote directory structure
echo "📁 Creating remote directories..."
ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_SERVER "mkdir -p $REMOTE_DIR/{prometheus,loki,otel,cloudflared,logs,certs,grafana,alertmanager}"

# Copy configurations to remote server
echo "📤 Copying monitoring configurations..."
scp -i $SSH_KEY -r monitoring/* $REMOTE_USER@$REMOTE_SERVER:$REMOTE_DIR/

# Install monitoring tools on remote server
echo "📦 Installing monitoring tools on remote server..."
ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_SERVER << 'EOF'
set -e
cd /home/cbwinslow/opendiscourse-monitoring

# Download and install Prometheus
if [ ! -f /usr/local/bin/prometheus ]; then
    echo "Installing Prometheus..."
    wget -q https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
    tar xzf prometheus-2.40.0.linux-amd64.tar.gz
    sudo cp prometheus-2.40.0.linux-amd64/prometheus /usr/local/bin/
    sudo cp prometheus-2.40.0.linux-amd64/promtool /usr/local/bin/
    rm -rf prometheus-2.40.0.linux-amd64*
fi

# Download and install Node Exporter
if [ ! -f /usr/local/bin/node_exporter ]; then
    echo "Installing Node Exporter..."
    wget -q https://github.com/prometheus/node_exporter/releases/download/v1.5.0/node_exporter-1.5.0.linux-amd64.tar.gz
    tar xzf node_exporter-1.5.0.linux-amd64.tar.gz
    sudo cp node_exporter-1.5.0.linux-amd64/node_exporter /usr/local/bin/
    rm -rf node_exporter-1.5.0.linux-amd64*
fi

# Download and install Postgres Exporter
if [ ! -f /usr/local/bin/postgres_exporter ]; then
    echo "Installing Postgres Exporter..."
    wget -q https://github.com/prometheus-community/postgres_exporter/releases/download/v0.11.1/postgres_exporter-0.11.1.linux-amd64.tar.gz
    tar xzf postgres_exporter-0.11.1.linux-amd64.tar.gz
    sudo cp postgres_exporter-0.11.1.linux-amd64/postgres_exporter /usr/local/bin/
    rm -rf postgres_exporter-0.11.1.linux-amd64*
fi

# Download and install Cloudflared
if [ ! -f /usr/local/bin/cloudflared ]; then
    echo "Installing Cloudflared..."
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
    sudo mv cloudflared-linux-amd64 /usr/local/bin/cloudflared
    sudo chmod +x /usr/local/bin/cloudflared
fi

# Download and install OpenTelemetry Collector
if [ ! -f /usr/local/bin/otelcol ]; then
    echo "Installing OpenTelemetry Collector..."
    wget -q https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.71.0/otelcol_0.71.0_linux_amd64.tar.gz
    tar xzf otelcol_0.71.0_linux_amd64.tar.gz
    sudo cp otelcol_0.71.0_linux_amd64/otelcol /usr/local/bin/
    rm -rf otelcol_0.71.0_linux_amd64*
fi

# Create systemd services
echo "🔧 Creating systemd services..."
sudo tee /etc/systemd/system/prometheus.service > /dev/null << 'EOFSVC'
[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/prometheus \\
  --config.file=/home/cbwinslow/opendiscourse-monitoring/prometheus/prometheus.yml \\
  --storage.tsdb.path=/home/cbwinslow/opendiscourse-monitoring/prometheus/data \\
  --web.console.libraries=/etc/prometheus/console_libraries \\
  --web.console.templates=/etc/prometheus/consoles \\
  --storage.tsdb.retention.time=30d \\
  --web.enable-lifecycle \\
  --web.enable-admin-api

[Install]
WantedBy=multi-user.target
EOFSVC

sudo tee /etc/systemd/system/node_exporter.service > /dev/null << 'EOFSVC'
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
EOFSVC

sudo tee /etc/systemd/system/postgres_exporter.service > /dev/null << 'EOFSVC'
[Unit]
Description=Postgres Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/postgres_exporter \\
  --datasource="postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse?sslmode=disable"

[Install]
WantedBy=multi-user.target
EOFSVC

sudo tee /etc/systemd/system/otelcol.service > /dev/null << 'EOFSVC'
[Unit]
Description=OpenTelemetry Collector
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/otelcol --config="/home/cbwinslow/opendiscourse-monitoring/otel/otel-collector-config.yaml"
Environment=OTEL_EXPORTER_OTLP_ENDPOINT=https://cloudcurio.cc
Environment=OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer ${CLOUDCURIO_OTEL_TOKEN}

[Install]
WantedBy=multi-user.target
EOFSVC

sudo tee /etc/systemd/system/cloudflared.service > /dev/null << 'EOFSVC'
[Unit]
Description=Cloudflare Tunnel
Wants=network-online.target
After=network-online.target

[Service]
User=cbwinslow
Group=cbwinslow
Type=simple
ExecStart=/usr/local/bin/cloudflared tunnel --config="/home/cbwinslow/opendiscourse-monitoring/cloudflared/config.yml" run

[Install]
WantedBy=multi-user.target
EOFSVC

# Reload systemd
sudo systemctl daemon-reload

echo "✅ Remote monitoring stack installed!"
EOF

# Update Prometheus configuration for remote deployment
echo "⚙️  Updating Prometheus configuration for remote deployment..."
cat > /tmp/prometheus_remote.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'cbwdellr720'
    environment: 'production'

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - localhost:9093

scrape_configs:
  # Remote system metrics
  - job_name: 'cbwdellr720-system'
    static_configs:
      - targets: ['localhost:9100']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # Remote database metrics
  - job_name: 'cbwdellr720-database'
    static_configs:
      - targets: ['localhost:9187']
    metrics_path: '/metrics'
    scrape_interval: 30s

  # Remote ingestion metrics (from laptop)
  - job_name: 'opendiscourse-ingestion-remote'
    static_configs:
      - targets: ['100.90.23.60:8000']  # Your laptop IP
    metrics_path: '/metrics'
    scrape_interval: 10s
    scrape_timeout: 5s

  # OpenTelemetry Collector metrics
  - job_name: 'cbwdellr720-otel'
    static_configs:
      - targets: ['localhost:8888']
    metrics_path: '/metrics'
    scrape_interval: 15s

# Remote write to cloudcurio.cc
remote_write:
  - url: "https://cloudcurio.cc/api/v1/write"
    headers:
      Authorization: "Bearer ${CLOUDCURIO_TOKEN}"
    queue_config:
      max_samples_per_send: 1000
      max_shards: 200
      capacity: 2500
EOF

scp -i $SSH_KEY /tmp/prometheus_remote.yml $REMOTE_USER@$REMOTE_SERVER:$REMOTE_DIR/prometheus/prometheus.yml

# Update OpenTelemetry configuration for remote deployment
echo "🔧 Updating OpenTelemetry configuration for remote deployment..."
cat > /tmp/otel_remote.yaml << 'EOF'
receivers:
  # Prometheus metrics from remote system
  prometheus:
    config:
      scrape_configs:
        - job_name: 'cbwdellr720-system'
          static_configs:
            - targets: ['localhost:9100']
          scrape_interval: 30s
        - job_name: 'cbwdellr720-database'
          static_configs:
            - targets: ['localhost:9187']
          scrape_interval: 30s

  # PostgreSQL database receiver
  postgresql:
    endpoint: "postgresql://opendiscourse:opendiscourse123@100.90.23.60:5432/opendiscourse"
    collection_interval: 30s
    tls:
      insecure: true

  # Host metrics receiver
  hostmetrics:
    collection_interval: 30s
    scrapers:
      - cpu
      - disk
      - filesystem
      - load
      - memory
      - network
      - processes

  # OTLP receiver from laptop
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  resourcedetection:
    detectors: [env]
    timeout: 2s
    override: false

  resource:
    attributes:
      - key: service.name
        value: opendiscourse-monitoring
        action: upsert
      - key: service.version
        value: "1.0.0"
        action: upsert
      - key: deployment.environment
        value: "production"
        action: upsert
      - key: host.name
        value: "cbwdellr720"
        action: upsert

  batch:
    send_batch_size: 1000
    send_batch_max_size: 2000
    timeout: 5s

exporters:
  # Export to cloudcurio.cc
  otlp/cloudcurio:
    endpoint: "https://cloudcurio.cc:443"
    headers:
      Authorization: "Bearer ${CLOUDCURIO_OTEL_TOKEN}"
    tls:
      insecure: false
    sending_queue:
      enabled: true
      num_consumers: 10
      queue_size: 5000

  # Local Prometheus for backup
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: "opendiscourse"
    const_labels:
      environment: "production"
      host: "cbwdellr720"

service:
  extensions: [health_check]
  
  pipelines:
    metrics:
      receivers: [prometheus, postgresql, hostmetrics, otlp]
      processors: [resourcedetection, resource, batch]
      exporters: [otlp/cloudcurio, prometheus]

    logs:
      receivers: [otlp]
      processors: [resourcedetection, resource, batch]
      exporters: [otlp/cloudcurio]

    traces:
      receivers: [otlp]
      processors: [resourcedetection, resource, batch]
      exporters: [otlp/cloudcurio]
EOF

scp -i $SSH_KEY /tmp/otel_remote.yaml $REMOTE_USER@$REMOTE_SERVER:$REMOTE_DIR/otel/otel-collector-config.yaml

# Start remote services
echo "🚀 Starting remote monitoring services..."
ssh -i $SSH_KEY $REMOTE_USER@$REMOTE_SERVER << 'EOF'
sudo systemctl enable prometheus
sudo systemctl enable node_exporter
sudo systemctl enable postgres_exporter
sudo systemctl enable otelcol

sudo systemctl start prometheus
sudo systemctl start node_exporter
sudo systemctl start postgres_exporter
sudo systemctl start otelcol

# Wait for services to start
sleep 5

# Check service status
echo "📊 Checking remote service status..."
for service in prometheus node_exporter postgres_exporter otelcol; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service is running on cbwdellr720"
    else
        echo "❌ $service failed to start on cbwdellr720"
        systemctl status $service
    fi
done
EOF

# Setup SSH websocket tunnels for monitoring access
echo "🌐 Setting up SSH websocket tunnels..."
cat > /tmp/setup_ssh_tunnels.sh << 'EOF'
#!/bin/bash
# SSH websocket tunnels for monitoring access

echo "🔗 Establishing SSH websocket tunnels to monitoring stack..."

# Kill existing tunnels
pkill -f "ssh -N -L"

# Create tunnels to remote monitoring services
ssh -N -L 8001:localhost:8000 cbwinslow@cbwdellr720 &
ssh -N -L 3001:localhost:3000 cbwinslow@cbwdellr720 &
ssh -N -L 3101:localhost:3100 cbwinslow@cbwdellr720 &
ssh -N -L 9091:localhost:9090 cbwinslow@cbwdellr720 &
ssh -N -L 8889:localhost:8889 cbwinslow@cbwdellr720 &
ssh -N -L 4317:localhost:4317 cbwinslow@cbwdellr720 &
ssh -N -L 4318:localhost:4318 cbwinslow@cbwdellr720 &

echo "✅ SSH tunnels established:"
echo "  - Prometheus: http://localhost:8001"
echo "  - Grafana: http://localhost:3001"
echo "  - Loki: http://localhost:3101"
echo "  - AlertManager: http://localhost:9091"
echo "  - OTEL Collector: http://localhost:8889"
echo "  - OTLP gRPC: localhost:4317"
echo "  - OTLP HTTP: localhost:4318"

echo "🔍 Monitoring stack is accessible via localhost tunnels!"
echo "📊 Prometheus: http://localhost:8001"
echo "📈 Grafana: http://localhost:3001"
echo "📋 Loki: http://localhost:3101"
EOF

chmod +x /tmp/setup_ssh_tunnels.sh
mv /tmp/setup_ssh_tunnels.sh ./scripts/setup_ssh_tunnels.sh

# Update local monitoring framework to push data to remote
echo "📤 Updating local ingestion to push metrics to remote server..."
cat > /tmp/remote_monitoring_config.py << 'EOF'
# Remote monitoring configuration for local ingestion scripts
import os

# Remote monitoring endpoints
REMOTE_OTLP_ENDPOINT = "http://cbwdellr720:4318"
REMOTE_PROMETHEUS_GATEWAY = "http://cbwdellr720:8889"
REMOTE_LOKI_ENDPOINT = "http://cbwdellr720:3100/loki/api/v1/push"

# Environment variables for remote monitoring
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = REMOTE_OTLP_ENDPOINT
os.environ['OTEL_EXPORTER_OTLP_HEADERS'] = ''
os.environ['PROMETHEUS_GATEWAY_URL'] = REMOTE_PROMETHEUS_GATEWAY
os.environ['LOKI_URL'] = REMOTE_LOKI_ENDPOINT

# Feature flags for remote monitoring
os.environ['ENABLE_OPENTELEMETRY'] = 'true'
os.environ['ENABLE_PROMETHEUS'] = 'true'
os.environ['ENABLE_LOKI_LOGGING'] = 'true'
os.environ['ENABLE_ALLOY_OBSERVABILITY'] = 'true'
os.environ['ENABLE_DETAILED_TRIGGERS'] = 'true'
os.environ['ENABLE_BENCHMARKING'] = 'true'
os.environ['ENABLE_TELEMETRY'] = 'true'
os.environ['ENABLE_ERROR_TRACKING'] = 'true'
os.environ['ENABLE_PERFORMANCE_METRICS'] = 'true'
EOF

scp -i $SSH_KEY /tmp/remote_monitoring_config.py $REMOTE_USER@$REMOTE_SERVER:$REMOTE_DIR/

echo "🎉 Remote monitoring stack deployment complete!"
echo ""
echo "📊 Remote Monitoring Stack on cbwdellr720:"
echo "  - Prometheus: http://cbwdellr720:8000"
echo "  - Node Exporter: http://cbwdellr720:9100/metrics"
echo "  - Postgres Exporter: http://cbwdellr720:9187/metrics"
echo "  - OpenTelemetry: http://cbwdellr720:8888/metrics"
echo ""
echo "🌐 Local Access via SSH Tunnels:"
echo "  Run: ./scripts/setup_ssh_tunnels.sh"
echo "  Then access:"
echo "    - Prometheus: http://localhost:8001"
echo "    - Grafana: http://localhost:3001"
echo "    - Loki: http://localhost:3101"
echo ""
echo "📤 Data Flow:"
echo "  Local Ingestion → Remote OTEL Collector → cloudcurio.cc"
echo "  Remote System → Remote Prometheus → cloudcurio.cc"
echo ""
echo "🔧 Next Steps:"
echo "1. Run: ./scripts/setup_ssh_tunnels.sh"
echo "2. Set environment variables for cloudcurio.cc tokens"
echo "3. Start ingestion - data will flow to remote monitoring"
echo "4. Access dashboards via localhost tunnels"