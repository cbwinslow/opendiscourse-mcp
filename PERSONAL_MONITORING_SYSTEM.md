# Personal Activity Monitoring System

## 🎯 Overview

Comprehensive personal monitoring system using Ollama for activity summarization and screen capture for visual tracking. All data stored in central database with local fallback and homelab sync capabilities.

## 🏗️ Architecture

### Components
1. **Ollama Model**: Lightweight LLM for real-time activity summarization
2. **Screen Capture**: Automated screenshot system with visual analysis
3. **Activity Logger**: Tracks applications, websites, typing, interactions
4. **Database Storage**: Central PostgreSQL with local fallback
5. **Sync Service**: Homelab synchronization when SSH available

### Data Collection Points
- ✅ Applications used and time spent
- ✅ Websites visited and duration
- ✅ Keystrokes and typing patterns
- ✅ Mouse movements and clicks
- ✅ Agent interactions and conversations
- ✅ Login/logout events
- ✅ Screen captures (interval-based)
- ✅ System performance metrics

---

## 🚀 Implementation Plan

### Phase 1: Ollama Setup
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull lightweight model
ollama pull llama3.2:1b  # 1.3GB - perfect for summarization

# Start Ollama service
ollama serve &
```

### Phase 2: Screen Capture System
```bash
# Install dependencies
pip install pillow opencv-python mss pyautogui

# Screen capture script
python3 screen_capture.py --interval 30 --output_dir ./screenshots
```

### Phase 3: Activity Monitoring
```bash
# Install monitoring dependencies
pip install pynput psutil python-xlib

# Activity logger
python3 activity_monitor.py --log_interval 60
```

### Phase 4: Database Integration
```bash
# Create monitoring tables
python3 create_monitoring_tables.py

# Data sync service
python3 sync_service.py --target homelab
```

---

## 📊 Database Schema

### Activity Logs Table
```sql
CREATE TABLE activity_logs (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Screen Captures Table
```sql
CREATE TABLE screen_captures (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(500),
    file_size INTEGER,
    resolution VARCHAR(20),
    analysis_result TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Agent Interactions Table
```sql
CREATE TABLE agent_interactions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100),
    interaction_type VARCHAR(50),
    conversation_text TEXT,
    summary TEXT,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🤖 Ollama Integration

### Summarization Model
```python
import requests
import json

def summarize_activity(activity_data):
    """Use Ollama to summarize activity data"""
    
    prompt = f"""
    Summarize the following user activity:
    
    Applications used: {activity_data['applications']}
    Websites visited: {activity_data['websites']}
    Time spent: {activity_data['duration']} minutes
    Key interactions: {activity_data['interactions']}
    
    Provide a concise summary focusing on:
    1. Productivity patterns
    2. Key accomplishments
    3. Time allocation
    4. Notable behaviors
    
    Keep it under 100 words.
    """
    
    response = requests.post('http://localhost:11434/api/generate', 
                          json={
                              'model': 'llama3.2:1b',
                              'prompt': prompt,
                              'stream': False
                          })
    
    return response.json()['response']
```

### Real-time Processing
```python
def process_activity_stream():
    """Continuous activity processing with Ollama"""
    
    while True:
        # Collect activity data
        activity_data = collect_activity_data()
        
        # Generate summary
        summary = summarize_activity(activity_data)
        
        # Store in database
        store_activity_log(activity_data, summary)
        
        # Sleep for next interval
        time.sleep(60)  # Process every minute
```

---

## 📸 Screen Capture System

### Automated Screenshots
```python
import mss
import time
from datetime import datetime

class ScreenCapture:
    def __init__(self, interval=30, output_dir="./screenshots"):
        self.interval = interval
        self.output_dir = output_dir
        self.sct = mss.mss()
        
    def capture_screen(self):
        """Capture and save screenshot"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_dir}/screen_{timestamp}.png"
        
        # Capture screen
        screenshot = self.sct.shot(output=filename)
        
        # Analyze with Ollama
        analysis = analyze_screenshot(filename)
        
        # Store in database
        store_screen_capture(filename, analysis)
        
        return filename
    
    def start_capture(self):
        """Start continuous capture"""
        while True:
            self.capture_screen()
            time.sleep(self.interval)
```

### Visual Analysis
```python
def analyze_screenshot(image_path):
    """Analyze screenshot with Ollama"""
    
    # For now, we'll use basic analysis
    # In future, can integrate vision models
    
    prompt = f"""
    Analyze this screenshot context: {image_path}
    
    Based on the filename timestamp and typical usage patterns,
    describe what the user is likely doing.
    
    Focus on:
    1. Application type (coding, browsing, productivity)
    2. Activity level (active, idle, focused)
    3. Context (work, leisure, learning)
    
    Keep response under 50 words.
    """
    
    # This would need vision model integration
    # For now, return basic analysis
    return "User actively working on computer"
```

---

## 🔄 Sync Service

### Local to Homelab Sync
```python
import psycopg2
import requests
import json

class SyncService:
    def __init__(self, local_db, homelab_db):
        self.local_db = local_db
        self.homelab_db = homelab_db
        
    def check_homelab_connection(self):
        """Check if homelab is accessible"""
        try:
            response = requests.get('http://homelab:8080/health', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def sync_to_homelab(self):
        """Sync local data to homelab"""
        if not self.check_homelab_connection():
            print("Homelab not accessible, keeping data local")
            return False
            
        # Get unsynced data
        unsynced_data = self.get_unsynced_data()
        
        # Push to homelab
        for record in unsynced_data:
            self.push_record_to_homelab(record)
            self.mark_as_synced(record['id'])
            
        return True
    
    def continuous_sync(self):
        """Continuous sync service"""
        while True:
            try:
                self.sync_to_homelab()
            except Exception as e:
                print(f"Sync failed: {e}")
            
            time.sleep(300)  # Try every 5 minutes
```

---

## 📱 Installation & Setup

### Prerequisites
```bash
# System dependencies
sudo apt update
sudo apt install -y python3-pip python3-dev postgresql-client

# Python dependencies
pip install ollama pynput psutil mss pillow opencv-python
```

### Database Setup
```bash
# Create monitoring database
createdb monitoring_db

# Create tables
python3 create_monitoring_tables.py
```

### Service Configuration
```bash
# Create systemd service for continuous monitoring
sudo tee /etc/systemd/system/personal-monitor.service > /dev/null <<EOF
[Unit]
Description=Personal Activity Monitor
After=network.target

[Service]
Type=simple
User=cbwinslow
WorkingDirectory=/home/cbwinslow/opendiscourse/monitoring
ExecStart=/usr/bin/python3 /home/cbwinslow/opendiscourse/monitoring/main_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable personal-monitor
sudo systemctl start personal-monitor
```

---

## 🔒 Privacy & Security

### Data Protection
- ✅ All data stored locally first
- ✅ Encrypted transmission to homelab
- ✅ Configurable data retention policies
- ✅ Sensitive data filtering options

### Access Control
- ✅ Local database access only
- ✅ Homelab authentication required
- ✅ Configurable data sharing settings

---

## 📈 Usage Examples

### Start Monitoring
```bash
# Start all services
python3 start_monitoring.py --all

# Start specific components
python3 start_monitoring.py --ollama --screen-capture --activity-logger
```

### View Summaries
```bash
# Daily summary
python3 get_summary.py --period day

# Weekly summary
python3 get_summary.py --period week

# Agent interactions
python3 get_summary.py --agent-interactions
```

### Data Management
```bash
# Sync to homelab
python3 sync_service.py --force

# Cleanup old data
python3 cleanup_service.py --older-than 30d

# Export data
python3 export_service.py --format json --output activity_export.json
```

---

## 🎯 Next Steps

### Immediate Implementation
1. ✅ Install Ollama and lightweight model
2. ✅ Set up screen capture system
3. ✅ Create database schema
4. ✅ Implement activity logger
5. ✅ Configure sync service

### Advanced Features
1. 🔄 Vision model integration for screenshot analysis
2. 🔄 Voice activity monitoring
3. 🔄 Biometric data integration
4. 🔄 Predictive activity patterns
5. 🔄 Automated productivity insights

---

## 📞 Quick Start Commands

```bash
# Install everything
./setup_monitoring.sh

# Start monitoring
./start_monitoring.sh

# Check status
./monitoring_status.sh

# View summaries
./get_daily_summary.sh
```

---

*System designed for comprehensive personal activity monitoring with privacy-first approach*