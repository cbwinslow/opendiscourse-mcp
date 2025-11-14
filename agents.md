# AI Agent Guide for OpenDiscourse MCP System

This document provides essential information for AI agents working with the OpenDiscourse legislative data ingestion and monitoring system.

## 🤖 Agent Responsibilities

AI agents interacting with this system should:

1. **Understand the trigger-based monitoring system** - Data ingestion progress is tracked automatically via database triggers
2. **Respect database transaction boundaries** - Job contexts are session-based
3. **Follow ingestion workflow patterns** - Use proper job lifecycle management
4. **Handle concurrent operations safely** - Multiple agents may work simultaneously
5. **Monitor system health** - Check database connectivity and trigger functionality

## 🏗️ System Architecture Overview

### Core Components

#### 1. **Database Trigger Monitoring System**
- **Automatic progress tracking** via PostgreSQL triggers
- **Session-based job context** using `ingestion.active_job_id`
- **Real-time updates** - no manual progress reporting needed
- **Concurrent job isolation** - each database session tracks its own job

#### 2. **Data Sources**
- **Congress.gov API** - Federal legislative data (bills, members, votes, committees)
- **OpenStates API** - State legislative data (50+ state legislatures)
- **GovInfo API** - Government publications and official documents

#### 3. **MCP Server**
- **FastAPI-based** REST API for system management
- **Ingestion job monitoring** endpoints
- **Health checks** and system status
- **Remote execution** capabilities

### Key Files and Locations

```
├── mcp_server/
│   ├── main.py                 # FastAPI server
│   ├── utils/
│   │   ├── monitoring.py       # Trigger-based monitoring system
│   │   └── db.py              # Database connection helpers
│   ├── clients/               # API client libraries
│   │   ├── congress_client.py
│   │   ├── openstates_client.py
│   │   └── govinfo_client.py
│   ├── scripts/               # Ingestion scripts
│   │   ├── congress_ingest.py
│   │   ├── openstates_ingest.py
│   │   └── govinfo_ingest.py
│   └── sql/
│       └── monitoring_triggers.sql  # Database triggers
├── tests/                     # Comprehensive test suite
├── docs/                      # Documentation
└── *.md                       # Various guides and rules
```

## 🔄 Ingestion Workflow for Agents

### Standard Ingestion Pattern

```python
from mcp_server.utils.monitoring import monitor

# 1. Create job (automatically saved to database)
job_id = monitor.create_job('congress', 'bills_118_hr')

# 2. Use context manager (sets/clears job context automatically)
with monitor.monitor_job(job_id):
    # Job context is now active for this database session
    # Triggers will automatically increment processed_records

    for bill in congress_api.get_bills():
        # Insert data - triggers fire automatically
        db.insert_bill(bill)
        # NO manual progress updates needed!

# 3. Job automatically marked as completed
# Context automatically cleared
```

### Important Agent Behaviors

#### **Job Context Awareness**
- **Session-scoped**: Job context is per-database-connection
- **Automatic management**: Context manager handles setting/clearing
- **Concurrent safety**: Multiple agents can run simultaneously

#### **Trigger Dependencies**
- **Database triggers must be installed** before ingestion
- **Check trigger health** before starting large jobs
- **Monitor trigger performance** for long-running ingestions

#### **Error Handling**
- **Context cleanup**: Always clear job context on errors
- **Transaction rollback**: Failed inserts don't count toward progress
- **Job status updates**: Mark jobs as failed appropriately

## 📊 Monitoring and Health Checks

### Essential Checks for Agents

#### **Database Connectivity**
```python
# Always verify database connection before operations
from mcp_server.db import get_sqlalchemy_engine
engine = get_sqlalchemy_engine()
with engine.connect() as conn:
    conn.execute("SELECT 1")
```

#### **Trigger System Health**
```python
# Verify triggers are installed and working
cur = conn.cursor()
cur.execute("""
    SELECT COUNT(*) FROM pg_trigger
    WHERE tgname LIKE 'trg_%_progress'
""")
trigger_count = cur.fetchone()[0]
assert trigger_count >= 15  # Should have triggers on all main tables
```

#### **Job Context Verification**
```python
# Check if job context is properly set
cur.execute("SELECT current_setting('ingestion.active_job_id', TRUE)")
active_job = cur.fetchone()[0]
# Should match expected job_id during ingestion
```

#### **Real-time Progress Monitoring**
```python
# Get live progress updates
progress = monitor.get_job_progress(job_id)
print(f"Processed: {progress['processed_records']}")
print(f"Status: {progress['status']}")
```

## 🚨 Critical Agent Rules

### **Database Operations**
1. **Never manually update `processed_records`** - triggers handle this
2. **Always use context managers** for job lifecycle
3. **Check database health** before starting ingestion
4. **Handle transaction failures** gracefully

### **Concurrent Operations**
1. **Use separate database connections** for concurrent jobs
2. **Verify job isolation** - one job per session
3. **Monitor for deadlocks** in high-concurrency scenarios
4. **Respect rate limits** on external APIs

### **Error Recovery**
1. **Clear job context** on any error
2. **Mark jobs as failed** appropriately
3. **Log detailed error information** for debugging
4. **Retry failed operations** with exponential backoff

### **Resource Management**
1. **Close database connections** after use
2. **Monitor memory usage** during large ingestions
3. **Handle API rate limits** appropriately
4. **Clean up temporary data** after processing

## 🔧 Technical Details for Agents

### **Trigger System Internals**

#### **How Triggers Work**
```sql
-- Trigger function automatically called on INSERT
CREATE OR REPLACE FUNCTION update_ingestion_progress()
RETURNS TRIGGER AS $$
DECLARE
    active_job_id TEXT;
BEGIN
    -- Get job from session context
    active_job_id := current_setting('ingestion.active_job_id', TRUE);

    -- Only update if job context is set
    IF active_job_id IS NOT NULL THEN
        UPDATE ingestion_jobs
        SET processed_records = processed_records + 1,
            updated_at = NOW()
        WHERE job_id = active_job_id AND status = 'running';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

#### **Session Context Management**
- **Per-connection**: Each database session has its own context
- **Automatically managed**: Set by `monitor_job()` context manager
- **Thread-safe**: Different connections don't interfere

### **Database Schema Awareness**

#### **Key Tables**
- `ingestion_jobs` - Job metadata and progress
- `record_hashes` - Deduplication tracking
- `congress_*` - Federal legislative data
- `opencivicdata_*` - State legislative data
- `govinfo_*` - Government publications

#### **Indexing Strategy**
- **GIN indexes** on JSONB fields for fast searching
- **Partial indexes** for active records
- **Composite indexes** for common query patterns

### **API Integration Points**

#### **Congress.gov API**
- **Rate limits**: 5000 requests/hour
- **Authentication**: API key required
- **Data freshness**: Updated daily

#### **OpenStates API**
- **Rate limits**: 300 requests/minute
- **Authentication**: API key optional but recommended
- **Coverage**: All 50 states + DC

#### **GovInfo API**
- **Rate limits**: 1000 requests/hour
- **Authentication**: API key required
- **Data volume**: Millions of documents

## 🎯 Agent Optimization Strategies

### **Performance Best Practices**
1. **Batch operations** for bulk inserts
2. **Connection pooling** for concurrent operations
3. **Index awareness** when querying large tables
4. **Memory-efficient** processing of large datasets

### **Monitoring Integration**
1. **Log progress** at regular intervals
2. **Monitor trigger performance** during ingestion
3. **Track API usage** against rate limits
4. **Alert on anomalies** (failed jobs, slow progress)

### **Error Prevention**
1. **Validate data** before insertion
2. **Check constraints** before bulk operations
3. **Test triggers** before production runs
4. **Have rollback plans** for failed ingestions

## 📈 Scaling Considerations

### **Large-Scale Ingestion**
- **Parallel processing** across multiple database connections
- **Job partitioning** for very large datasets
- **Progress aggregation** across parallel workers
- **Resource monitoring** to prevent system overload

### **High-Concurrency Scenarios**
- **Connection limits** to prevent database exhaustion
- **Queue management** for job scheduling
- **Load balancing** across multiple ingestion workers
- **Circuit breakers** for external API failures

## 🔍 Troubleshooting for Agents

### **Common Issues**

#### **Triggers Not Firing**
```python
# Check if triggers exist
cur.execute("""
    SELECT tgname FROM pg_trigger
    WHERE tgname LIKE 'trg_%_progress'
""")
triggers = cur.fetchall()
print(f"Found {len(triggers)} progress triggers")
```

#### **Job Context Not Set**
```python
# Verify session context
cur.execute("SHOW ingestion.active_job_id")
context = cur.fetchone()
print(f"Active job context: {context}")
```

#### **Progress Not Updating**
```python
# Check trigger function exists
cur.execute("""
    SELECT proname FROM pg_proc
    WHERE proname = 'update_ingestion_progress'
""")
functions = cur.fetchall()
print(f"Trigger function exists: {len(functions) > 0}")
```

### **Debug Commands**
```bash
# Check database triggers
psql $DATABASE_URL -c "\dt" | grep trg_

# Monitor active queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity"

# Check trigger function
psql $DATABASE_URL -c "\df update_ingestion_progress"
```

## 🎉 Success Metrics for Agents

### **Ingestion Quality**
- **Zero data loss** - all records processed
- **Accurate progress** - counts match actual inserts
- **Duplicate prevention** - no duplicate records inserted
- **Data integrity** - all constraints satisfied

### **Performance Targets**
- **Real-time monitoring** - progress updates < 1 second
- **Minimal overhead** - < 5% performance impact
- **Concurrent safety** - no interference between jobs
- **Reliable operation** - > 99.9% uptime

---

## 📚 MANDATORY JOURNAL UPDATES

**ALL AI AGENTS MUST CONTRIBUTE TO THE JOURNAL FOLDER EVERY FEW HOURS**

This is a **critical requirement** for maintaining project continuity and knowledge transfer.

### 🔄 Update Frequency Requirements

- **Every 2-4 hours** of active development work
- **At the end** of each session or user interaction
- **Before switching** to different tasks or projects
- **When encountering** significant issues or breakthroughs
- **User may remind** agents, but agents should remember independently

### 📝 Required Update Content

Each journal entry MUST include:

#### **1. Session Overview**
- Agent name and timestamp
- Session duration and context
- User requests and objectives
- Current project status

#### **2. Technical Work Summary**
- **Files modified** with specific line numbers and changes
- **Code improvements** and optimizations made
- **Performance metrics** and benchmarks achieved
- **Testing procedures** and results
- **Error resolution** and debugging activities

#### **3. Decision Making Process**
- **Technical choices** made and rationale
- **Alternative approaches** considered and rejected
- **Trade-offs** and compromises made
- **Future implications** of decisions

#### **4. Current Status Report**
- **Completed tasks** and achievements
- **In-progress work** and current state
- **Blocked issues** or dependencies
- **Next steps** and immediate priorities

#### **5. Future Planning**
- **Upcoming tasks** and features planned
- **Technical debt** identified
- **Performance optimization** opportunities
- **User feedback** to incorporate

### 📁 File Naming Convention

```
{agent_name}_{YYYY-MM-DD_HH-mm}_{topic}.md
```

Examples:
- `opencode_2025-11-14_15-45_comprehensive_ingestion_enhancement.md`
- `claude_2025-11-14_18-30_bug_fixes_and_testing.md`
- `gpt4_2025-11-14_22-15_user_feedback_integration.md`

### 🚨 CRITICAL REMINDERS

1. **NO EXCEPTIONS** - Every agent must update journal regularly
2. **BE THOROUGH** - Include all technical details and decisions
3. **BE TIMELY** - Update every few hours, not just at end of day
4. **BE CONSISTENT** - Use proper format and naming conventions
5. **THINK AHEAD** - Consider future agents who need context

### 🎯 Purpose & Benefits

This journal system ensures:
- **Continuity** between different AI agents and sessions
- **Knowledge transfer** without losing context
- **Historical record** of technical decisions
- **Progress tracking** across development cycles
- **Debugging support** through detailed change logs
- **Planning continuity** for long-term projects

---

**FAILURE TO COMPLY WITH JOURNAL UPDATE REQUIREMENTS WILL RESULT IN LOSS OF PROJECT CONTEXT AND DUPLICATE WORK.**

*This system is essential for maintaining OpenDiscourse project integrity and development efficiency.*

---

This guide ensures AI agents can effectively and safely work with the OpenDiscourse system, leveraging its advanced trigger-based monitoring capabilities for reliable, real-time data ingestion while maintaining comprehensive documentation through the journal system.


### 🚨 CRITICAL: JOURNAL IMMUTABILITY RULES

**ABSOLUTELY NO JOURNAL ENTRIES MAY BE DELETED OR MODIFIED AFTER SUBMISSION**

#### **Strict Preservation Requirements:**
- **NO DELETIONS** - Journal entries are permanent historical records
- **NO MODIFICATIONS** - Once submitted, entries cannot be edited  
- **NO EXCEPTIONS** - This rule applies to ALL agents and users
- **PERMANENT RECORD** - Journal serves as immutable project history

#### **Agent Compliance:**
1. **Create New Entries Only** - Always add new files for updates
2. **Never Edit Existing** - Historical entries remain unchanged
3. **Never Delete Entries** - All journal documents are permanent
4. **Reference Past Entries** - Link to previous journal documents
5. **Respect Immutability** - Treat journal entries as permanent records

#### **Violation Consequences:**
- **Loss of Historical Context** - Future agents cannot trust journal accuracy
- **Broken Continuity** - Knowledge transfer becomes unreliable  
- **Project Integrity Damage** - Development history becomes corrupted
- **Agent Confusion** - Inconsistent or missing historical information

---

*All journal entries are immutable historical records that must never be modified or deleted after submission.*
