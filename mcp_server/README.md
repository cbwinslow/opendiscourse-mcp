# MCP Server for Legislative Data APIs

A Model Context Protocol (MCP) server that reverse-engineers APIs from OpenStates, Congress.gov, and GovInfo to enable LLMs to query, ingest, manipulate, and transform legislative data.

## Features

- **API Clients**: Site-specific clients for OpenStates v3, Congress.gov, and GovInfo with comprehensive endpoint coverage
- **Data Ingestion**: Utilities to convert API responses/XML into DataFrames, transform timeframes, and export formats
- **Database Integration**: Optimized PostgreSQL schemas with efficient data types
- **MCP Server**: FastAPI-based server exposing functions to LLMs with per-user API key management
- **Bulk Data Handling**: Support for bulk downloads and ingestion of large datasets

## Quick Start

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Database Setup
Add your Postgres connection string to `mcp_server/.env`:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/opendiscourse
```

Run migrations:
```bash
./mcp_server/scripts/init_db.sh
```

Or manually:
```bash
python mcp_server/db_init.py --all
```

### Run Server
```bash
uvicorn mcp_server.main:app --reload --port 8080
```

## API Endpoints

### Token Management
- `POST /mcp/register_token`: Register API keys per user/site
  ```json
  {
    "site": "congress",
    "user_id": "alice",
    "api_key": "your_api_key_here"
  }
  ```

### Function Discovery
- `GET /mcp/functions`: List available functions per site

### Function Execution
- `POST /mcp/execute`: Execute registered functions
  ```json
  {
    "user_id": "alice",
    "site": "openstates",
    "function": "search_bills",
    "args": {"jurisdiction": "nc", "q": "education"}
  }
  ```

### Data Model Exposure
- `GET /mcp/data_model`: Get database table schemas and field types

## Available Functions

### Congress.gov
- `search_bills`: Search bills by congress, type, etc.
- `get_bill`: Get detailed bill information
- `get_bill_actions`: Retrieve bill action history
- `get_bill_text`: Get bill text content
- `list_members`: List congressional members
- `get_member`: Get member details

### OpenStates
- `search_bills`: Search bills by jurisdiction, query
- `get_bill`: Get bill details
- `search_people`: Search legislators
- `get_person`: Get person details
- `search_events`: Search legislative events
- `get_event`: Get event details

### GovInfo
- `list_collections`: List available collections
- `bulk_download`: Download bulk data files
- `fetch_bulk_file`: Download individual files
- `ingest_xml_to_df`: Parse XML to DataFrame

## Database Schemas

Optimized PostgreSQL tables with minimal storage:

- **openstates_bills**: Bills with classifications, subjects, dates
- **openstates_people**: Legislator information
- **openstates_events**: Legislative events
- **congress_bills**: Congress bills with sponsors, actions
- **congress_members**: Member details
- **congress_votes**: Vote records
- **govinfo_documents**: Bulk document metadata

## Usage Examples

### Register API Keys
```bash
curl -X POST http://localhost:8080/mcp/register_token \
  -H "Content-Type: application/json" \
  -d '{"site": "congress", "user_id": "alice", "api_key": "your_key"}'
```

### Search Bills
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "openstates",
    "function": "search_bills",
    "args": {"jurisdiction": "nc"}
  }'
```

### Run Ingestion
```bash
export DATABASE_URL='postgresql://...'
python mcp_server/scripts/openstates_ingest.py --jurisdiction nc
```

## Development

### Testing
```bash
pytest tests/
```

### Adding New Clients
1. Create client class inheriting from `BaseClient`
2. Add to `CLIENTS` dict in `main.py`
3. Update function list in `/mcp/functions`

### Production Notes
- Replace in-memory token store with encrypted database
- Add rate limiting and authentication
- Use connection pooling for database access
- Implement proper logging and monitoring
