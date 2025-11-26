# API Reference - Complete Documentation

## 🎯 Overview

Comprehensive API reference for unified ingestion system and personal monitoring system.

---

## 📚 Table of Contents

1. [Unified Ingestion API](#unified-ingestion-api)
2. [Personal Monitoring API](#personal-monitoring-api)
3. [Database Schema API](#database-schema-api)
4. [Configuration API](#configuration-api)
5. [Error Handling](#error-handling)

---

## 🚀 Unified Ingestion API

### Main Entry Point
```bash
python unified_ingestion_fixed.py [OPTIONS]
```

### Core Classes

#### UnifiedIngester
```python
class UnifiedIngester:
    """Main unified ingestion class"""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize unified ingestion system
        
        Args:
            dry_run (bool): If True, only show what would be executed
        """
        
    def ingest(self, source: DataSource, **kwargs) -> List[IngestionResult]:
        """
        Main ingestion method
        
        Args:
            source (DataSource): Data source to ingest from
            **kwargs: Source-specific parameters
            
        Returns:
            List[IngestionResult]: Results for each ingestion task
        """
        
    def print_summary(self):
        """Print comprehensive ingestion summary"""
```

#### DataSource Enum
```python
class DataSource(Enum):
    """Available data sources"""
    CONGRESS = "congress"
    GOVINFO = "govinfo"
    OPENSTATES = "openstates"
    ALL = "all"
```

#### CongressDataType Enum
```python
class CongressDataType(Enum):
    """Congress data types"""
    BILLS = "bills"
    MEMBERS = "members"
    COMMITTEES = "committees"
    VOTES = "votes"
    BILL_ACTIONS = "bill_actions"
    BILL_TEXT = "bill_text"
    SUMMARIES = "summaries"
    TREATIES = "treaties"
    NOMINATIONS = "nominations"
    HEARINGS = "hearings"
    CONGRESS = "congress"
    ALL = "all"
```

#### GovInfoCollection Enum
```python
class GovInfoCollection(Enum):
    """GovInfo collections"""
    BILLS = "BILLS"
    STATUTES = "STATUTES"
    CRR = "CRR"  # Congressional Record
    CRPT = "CRPT"  # Committee Reports
    CREC = "CREC"  # Congressional Record Electronic
    FR = "FR"  # Federal Register
    GPO = "GPO"  # Government Publishing Office
```

#### IngestionResult Dataclass
```python
@dataclass
class IngestionResult:
    """Result of an ingestion operation"""
    source: str                    # Data source name
    data_type: str                 # Specific data type
    success: bool                  # Success status
    records_processed: int          # Number of records processed
    duration: float               # Duration in seconds
    errors: List[str]             # Error messages
    parameters: Dict[str, Any]     # Parameters used
```

### Command Line Parameters

#### Global Parameters
| Parameter | Type | Required | Default | Description |
|-----------|-------|----------|----------|-------------|
| `--source` | Choice | ✅ Required | - | Data source: congress, govinfo, openstates, all |
| `--dry-run` | flag | ❌ Optional | false | Show what would be executed without running |

#### Congress Parameters
| Parameter | Type | Required | Default | Description |
|-----------|-------|----------|----------|-------------|
| `--data-type` | Choice[] | ❌ Optional | all | Congress data types (see CongressDataType) |
| `--congress` | int[] | ❌ Optional | - | Congress number(s): 116, 117, 118, 119 |
| `--max-pages` | int | ❌ Optional | 10 | Maximum pages to ingest |
| `--per-page` | int | ❌ Optional | 20 | Records per page |
| `--timeout` | int | ❌ Optional | 300 | Script timeout in seconds |

#### GovInfo Parameters
| Parameter | Type | Required | Default | Description |
|-----------|-------|----------|----------|-------------|
| `--collection` | Choice | ❌ Optional | BILLS | GovInfo collection (see GovInfoCollection) |
| `--year` | int | ❌ Optional | - | Year for GovInfo data |
| `--download-dir` | string | ❌ Optional | ./data | Download directory |
| `--timeout` | int | ❌ Optional | 600 | Script timeout in seconds |

#### OpenStates Parameters
| Parameter | Type | Required | Default | Description |
|-----------|-------|----------|----------|-------------|
| `--jurisdiction` | string | ❌ Optional | - | OpenStates jurisdiction code |
| `--query` | string | ❌ Optional | - | OpenStates search query |
| `--per-page` | int | ❌ Optional | 50 | Records per page |
| `--timeout` | int | ❌ Optional | 300 | Script timeout in seconds |

### Usage Examples

#### Basic Usage
```bash
# Ingest Congress members
python unified_ingestion_fixed.py --source congress --data-type members --congress 118

# Ingest GovInfo bills
python unified_ingestion_fixed.py --source govinfo --collection BILLS --year 2023

# Ingest OpenStates data
python unified_ingestion_fixed.py --source openstates --jurisdiction ca
```

#### Advanced Usage
```bash
# Multiple data types
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members committees votes \
  --congress 118 \
  --max-pages 5

# Multiple congresses
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 116 117 118 \
  --max-pages 10

# Comprehensive ingestion
python unified_ingestion_fixed.py \
  --source congress \
  --congress 118 \
  --comprehensive \
  --max-pages 5

# Dry run
python unified_ingestion_fixed.py \
  --source congress \
  --data-type members \
  --congress 118 \
  --dry-run
```

---

## 🖥️ Personal Monitoring API

### Core Classes

#### ActivityLogger
```python
class ActivityLogger:
    """Tracks user activity including applications, websites, typing, and interactions"""
    
    def __init__(self, db_url: str, log_interval: int = 60):
        """
        Initialize activity logger
        
        Args:
            db_url (str): Database connection string
            log_interval (int): Seconds between activity logs (default: 60)
        """
        
    def on_key_press(self, event):
        """Handle keyboard events"""
        
    def on_mouse_click(self, x, y, button, pressed):
        """Handle mouse events"""
        
    def get_active_window_info(self):
        """Get current active window information"""
        
    def get_system_metrics(self):
        """Collect system performance metrics"""
        
    def log_activity(self):
        """Log current activity to database"""
        
    def start_monitoring(self):
        """Start activity monitoring"""
        
    def stop(self):
        """Stop monitoring"""
```

#### ScreenCapture
```python
class ScreenCapture:
    """Automated screenshot capture with analysis"""
    
    def __init__(self, db_url: str, capture_interval: int = 30, output_dir: str = "./screenshots"):
        """
        Initialize screen capture
        
        Args:
            db_url (str): Database connection string
            capture_interval (int): Seconds between captures (default: 30)
            output_dir (str): Screenshot storage directory
        """
        
    def capture_screen(self):
        """Capture and save screenshot"""
        
    def analyze_screenshot(self, image_path: str):
        """Analyze screenshot with Ollama"""
        
    def store_screen_capture(self, filename: str, file_size: int, resolution: str, analysis: str):
        """Store screenshot information in database"""
        
    def start_capture(self):
        """Start continuous screen capture"""
        
    def stop(self):
        """Stop screen capture"""
```

#### OllamaSummarizer
```python
class OllamaSummarizer:
    """Real-time activity summarization using Ollama"""
    
    def __init__(self, db_url: str, ollama_host: str = "http://localhost:11434", model: str = "llama3.2:1b"):
        """
        Initialize Ollama summarizer
        
        Args:
            db_url (str): Database connection string
            ollama_host (str): Ollama API endpoint
            model (str): AI model to use for summarization
        """
        
    def check_ollama(self):
        """Check if Ollama is available"""
        
    def get_recent_activity(self, hours: int = 1):
        """Get recent activity data for summarization"""
        
    def summarize_activities(self, activities: List) -> str:
        """Summarize activities using Ollama"""
        
    def format_activities_for_ollama(self, activities: List) -> str:
        """Format activities for Ollama prompt"""
        
    def store_summary(self, activity_ids: List[int], summary: str):
        """Store summary in database"""
        
    def process_summaries(self):
        """Main processing loop for summaries"""
        
    def start(self):
        """Start summarizer"""
        
    def stop(self):
        """Stop summarizer"""
```

### Usage Examples

#### Activity Monitoring
```bash
# Start with default settings
python3 activity_logger.py

# Custom interval
python3 activity_logger.py --log_interval 30

# Custom database
python3 activity_logger.py --db_url "postgresql://user:pass@host:5432/db"
```

#### Screen Capture
```bash
# Start with default settings
python3 screen_capture.py

# Custom interval
python3 screen_capture.py --interval 60

# Custom output directory
python3 screen_capture.py --output_dir /path/to/screenshots
```

#### Ollama Summarization
```bash
# Start with default settings
python3 ollama_summarizer.py

# Custom Ollama host
python3 ollama_summarizer.py --ollama_host http://localhost:11434

# Different model
python3 ollama_summarizer.py --model llama3.2:3b
```

---

## 🗄️ Database Schema API

### Tables

#### activity_logs
```sql
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activity_type VARCHAR(50),              -- 'user_activity', 'system_event'
    application VARCHAR(100),               -- Active application name
    website VARCHAR(255),                    -- Website (if browser)
    duration_seconds INTEGER,                 -- Activity duration
    keystrokes INTEGER,                      -- Keystroke count
    mouse_clicks INTEGER,                   -- Mouse click count
    window_title VARCHAR(255),                -- Active window title
    agent_interaction TEXT,                   -- AI agent interactions
    summary TEXT,                           -- AI-generated summary
    raw_data JSONB,                         -- Raw activity data
    synced_to_homelab BOOLEAN DEFAULT FALSE, -- Sync status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### screen_captures
```sql
CREATE TABLE screen_captures (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    file_path VARCHAR(500),                 -- Screenshot file path
    file_size INTEGER,                       -- File size in bytes
    resolution VARCHAR(20),                  -- Screen resolution
    analysis_result TEXT,                     -- AI analysis result
    summary TEXT,                           -- Brief summary
    synced_to_homelab BOOLEAN DEFAULT FALSE, -- Sync status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### agent_interactions
```sql
CREATE TABLE agent_interactions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100),                 -- Agent name
    interaction_type VARCHAR(50),             -- 'conversation', 'command', 'query'
    conversation_text TEXT,                   -- Full conversation
    summary TEXT,                           -- AI-generated summary
    context JSONB,                          -- Interaction context
    synced_to_homelab BOOLEAN DEFAULT FALSE, -- Sync status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### system_metrics
```sql
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_percent DECIMAL(5,2),              -- CPU usage percentage
    memory_percent DECIMAL(5,2),            -- Memory usage percentage
    disk_usage_gb DECIMAL(10,2),            -- Disk usage in GB
    network_bytes_sent BIGINT,                 -- Network bytes sent
    network_bytes_recv BIGINT,                 -- Network bytes received
    active_processes INTEGER,                  -- Active process count
    uptime_seconds INTEGER,                   -- System uptime
    synced_to_homelab BOOLEAN DEFAULT FALSE, -- Sync status
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes
```sql
-- Performance indexes
CREATE INDEX idx_activity_logs_timestamp ON activity_logs(timestamp);
CREATE INDEX idx_screen_captures_timestamp ON screen_captures(timestamp);
CREATE INDEX idx_agent_interactions_timestamp ON agent_interactions(timestamp);
CREATE INDEX idx_system_metrics_timestamp ON system_metrics(timestamp);

-- Sync status indexes
CREATE INDEX idx_activity_logs_synced ON activity_logs(synced_to_homelab);
CREATE INDEX idx_screen_captures_synced ON screen_captures(synced_to_homelab);
CREATE INDEX idx_agent_interactions_synced ON agent_interactions(synced_to_homelab);
CREATE INDEX idx_system_metrics_synced ON system_metrics(synced_to_homelab);
```

### Common Queries

#### Activity Analysis
```sql
-- Daily activity summary
SELECT 
    DATE(timestamp) as date,
    application,
    SUM(duration_seconds) as total_time,
    COUNT(*) as sessions,
    SUM(keystrokes) as total_keystrokes,
    SUM(mouse_clicks) as total_clicks
FROM activity_logs 
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(timestamp), application
ORDER BY date, total_time DESC;

-- Productivity patterns
SELECT 
    EXTRACT(HOUR FROM timestamp) as hour,
    application,
    COUNT(*) as activity_count
FROM activity_logs 
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY EXTRACT(HOUR FROM timestamp), application
ORDER BY hour, activity_count DESC;
```

#### Screen Capture Analysis
```sql
-- Screenshot frequency
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as screenshot_count,
    AVG(file_size) as avg_size
FROM screen_captures 
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY date;

-- Storage usage
SELECT 
    SUM(file_size) as total_size,
    SUM(file_size) / 1024.0 / 1024.0 / 1024.0 as total_gb,
    COUNT(*) as total_screenshots
FROM screen_captures;
```

#### AI Summary Analysis
```sql
-- Recent AI summaries
SELECT 
    summary,
    COUNT(*) as frequency,
    MAX(timestamp) as last_seen
FROM activity_logs 
WHERE summary IS NOT NULL
    AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY summary
ORDER BY frequency DESC, last_seen DESC
LIMIT 10;
```

---

## ⚙️ Configuration API

### Environment Variables

#### Unified Ingestion
```bash
# Database
DATABASE_URL=postgresql://opendiscourse:opendiscourse123@localhost:5432/opendiscourse

# API Keys
CONGRESS_API_KEY=your_congress_api_key
GOVINFO_API_KEY=your_govinfo_api_key
OPENSTATES_API_KEY=your_openstates_api_key

# Python Path
PYTHONPATH=/home/cbwinslow/opendiscourse:$PYTHONPATH
```

#### Personal Monitoring
```bash
# Database
MONITORING_DB=postgresql://cbwinslow@localhost:5432/monitoring_db

# Ollama
OLLAMA_HOST=http://localhost:11434

# Capture Settings
SCREEN_CAPTURE_INTERVAL=30
ACTIVITY_LOG_INTERVAL=60

# Sync Settings
SYNC_INTERVAL=300
HOMELAB_URL=http://100.90.251.120:8080

# Data Retention
DATA_RETENTION_DAYS=90
```

### Configuration Files

#### monitoring/.env
```bash
# Personal Monitoring Configuration
MONITORING_DB=postgresql://cbwinslow@localhost:5432/monitoring_db
OLLAMA_HOST=http://localhost:11434
SCREEN_CAPTURE_INTERVAL=30
ACTIVITY_LOG_INTERVAL=60
SYNC_INTERVAL=300
HOMELAB_URL=http://100.90.251.120:8080
DATA_RETENTION_DAYS=90
```

#### mcp_server/.env
```bash
# Unified Ingestion Configuration
export CONGRESS_API_KEY="your_congress_api_key"
export GOVINFO_API_KEY="your_govinfo_api_key"
export OPENSTATES_API_KEY="your_openstates_api_key"
DATABASE_URL=postgresql://opendiscourse:opendiscourse123@localhost:5432/opendiscourse
```

---

## 🚨 Error Handling

### Common Error Types

#### Database Errors
```python
# Connection errors
psycopg2.OperationalError: could not connect to server
# Solution: Check database connection and credentials

# Table not found
psycopg2.errors.UndefinedTable: relation "table_name" does not exist
# Solution: Run database schema creation

# Permission errors
psycopg2.errors.InsufficientPrivilege: permission denied for relation
# Solution: Check database user permissions
```

#### API Errors
```python
# Authentication errors
requests.exceptions.HTTPError: 401 Client Error: Unauthorized
# Solution: Check API keys

# Rate limiting
requests.exceptions.HTTPError: 429 Client Error: Too Many Requests
# Solution: Reduce request frequency or add delays

# Network errors
requests.exceptions.ConnectionError: Connection failed
# Solution: Check network connectivity
```

#### File System Errors
```python
# Permission errors
PermissionError: [Errno 13] Permission denied
# Solution: Check file permissions

# Disk space errors
OSError: [Errno 28] No space left on device
# Solution: Clean up disk space

# File not found
FileNotFoundError: [Errno 2] No such file or directory
# Solution: Check file paths
```

### Error Recovery

#### Automatic Retry
```python
import time
import requests
from functools import wraps

def retry(max_attempts=3, delay=1):
    """Decorator for retrying failed operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    print(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
        return wrapper
    return decorator

@retry(max_attempts=3, delay=2)
def api_call(url):
    return requests.get(url)
```

#### Graceful Degradation
```python
def safe_api_call(url, fallback=None):
    """Make API call with fallback"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API call failed: {e}")
        if fallback:
            return fallback
        return None
```

#### Logging and Monitoring
```python
import logging
import traceback

def setup_logging():
    """Setup comprehensive logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

def handle_error(error, context=""):
    """Handle errors with logging and context"""
    logging.error(f"Error in {context}: {error}")
    logging.error(f"Traceback: {traceback.format_exc()}")
    
    # Send notification if critical
    if isinstance(error, CriticalError):
        send_notification(f"Critical error: {error}")
```

---

## 📞 Support and Resources

### Getting Help
```bash
# Command line help
python unified_ingestion_fixed.py --help
python3 activity_logger.py --help
python3 screen_capture.py --help
python3 ollama_summarizer.py --help

# Check system status
./monitoring_status.sh

# Database diagnostics
psql "$DATABASE_URL" -c "\dt"
psql "$MONITORING_DB" -c "\dt"
```

### Log Locations
```bash
# Application logs
tail -f logs/ingestion.log
tail -f logs/activity.log
tail -f logs/screen.log
tail -f logs/summarizer.log

# Database logs
docker logs mcp-postgres

# System logs
journalctl -u opendiscourse -f
```

### Performance Monitoring
```bash
# System resources
htop                          # CPU and memory
iotop                          # Disk I/O
nethogs                         # Network

# Database performance
psql "$DATABASE_URL" -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes
FROM pg_stat_user_tables 
WHERE schemaname = 'public''
ORDER BY n_tup_ins DESC;"
```

---

## 📚 Additional Resources

### Documentation
- **Unified Ingestion Workflow**: `/docs/workflows/unified-ingestion-workflow.md`
- **Personal Monitoring Workflow**: `/docs/workflows/personal-monitoring-workflow.md`
- **Code Examples**: `/docs/examples/`
- **Troubleshooting**: `/docs/troubleshooting/`

### Community Support
- **GitHub Issues**: https://github.com/cbwinslow/opendiscourse-mcp/issues
- **GitLab Issues**: https://gitlab.com/cbwinslow/opendiscourse-mcp/-/issues
- **Documentation**: https://cbwinslow.github.io/opendiscourse-mcp/

### Development
- **API Reference**: This document
- **Source Code**: `/mcp_server/` and `/monitoring/`
- **Tests**: `/tests/`
- **Examples**: `/docs/examples/`

---

*This API reference covers all components of the unified ingestion and personal monitoring systems.*