from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
import os
import subprocess
from datetime import datetime
from mcp_server.clients.congress_client import CongressClient
from mcp_server.clients.openstates_client import OpenStatesClient
from mcp_server.clients.govinfo_client import GovInfoClient
from mcp_server.utils.monitoring import monitor, deduplicator

app = FastAPI(title="MCP Server Scaffold")

# In-memory stores (replace with secure DB/encrypted store in production)
USER_API_KEYS: Dict[str, Dict[str, str]] = {}
CLIENTS = {
    "congress": CongressClient,
    "openstates": OpenStatesClient,
    "govinfo": GovInfoClient,
}


class TokenRegister(BaseModel):
    site: str
    user_id: str
    api_key: str


class ExecuteRequest(BaseModel):
    user_id: str
    site: str
    function: str
    args: Dict[str, Any] = {}


class IngestionRequest(BaseModel):
    user_id: str
    site: str
    database_url: str
    query_params: Dict[str, Any] = {}
    ingestion_mode: str = "incremental"  # incremental, full, or append


class QueryRequest(BaseModel):
    user_id: str
    database_url: str
    table: str
    where_clause: Optional[str] = None
    limit: int = 100
    order_by: Optional[str] = None


class ExportRequest(BaseModel):
    user_id: str
    database_url: str
    table: str
    format: str = "csv"
    where_clause: Optional[str] = None
    output_path: Optional[str] = None


@app.post("/mcp/register_token")
def register_token(payload: TokenRegister):
    site = payload.site.lower()
    if site not in CLIENTS:
        raise HTTPException(status_code=400, detail=f"Unknown site {site}")
    USER_API_KEYS.setdefault(payload.user_id, {})[site] = payload.api_key
    return {"status": "ok", "site": site, "user_id": payload.user_id}


@app.post("/mcp/execute")
def execute_function(payload: ExecuteRequest):
    user_id = payload.user_id
    site = payload.site.lower()
    function = payload.function
    args = payload.args or {}

    if user_id not in USER_API_KEYS or site not in USER_API_KEYS[user_id]:
        raise HTTPException(status_code=401, detail=f"No API key registered for user {user_id} and site {site}")

    api_key = USER_API_KEYS[user_id][site]

    if site not in CLIENTS:
        raise HTTPException(status_code=400, detail=f"Unknown site {site}")

    client_class = CLIENTS[site]
    client = client_class(api_key=api_key)

    # Check if function exists
    available_functions = {
        "congress": [
            "search_bills", "get_bill", "get_bill_actions", "get_bill_text",
            "list_members", "get_member", "bulk_download_collection",
            "query_congress_bills", "analyze_bill_sponsors_congress",
            "get_congressional_trends", "search_congress_bills_advanced",
            "analyze_member_activity", "compare_congresses", "export_congress_data",
            "query_bills_by_party", "query_bills_by_member_name", "query_bills_by_year_range",
            "query_bills_by_topics", "query_member_voting_record", "query_committee_members",
            "search_bills_by_text_content"
        ],
        "openstates": [
            "search_bills", "get_bill", "search_people", "get_person",
            "search_events", "get_event", "get_openapi_schema",
            "query_bills", "export_bills", "analyze_bill_sponsors",
            "find_related_bills", "get_legislative_trends", "search_bills_advanced",
            "get_bill_statistics", "export_filtered_data", "compare_legislatures",
            "generate_bill_report", "query_bills_by_party", "query_bills_by_person_name",
            "query_bills_by_year_range", "query_bills_by_topics", "query_person_voting_record",
            "query_committees", "search_bills_by_text_content"
        ],
        "govinfo": [
            "list_collections", "bulk_download", "fetch_bulk_file", "ingest_xml_to_df",
            "query_govinfo_documents", "analyze_document_collections",
            "get_document_trends", "search_documents_advanced",
            "analyze_document_metadata", "compare_collections", "export_govinfo_data",
            "query_documents_by_year_range", "query_documents_by_topics",
            "query_documents_by_type", "search_documents_by_text_content",
            "query_recent_documents", "analyze_document_types", "query_documents_by_metadata_field"
        ],
    }

    if function not in available_functions.get(site, []):
        raise HTTPException(status_code=400, detail=f"Unknown function {function} for site {site}")

    try:
        method = getattr(client, function)
        result = method(**args)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Function execution failed: {str(e)}")


@app.post("/mcp/ingest_data")
def ingest_data(payload: IngestionRequest):
    user_id = payload.user_id
    site = payload.site.lower()
    database_url = payload.database_url
    query_params = payload.query_params or {}
    ingestion_mode = payload.ingestion_mode

    if user_id not in USER_API_KEYS or site not in USER_API_KEYS[user_id]:
        raise HTTPException(status_code=401, detail=f"No API key registered for user {user_id} and site {site}")

    api_key = USER_API_KEYS[user_id][site]

    # Set environment variables for the ingestion script
    env = os.environ.copy()
    env[f"{site.upper()}_API_KEY"] = api_key
    env["DATABASE_URL"] = database_url

    # Map site to script
    script_map = {
        "openstates": "mcp_server/scripts/openstates_ingest.py",
        "congress": "mcp_server/scripts/congress_ingest.py",
        "govinfo": "mcp_server/scripts/govinfo_ingest.py"
    }

    if site not in script_map:
        raise HTTPException(status_code=400, detail=f"No ingestion script for site {site}")

    script_path = script_map[site]

    # Define allowlists for command-line argument keys per site
    allowed_query_keys = {
        "openstates": {"session", "state", "district", "chamber"},   # Example keys; update as appropriate
        "congress": {"chamber", "session", "member"},                # Example keys; update as appropriate
        "govinfo": {"collection", "doc", "year"}                    # Example keys; update as appropriate
    }
    allowed_keys = allowed_query_keys.get(site, set())

    # Build command arguments
    cmd = ["python", script_path]

    # Add query parameters as command line args, validating keys
    for key, value in query_params.items():
        # Only process allowed/safe keys
        if key not in allowed_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid query parameter: {key!r} for site {site}"
            )
        # Additional key format validation: alphanumeric, underscores, dashes only
        if not isinstance(key, str) or not key.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=400,
                detail=f"Unsafe query parameter key: {key!r}"
            )
        if isinstance(value, bool):
            if value:
                cmd.append(f"--{key}")
        else:
            cmd.append(f"--{key}")
            cmd.append(str(value))

    try:
        # Run the ingestion script
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, cwd="/home/cbwinslow/opendiscourse")
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Ingestion failed: {result.stderr}")

        return {
            "status": "success",
            "site": site,
            "ingestion_mode": ingestion_mode,
            "message": f"Data ingestion completed for {site}",
            "output": result.stdout
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion execution failed: {str(e)}")


@app.post("/mcp/query_data")
def query_data(payload: QueryRequest):
    """Query data from database tables"""
    import psycopg2
    import pandas as pd

    try:
        conn = psycopg2.connect(payload.database_url)
        cur = conn.cursor()

        query = f"SELECT * FROM {payload.table}"
        if payload.where_clause:
            query += f" WHERE {payload.where_clause}"
        if payload.order_by:
            query += f" ORDER BY {payload.order_by}"
        query += f" LIMIT {payload.limit}"

        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        cur.close()
        conn.close()

        df = pd.DataFrame(rows, columns=columns)
        return {
            "status": "success",
            "table": payload.table,
            "count": len(df),
            "columns": columns,
            "data": df.to_dict('records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/mcp/export_data")
def export_data(payload: ExportRequest):
    """Export data from database to file"""
    import psycopg2
    import pandas as pd
    from mcp_server.utils.ingest import save_dataframe

    try:
        conn = psycopg2.connect(payload.database_url)
        cur = conn.cursor()

        query = f"SELECT * FROM {payload.table}"
        if payload.where_clause:
            query += f" WHERE {payload.where_clause}"

        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

        cur.close()
        conn.close()

        df = pd.DataFrame(rows, columns=columns)

        if not payload.output_path:
            payload.output_path = f"{payload.table}_export.{payload.format}"

        save_dataframe(df, payload.output_path, payload.format)

        return {
            "status": "success",
            "table": payload.table,
            "format": payload.format,
            "file": payload.output_path,
            "records": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/mcp/functions")
def list_functions():
    # For simplicity, enumerate a small set of functions available per client
    return {
        "congress": [
            "search_bills", "get_bill", "get_bill_actions", "get_bill_text",
            "list_members", "get_member", "bulk_download_collection",
            "ingest_bills", "ingest_members", "query_bills", "export_bills"
        ],
        "openstates": [
            "search_bills", "get_bill", "search_people", "get_person",
            "search_events", "get_event", "get_openapi_schema",
            "ingest_bills", "ingest_people", "ingest_events", "query_bills", "export_data"
        ],
        "govinfo": [
            "list_collections", "bulk_download", "fetch_bulk_file", "ingest_xml_to_df",
            "ingest_bulk_data", "query_documents", "export_documents"
        ],
    }


@app.get("/mcp/data_model")
def get_data_model():
    # Return database table schemas for data model exposure
    schemas = {
        "openstates_bills": {
            "id": "text (primary key)",
            "session": "text",
            "jurisdiction": "text",
            "identifier": "text",
            "title": "text",
            "classification": "text[]",
            "subjects": "text[]",
            "created_at": "timestamptz",
            "updated_at": "timestamptz",
            "first_action_date": "date",
            "latest_action_date": "date",
            "latest_action_description": "text",
            "openstates_url": "text",
            "raw": "jsonb"
        },
        "openstates_people": {
            "id": "text (primary key)",
            "name": "text",
            "party": "text",
            "jurisdiction": "text",
            "given_name": "text",
            "family_name": "text",
            "image": "text",
            "email": "text",
            "gender": "text",
            "birth_date": "date",
            "death_date": "date",
            "extras": "jsonb",
            "raw": "jsonb"
        },
        "openstates_events": {
            "id": "text (primary key)",
            "name": "text",
            "jurisdiction": "text",
            "description": "text",
            "classification": "text",
            "start_date": "timestamptz",
            "end_date": "timestamptz",
            "all_day": "boolean",
            "status": "text",
            "location": "jsonb",
            "raw": "jsonb"
        },
        "congress_bills": {
            "id": "text (primary key)",
            "congress": "smallint",
            "bill_type": "text",
            "bill_number": "integer",
            "title": "text",
            "latest_action_date": "date",
            "latest_action_description": "text",
            "subjects": "text[]",
            "sponsors": "jsonb",
            "raw": "jsonb"
        },
        "congress_members": {
            "bioguide_id": "text (primary key)",
            "first_name": "text",
            "last_name": "text",
            "party": "text",
            "state": "text",
            "district": "text",
            "raw": "jsonb"
        },
        "congress_votes": {
            "id": "text (primary key)",
            "congress": "smallint",
            "session": "smallint",
            "vote_number": "text",
            "date": "timestamptz",
            "result": "text",
            "counts": "jsonb",
            "raw": "jsonb"
        },
        "govinfo_documents": {
            "id": "text (primary key)",
            "collection": "text",
            "date": "date",
            "title": "text",
            "url": "text",
            "metadata": "jsonb",
            "raw": "jsonb"
        }
    }
    return schemas


# Monitoring endpoints
@app.get("/mcp/ingestion/jobs")
def get_ingestion_jobs(status: Optional[str] = None):
    """Get all ingestion jobs, optionally filtered by status."""
    return monitor.get_all_jobs(status)


@app.get("/mcp/ingestion/jobs/{job_id}")
def get_ingestion_job(job_id: str):
    """Get a specific ingestion job by ID."""
    job = monitor.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@app.post("/mcp/ingestion/start")
def start_ingestion_job(source: str, collection: str, **metadata):
    """Start a new ingestion job."""
    try:
        job_id = monitor.create_job(source, collection, **metadata)
        return {"job_id": job_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@app.delete("/mcp/ingestion/cleanup")
def cleanup_old_data(days: int = 30):
    """Clean up old ingestion data and hashes."""
    try:
        deduplicator.cleanup_old_hashes(days)
        return {"status": "success", "message": f"Cleaned up data older than {days} days"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@app.get("/mcp/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
