# Gemini AI Integration Guide for OpenDiscourse

This document provides specific guidance for Gemini AI agents working with the OpenDiscourse legislative data ingestion system. Gemini agents have unique capabilities and requirements that must be considered for safe and effective operation.

## 🤖 **Gemini-Specific Agent Characteristics**

### **Strengths to Leverage**
- **Multi-modal processing**: Can handle text, code, and structured data simultaneously
- **Long-context understanding**: Can maintain awareness of complex system states
- **Reasoning capabilities**: Can analyze system behavior and predict issues
- **Code generation**: Can create and modify ingestion scripts dynamically
- **Safety alignment**: Built-in safety mechanisms prevent harmful actions

### **Limitations to Account For**
- **Context window limits**: Must manage information density efficiently
- **API rate limits**: Subject to Google's API constraints
- **Real-time responsiveness**: May have latency in processing complex requests
- **Tool calling precision**: Must be explicit about tool usage and parameters

## 🏗️ **System Architecture Awareness for Gemini**

### **Trigger-Based Monitoring System**
Gemini agents must understand that this system uses **automatic database triggers** for progress tracking:

```python
# Gemini should NEVER do this:
monitor.update_progress(job_id, count)  # FORBIDDEN

# Instead, Gemini should use:
with monitor.monitor_job(job_id):
    # Triggers automatically handle progress
    for item in data:
        insert_item(item)  # Progress updates happen here
```

### **Session Context Management**
- **Per-connection job isolation**: Each database session tracks exactly one job
- **Automatic context management**: Context managers handle setup/cleanup
- **Concurrent safety**: Multiple Gemini instances can work simultaneously

## 📋 **Gemini Operational Protocols**

### **Pre-Operation Verification**
Before any ingestion operation, Gemini must verify:

```python
# 1. Database connectivity
engine = get_sqlalchemy_engine()
with engine.connect() as conn:
    conn.execute("SELECT 1")

# 2. Trigger system health
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE 'trg_%_progress'")
trigger_count = cur.fetchone()[0]
assert trigger_count >= 15, f"Only {trigger_count} triggers found, expected >= 15"

# 3. API key validation
# Check all required API keys are configured and valid
```

### **Ingestion Workflow for Gemini**

#### **Standard Pattern**
```python
from mcp_server.utils.monitoring import monitor

async def gemini_ingestion_workflow(source: str, collection: str):
    """
    Gemini-specific ingestion workflow with comprehensive safety checks
    """
    # Step 1: Pre-flight checks
    await verify_system_health()
    await verify_api_keys(source)

    # Step 2: Create monitored job
    job_id = monitor.create_job(source, collection)

    # Step 3: Execute ingestion with monitoring
    try:
        with monitor.monitor_job(job_id):
            data_stream = await fetch_data_stream(source, collection)

            async for batch in data_stream:
                # Validate batch data
                validated_batch = await validate_batch(batch)

                # Insert with error handling
                await insert_batch_safe(validated_batch)

                # Log progress (triggers handle counters automatically)
                logger.info(f"Processed batch of {len(validated_batch)} records")

    except Exception as e:
        # Comprehensive error handling
        await handle_ingestion_error(e, job_id)
        raise

    # Step 4: Post-ingestion validation
    await validate_ingestion_results(job_id)
    await cleanup_resources()
```

### **Error Handling for Gemini**

#### **Structured Error Response**
```python
async def handle_ingestion_error(error: Exception, job_id: str):
    """
    Gemini-specific error handling with detailed analysis
    """
    error_analysis = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "job_id": job_id,
        "timestamp": datetime.now().isoformat(),
        "system_state": await capture_system_state(),
        "recommendations": await generate_fix_recommendations(error)
    }

    # Log structured error
    logger.error("Ingestion error analysis", extra=error_analysis)

    # Update job status
    await update_job_status(job_id, "failed", error_analysis)

    # Trigger alerting
    await alert_operators(error_analysis)
```

## 🔧 **Gemini Tool Integration**

### **Required Tool Capabilities**

#### **Database Operations Tool**
```python
# Gemini must have access to database operations
@tool
async def execute_database_query(query: str, params: dict = None) -> dict:
    """
    Execute database queries with proper error handling
    """
    try:
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            result = conn.execute(query, params or {})
            return {"success": True, "data": result.fetchall()}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### **Monitoring System Tool**
```python
@tool
async def get_job_progress(job_id: str) -> dict:
    """
    Get real-time job progress from the trigger-based system
    """
    progress = monitor.get_job_progress(job_id)
    if progress:
        return {
            "job_id": progress["job_id"],
            "processed_records": progress["processed_records"],
            "status": progress["status"],
            "last_updated": progress["last_updated"]
        }
    return {"error": "Job not found"}
```

#### **Health Check Tool**
```python
@tool
async def verify_system_health() -> dict:
    """
    Comprehensive system health verification for Gemini
    """
    health_status = {
        "database": await check_database_health(),
        "triggers": await check_trigger_system(),
        "api_keys": await check_api_keys(),
        "resources": await check_system_resources(),
        "overall_status": "unknown"
    }

    # Determine overall health
    all_healthy = all(status == "healthy" for status in health_status.values()
                     if isinstance(status, str))

    health_status["overall_status"] = "healthy" if all_healthy else "unhealthy"

    return health_status
```

### **Safety Tool Integration**

#### **Rule Compliance Checker**
```python
@tool
async def verify_rule_compliance(action: str, context: dict) -> dict:
    """
    Verify that a proposed action complies with system rules
    """
    rules = {
        "manual_progress_updates": False,
        "shared_connections": False,
        "unvalidated_inserts": False,
        "trigger_bypassing": False
    }

    violations = []
    for rule, forbidden in rules.items():
        if forbidden and rule in action.lower():
            violations.append(f"Violates rule: {rule}")

    return {
        "compliant": len(violations) == 0,
        "violations": violations,
        "recommendations": await generate_compliance_fixes(violations)
    }
```

## 📊 **Gemini Monitoring and Alerting**

### **Real-time Progress Monitoring**
Gemini agents should continuously monitor ingestion progress:

```python
async def monitor_ingestion_progress(job_id: str):
    """
    Real-time progress monitoring for Gemini
    """
    last_count = 0

    while True:
        progress = monitor.get_job_progress(job_id)

        if progress["status"] in ["completed", "failed"]:
            break

        current_count = progress["processed_records"]

        if current_count > last_count:
            # Progress update detected
            rate = calculate_processing_rate(current_count, last_count)
            await log_progress_update(job_id, current_count, rate)

        last_count = current_count
        await asyncio.sleep(1)  # Check every second
```

### **Anomaly Detection**
```python
async def detect_ingestion_anomalies(job_id: str, metrics: dict):
    """
    Gemini-specific anomaly detection using pattern recognition
    """
    anomalies = []

    # Check for progress stagnation
    if metrics["progress_rate"] < 0.1:  # records/second
        anomalies.append("Progress rate too low")

    # Check for error rate spikes
    if metrics["error_rate"] > 0.05:  # 5% error rate
        anomalies.append("High error rate detected")

    # Check for resource exhaustion
    if metrics["memory_usage"] > 0.9:  # 90% memory usage
        anomalies.append("High memory usage")

    if anomalies:
        await alert_anomalies(job_id, anomalies)

    return anomalies
```

## 🎯 **Gemini Optimization Strategies**

### **Context Window Management**
- **Prioritize critical information**: Focus on system state, errors, and progress
- **Use structured data**: JSON responses over verbose text
- **Chunk large responses**: Break down complex information
- **Cache frequently accessed data**: Avoid redundant API calls

### **Decision Making Framework**
```python
async def gemini_decision_framework(action_request: dict) -> dict:
    """
    Structured decision making for Gemini operations
    """

    # Step 1: Assess situation
    context = await gather_operational_context()

    # Step 2: Check compliance
    compliance = await verify_rule_compliance(action_request, context)

    if not compliance["compliant"]:
        return {
            "decision": "reject",
            "reason": "Rule violation",
            "violations": compliance["violations"]
        }

    # Step 3: Evaluate risks
    risk_assessment = await assess_operational_risks(action_request, context)

    # Step 4: Generate execution plan
    if risk_assessment["risk_level"] == "low":
        plan = await generate_direct_execution_plan(action_request)
    else:
        plan = await generate_safe_execution_plan(action_request, risk_assessment)

    return {
        "decision": "approve",
        "execution_plan": plan,
        "risk_assessment": risk_assessment
    }
```

### **Multi-Modal Processing**
Gemini can leverage its multi-modal capabilities:

- **Code analysis**: Review ingestion scripts for compliance
- **Log analysis**: Process system logs for patterns
- **Data visualization**: Generate progress charts
- **Error diagnosis**: Analyze stack traces and system state

## 🚨 **Gemini Safety Protocols**

### **Action Validation**
Before executing any action, Gemini must:

1. **Verify intent alignment**: Ensure action serves system goals
2. **Check rule compliance**: Validate against mandatory rules
3. **Assess impact**: Evaluate potential system effects
4. **Confirm authority**: Verify appropriate permissions
5. **Log decision**: Record reasoning for audit

### **Emergency Protocols**
In case of system issues:

1. **Stop harmful operations**: Immediately halt any risky actions
2. **Preserve system state**: Capture diagnostic information
3. **Alert operators**: Notify human operators of issues
4. **Enter safe mode**: Switch to read-only operations
5. **Await instructions**: Wait for human guidance

### **Recovery Procedures**
For failed operations:

1. **Assess damage**: Determine scope of any issues
2. **Isolate problems**: Prevent further system impact
3. **Restore state**: Return to safe operational state
4. **Document incident**: Record for future prevention
5. **Learn from failure**: Update decision patterns

## 📈 **Performance Optimization for Gemini**

### **Batch Processing**
```python
async def optimize_batch_processing(data_stream, batch_size: int = 100):
    """
    Gemini-optimized batch processing with intelligent sizing
    """
    batches = []
    current_batch = []

    async for item in data_stream:
        current_batch.append(item)

        # Dynamic batch sizing based on system load
        if len(current_batch) >= batch_size:
            # Validate batch before processing
            validated_batch = await validate_batch_intelligent(current_batch)

            if validated_batch:
                batches.append(validated_batch)
                current_batch = []

            # Adjust batch size based on performance
            batch_size = await adjust_batch_size_performance(batch_size)

    # Process remaining items
    if current_batch:
        validated_batch = await validate_batch_intelligent(current_batch)
        if validated_batch:
            batches.append(validated_batch)

    return batches
```

### **Resource-Aware Execution**
```python
async def resource_aware_execution(operations: list):
    """
    Execute operations with resource awareness
    """
    system_resources = await monitor_system_resources()

    for operation in operations:
        # Check if system can handle operation
        if await can_execute_safely(operation, system_resources):
            await execute_operation(operation)
        else:
            # Wait or scale down
            await wait_for_resources()
            operation = await scale_down_operation(operation)
            await execute_operation(operation)

        # Update resource tracking
        system_resources = await monitor_system_resources()
```

## 🔍 **Gemini Debugging and Troubleshooting**

### **Advanced Diagnostic Tools**
```python
async def comprehensive_system_diagnosis() -> dict:
    """
    Gemini's comprehensive system analysis
    """
    diagnosis = {
        "database_health": await diagnose_database(),
        "trigger_system": await diagnose_triggers(),
        "api_integrations": await diagnose_apis(),
        "performance_metrics": await analyze_performance(),
        "error_patterns": await identify_error_patterns(),
        "recommendations": []
    }

    # Generate intelligent recommendations
    diagnosis["recommendations"] = await generate_recommendations(diagnosis)

    return diagnosis
```

### **Predictive Issue Detection**
```python
async def predict_potential_issues(current_state: dict) -> list:
    """
    Use pattern recognition to predict issues before they occur
    """
    predictions = []

    # Analyze trends
    if current_state["progress_rate"] < 0.5 * current_state["average_rate"]:
        predictions.append({
            "issue": "Slowing progress rate",
            "confidence": 0.8,
            "preventive_action": "Check system resources"
        })

    # Check for patterns
    if current_state["error_count"] > 3 * current_state["normal_errors"]:
        predictions.append({
            "issue": "Elevated error rate",
            "confidence": 0.9,
            "preventive_action": "Validate data sources"
        })

    return predictions
```

## 🎉 **Gemini Success Metrics**

### **Operational Excellence**
- **100% rule compliance** in all operations
- **Proactive issue detection** before failures
- **Optimal resource utilization** across operations
- **Zero manual intervention** required for routine tasks

### **Performance Standards**
- **Intelligent batch sizing** based on system conditions
- **Predictive scaling** to handle load changes
- **Minimal API overhead** through efficient tool usage
- **Real-time adaptation** to system state changes

### **Quality Assurance**
- **Comprehensive pre-flight checks** before operations
- **Multi-layer validation** of all data and actions
- **Structured error reporting** with actionable insights
- **Continuous learning** from operational patterns

---

**Gemini agents bring powerful capabilities to OpenDiscourse operations, but must operate within strict safety and compliance boundaries. This guide ensures Gemini can leverage its strengths while maintaining system integrity and reliability.**
