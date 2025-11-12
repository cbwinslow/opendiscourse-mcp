# OpenDiscourse System Rules and Guidelines

This document outlines the mandatory rules and guidelines that all AI agents and human operators must follow when working with the OpenDiscourse legislative data ingestion system.

## 🚨 **MANDATORY RULES**

### **Rule 1: Database Trigger System Integrity**
- **NEVER** manually update `processed_records` in the `ingestion_jobs` table
- **ALWAYS** let database triggers handle progress tracking automatically
- **NEVER** bypass or disable database triggers for any reason
- **ALWAYS** verify trigger functionality before starting ingestion jobs

**Violation Consequence**: Data corruption, inaccurate progress reporting, system breakdown

### **Rule 2: Job Context Management**
- **ALWAYS** use the `monitor.monitor_job()` context manager for ingestion operations
- **NEVER** set or clear job context manually (use the provided functions)
- **ALWAYS** ensure job context is cleared after operations (automatic with context manager)
- **NEVER** run ingestion without an active job context

**Violation Consequence**: Progress tracking failures, cross-contamination between jobs

### **Rule 3: Database Connection Management**
- **ALWAYS** use separate database connections for concurrent ingestion jobs
- **NEVER** share database connections between different ingestion jobs
- **ALWAYS** close database connections after use
- **NEVER** hold database connections open indefinitely

**Violation Consequence**: Job interference, connection exhaustion, deadlocks

### **Rule 4: Transaction Boundaries**
- **ALWAYS** respect database transaction boundaries
- **NEVER** perform partial commits during ingestion
- **ALWAYS** ensure atomic operations for related data
- **NEVER** leave transactions in an inconsistent state

**Violation Consequence**: Data integrity violations, partial ingestion states

### **Rule 5: API Rate Limit Compliance**
- **ALWAYS** respect API rate limits for all external services
- **NEVER** exceed configured rate limits
- **ALWAYS** implement exponential backoff for rate limit errors
- **NEVER** implement aggressive retry logic that could trigger bans

**Violation Consequence**: API access suspension, service disruption

### **Rule 6: Data Validation Requirements**
- **ALWAYS** validate data before database insertion
- **NEVER** insert malformed or invalid data
- **ALWAYS** check for required fields and data types
- **NEVER** assume external API data is clean or complete

**Violation Consequence**: Database constraint violations, data corruption

### **Rule 7: Error Handling Protocols**
- **ALWAYS** implement comprehensive error handling
- **NEVER** allow unhandled exceptions to crash ingestion processes
- **ALWAYS** log detailed error information for debugging
- **NEVER** expose sensitive information in error messages

**Violation Consequence**: Silent failures, debugging difficulties, security risks

### **Rule 8: Resource Management**
- **ALWAYS** monitor memory usage during large ingestions
- **NEVER** allow memory leaks or unbounded memory growth
- **ALWAYS** implement resource limits and circuit breakers
- **NEVER** exhaust system resources

**Violation Consequence**: System instability, performance degradation

### **Rule 9: Concurrent Operation Safety**
- **ALWAYS** design for concurrent operation from the start
- **NEVER** assume single-threaded execution
- **ALWAYS** test concurrent scenarios thoroughly
- **NEVER** implement operations that could cause race conditions

**Violation Consequence**: Data corruption, inconsistent states, deadlocks

### **Rule 10: Monitoring and Alerting**
- **ALWAYS** implement health checks before operations
- **NEVER** start ingestion without verifying system health
- **ALWAYS** monitor progress and alert on anomalies
- **NEVER** allow failed jobs to go unnoticed

**Violation Consequence**: Unmonitored failures, undetected issues

## 📋 **OPERATIONAL GUIDELINES**

### **Ingestion Workflow Standards**

#### **Pre-Ingestion Checklist**
- [ ] Database connectivity verified
- [ ] All required API keys configured
- [ ] Database triggers installed and functional
- [ ] Sufficient disk space available
- [ ] System resources (CPU, memory) adequate
- [ ] No conflicting ingestion jobs running
- [ ] Backup strategy in place

#### **During Ingestion**
- [ ] Job context properly set
- [ ] Progress monitoring active
- [ ] Error handling implemented
- [ ] Resource usage within limits
- [ ] API rate limits respected
- [ ] Data validation active

#### **Post-Ingestion**
- [ ] Job status correctly set (completed/failed)
- [ ] Job context cleared
- [ ] Database connections closed
- [ ] Resources cleaned up
- [ ] Results logged and reported
- [ ] Any errors documented

### **Code Quality Standards**

#### **Error Handling**
```python
# ✅ CORRECT
try:
    with monitor.monitor_job(job_id):
        for item in data_source:
            process_item(item)
except Exception as e:
    logger.error(f"Ingestion failed: {e}")
    # Context manager automatically handles cleanup
    raise

# ❌ INCORRECT
try:
    monitor._set_job_context(job_id)  # Manual context management
    for item in data_source:
        process_item(item)
except Exception as e:
    monitor._clear_job_context()  # Manual cleanup
    raise
```

#### **Database Operations**
```python
# ✅ CORRECT
from mcp_server.db import get_sqlalchemy_engine

engine = get_sqlalchemy_engine()
with engine.connect() as conn:
    # Use connection within context
    pass
# Connection automatically closed

# ❌ INCORRECT
conn = psycopg2.connect(DATABASE_URL)
# Connection may leak if not properly closed
```

#### **Progress Monitoring**
```python
# ✅ CORRECT
# Let triggers handle progress automatically
with monitor.monitor_job(job_id):
    for bill in bills:
        insert_bill(bill)  # Progress updates automatically

# ❌ INCORRECT
# Manual progress updates (forbidden)
with monitor.monitor_job(job_id):
    for bill in bills:
        insert_bill(bill)
        monitor.update_progress(job_id, count)  # NEVER DO THIS
```

### **Testing Requirements**

#### **Unit Tests**
- [ ] All database operations tested
- [ ] Trigger functionality verified
- [ ] Error conditions handled
- [ ] Concurrent operations tested
- [ ] Resource cleanup verified

#### **Integration Tests**
- [ ] Full ingestion workflows tested
- [ ] API integrations verified
- [ ] Database constraints validated
- [ ] Performance benchmarks met
- [ ] Failure recovery tested

#### **System Tests**
- [ ] End-to-end ingestion tested
- [ ] Monitoring system validated
- [ ] Alerting mechanisms tested
- [ ] Backup/restore procedures verified

## 🚫 **PROHIBITED ACTIONS**

### **Database Operations**
- Direct manipulation of `ingestion_jobs.processed_records`
- Disabling or dropping database triggers
- Manual job context management
- Cross-session job interference
- Uncommitted database transactions

### **System Operations**
- Bypassing rate limiters
- Ignoring error conditions
- Resource exhaustion
- Concurrent access without proper isolation
- Unmonitored background operations

### **Data Operations**
- Inserting invalid data
- Bypassing validation checks
- Ignoring duplicate detection
- Partial data ingestion
- Data corruption risks

## ⚠️ **WARNING SIGNS**

### **System Health Indicators**
- Trigger functions not responding
- Job contexts not clearing
- Progress not updating in real-time
- Database connection timeouts
- Memory usage spikes

### **Data Quality Indicators**
- Unexpected duplicate records
- Constraint violation errors
- Inconsistent progress counts
- Missing required data fields
- API timeout errors

### **Performance Indicators**
- Slow progress updates
- High CPU/memory usage
- Database lock contention
- API rate limit hits
- Connection pool exhaustion

## 🛠️ **RECOVERY PROCEDURES**

### **Failed Ingestion Recovery**
1. Check job status in database
2. Verify job context is cleared
3. Assess data consistency
4. Clean up partial data if needed
5. Document failure reasons
6. Implement fixes before retry

### **Trigger System Recovery**
1. Verify trigger functions exist
2. Check trigger installation on tables
3. Test trigger functionality
4. Reinstall triggers if corrupted
5. Validate with test ingestion

### **Database Connection Recovery**
1. Check connection pool status
2. Verify database availability
3. Clear stuck connections
4. Restart connection pools if needed
5. Test connectivity before resuming

## 📊 **COMPLIANCE MONITORING**

### **Automated Checks**
- Database trigger health monitoring
- Job context validation
- Progress update verification
- Resource usage monitoring
- API rate limit compliance

### **Manual Audits**
- Code review for rule compliance
- Database state validation
- Log analysis for violations
- Performance metric review
- Security assessment

### **Reporting Requirements**
- Weekly compliance reports
- Incident response documentation
- Performance metric tracking
- Security audit results
- System health summaries

## 🎯 **SUCCESS CRITERIA**

### **Operational Excellence**
- 100% rule compliance
- Zero data corruption incidents
- < 0.1% ingestion failure rate
- Real-time progress monitoring
- Automatic error recovery

### **Performance Standards**
- < 5% monitoring overhead
- Real-time progress updates
- Concurrent job isolation
- Resource-efficient operations
- Scalable architecture

### **Quality Assurance**
- Comprehensive test coverage
- Automated validation
- Continuous monitoring
- Proactive issue detection
- Rapid incident response

---

**VIOLATION OF THESE RULES MAY RESULT IN:**
- Immediate system shutdown
- Data integrity compromise
- Service disruption
- Security incidents
- Legal compliance issues

**ALL OPERATORS AND AI AGENTS MUST ACKNOWLEDGE AND COMPLY WITH THESE RULES.**
