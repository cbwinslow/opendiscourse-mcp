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
- `query_congress_bills`: Query Congress bills from database
- `analyze_bill_sponsors_congress`: Analyze Congress bill sponsorship patterns
- `get_congressional_trends`: Analyze congressional activity by congress number
- `search_congress_bills_advanced`: Advanced search for Congress bills
- `analyze_member_activity`: Analyze legislative activity for members
- `compare_congresses`: Compare activity between different congresses
- `export_congress_data`: Export Congress data with filtering

### OpenStates
- `search_bills`: Search bills by jurisdiction, query
- `get_bill`: Get bill details
- `search_people`: Search legislators
- `get_person`: Get person details
- `search_events`: Search legislative events
- `get_event`: Get event details
- `analyze_bill_sponsors`: Analyze bill sponsorship patterns and statistics
- `find_related_bills`: Find bills related by sponsors, subjects, or keywords
- `get_legislative_trends`: Analyze legislative activity trends over time
- `search_bills_advanced`: Advanced bill search with multiple criteria
- `get_bill_statistics`: Get comprehensive statistics on bill data
- `export_filtered_data`: Export data with advanced filtering options
- `compare_legislatures`: Compare legislative activity between jurisdictions
- `generate_bill_report`: Generate detailed reports for specific bills

### GovInfo
- `list_collections`: List available collections
- `bulk_download`: Download bulk data files
- `fetch_bulk_file`: Download individual files
- `ingest_xml_to_df`: Parse XML to DataFrame
- `query_govinfo_documents`: Query GovInfo documents from database
- `analyze_document_collections`: Analyze document distribution across collections
- `get_document_trends`: Analyze document publication trends over time
- `search_documents_advanced`: Advanced search for GovInfo documents
- `analyze_document_metadata`: Analyze metadata patterns in documents
- `compare_collections`: Compare document characteristics between collections
- `export_govinfo_data`: Export GovInfo documents with filtering

## Database Schemas

Optimized PostgreSQL tables with minimal storage:

- **openstates_bills**: Bills with classifications, subjects, dates
- **openstates_people**: Legislator information
- **openstates_events**: Legislative events
- **congress_bills**: Congress bills with sponsors, actions
- **congress_members**: Member details
- **congress_votes**: Vote records
- **govinfo_documents**: Bulk document metadata

## Function Reference

This section provides detailed documentation for all available functions, including parameters, return values, and usage examples.

### OpenStates Functions

#### `analyze_bill_sponsors(jurisdiction=None, limit=50)`
Analyzes bill sponsorship patterns and statistics from OpenStates data.

**Parameters:**
- `jurisdiction` (str, optional): Filter by jurisdiction (e.g., "ca", "tx")
- `limit` (int): Maximum number of bills to analyze (default: 50)

**Returns:** Dict with sponsorship analysis including total bills, unique sponsors, top sponsors, and sample data.

**Example:**
```python
result = client.analyze_bill_sponsors(jurisdiction="ca", limit=100)
print(f"Found {result['unique_sponsors']} sponsors across {result['total_bills']} bills")
```

#### `find_related_bills(bill_id, jurisdiction=None)`
Finds bills related by sponsors, subjects, or keywords.

**Parameters:**
- `bill_id` (str): OpenStates bill ID to find related bills for
- `jurisdiction` (str, optional): Limit search to specific jurisdiction

**Returns:** Dict with count of related bills, related bills data, and search criteria used.

**Example:**
```python
related = client.find_related_bills("ocd-bill/123", jurisdiction="ca")
print(f"Found {related['related_bills_count']} related bills")
```

#### `get_legislative_trends(jurisdiction=None, start_date=None, end_date=None, group_by="month")`
Analyzes legislative activity trends over time.

**Parameters:**
- `jurisdiction` (str, optional): Filter by jurisdiction
- `start_date` (str, optional): Start date in YYYY-MM-DD format
- `end_date` (str, optional): End date in YYYY-MM-DD format
- `group_by` (str): Time grouping - "day", "week", "month", "year" (default: "month")

**Returns:** Dict with trends data, summary statistics, and grouping information.

**Example:**
```python
trends = client.get_legislative_trends(jurisdiction="ca", group_by="month")
print(f"Peak activity in {trends['summary']['peak_period']}")
```

#### `search_bills_advanced(keywords=None, sponsors=None, classification=None, status=None, jurisdiction=None, date_from=None, date_to=None, limit=100)`
Advanced bill search with multiple criteria.

**Parameters:**
- `keywords` (List[str], optional): Keywords to search in titles/subjects
- `sponsors` (List[str], optional): Sponsor names to search for
- `classification` (List[str], optional): Bill classifications to filter by
- `status` (str, optional): Bill status filter
- `jurisdiction` (str, optional): Jurisdiction filter
- `date_from` (str, optional): Start date filter
- `date_to` (str, optional): End date filter
- `limit` (int): Maximum results to return

**Returns:** Dict with search results, count, criteria used, and data.

**Example:**
```python
results = client.search_bills_advanced(
    keywords=["education", "funding"],
    sponsors=["Smith", "Johnson"],
    jurisdiction="ca",
    limit=50
)
print(f"Found {results['count']} bills matching criteria")
```

#### `get_bill_statistics(jurisdiction=None, classification=None)`
Gets comprehensive statistics on bill data.

**Parameters:**
- `jurisdiction` (str, optional): Filter by jurisdiction
- `classification` (List[str], optional): Filter by classifications

**Returns:** Dict with summary statistics and top classifications.

**Example:**
```python
stats = client.get_bill_statistics(jurisdiction="ca")
print(f"Total bills: {stats['summary']['total_bills']}")
```

#### `export_filtered_data(table, filters=None, format="csv", output_path=None)`
Exports data with advanced filtering options.

**Parameters:**
- `table` (str): Table name ("openstates_bills", "openstates_people", "openstates_events")
- `filters` (Dict, optional): Key-value filters to apply
- `format` (str): Export format - "csv", "parquet", "json"
- `output_path` (str, optional): Custom output path

**Returns:** Dict with export status, file path, record count, and filters applied.

**Example:**
```python
export = client.export_filtered_data(
    table="openstates_bills",
    filters={"jurisdiction": "ca", "classification": ["bill"]},
    format="parquet"
)
print(f"Exported {export['records']} records to {export['file']}")
```

#### `compare_legislatures(jurisdiction1, jurisdiction2)`
Compares legislative activity between two jurisdictions.

**Parameters:**
- `jurisdiction1` (str): First jurisdiction code
- `jurisdiction2` (str): Second jurisdiction code

**Returns:** Dict with comparison data and differences between jurisdictions.

**Example:**
```python
comparison = client.compare_legislatures("ca", "tx")
print(f"CA has {comparison['differences']['bill_count']} more bills than TX")
```

#### `generate_bill_report(bill_id)`
Generates a comprehensive report for a specific bill.

**Parameters:**
- `bill_id` (str): OpenStates bill ID

**Returns:** Dict with bill data, sponsor analysis, subject analysis, and formatted report.

**Example:**
```python
report = client.generate_bill_report("ocd-bill/123")
print(report['summary_report'])
```

### Congress Functions

#### `query_congress_bills(congress=None, bill_type=None, limit=100)`
Queries Congress bills from database with filtering.

**Parameters:**
- `congress` (int, optional): Congress number filter
- `bill_type` (str, optional): Bill type filter (e.g., "hr", "s")
- `limit` (int): Maximum results to return

**Returns:** Dict with query results, count, and column information.

**Example:**
```python
bills = client.query_congress_bills(congress=118, bill_type="hr", limit=50)
print(f"Found {bills['count']} House bills in 118th Congress")
```

#### `analyze_bill_sponsors_congress(congress=None, bill_type=None)`
Analyzes bill sponsorship patterns in Congress data.

**Parameters:**
- `congress` (int, optional): Congress number filter
- `bill_type` (str, optional): Bill type filter

**Returns:** Dict with sponsorship analysis for Congress bills.

**Example:**
```python
sponsors = client.analyze_bill_sponsors_congress(congress=118)
print(f"Top sponsor: {list(sponsors['top_sponsors'].keys())[0]}")
```

#### `get_congressional_trends(start_congress=None, end_congress=None)`
Analyzes congressional activity trends by congress number.

**Parameters:**
- `start_congress` (int, optional): Starting congress number
- `end_congress` (int, optional): Ending congress number

**Returns:** Dict with trends by bill type and summary statistics.

**Example:**
```python
trends = client.get_congressional_trends(start_congress=115, end_congress=118)
print(f"Most active congress: {trends['summary']['most_active_congress']}")
```

#### `search_congress_bills_advanced(keywords=None, sponsors=None, congress=None, bill_type=None, limit=100)`
Advanced search for Congress bills with multiple criteria.

**Parameters:**
- `keywords` (List[str], optional): Keywords to search in titles
- `sponsors` (List[str], optional): Sponsor names to search for
- `congress` (int, optional): Congress number filter
- `bill_type` (str, optional): Bill type filter
- `limit` (int): Maximum results to return

**Returns:** Dict with search results and criteria used.

**Example:**
```python
results = client.search_congress_bills_advanced(
    keywords=["infrastructure", "transportation"],
    congress=118,
    limit=25
)
```

#### `analyze_member_activity(bioguide_id=None, congress=None)`
Analyzes legislative activity for congressional members.

**Parameters:**
- `bioguide_id` (str, optional): Specific member ID to analyze
- `congress` (int, optional): Congress number filter

**Returns:** Dict with member info and sponsored bills analysis.

**Example:**
```python
activity = client.analyze_member_activity(bioguide_id="S001227", congress=118)
print(f"Member sponsored {activity['sponsored_bills_count']} bills")
```

#### `compare_congresses(congress1, congress2)`
Compares legislative activity between two congresses.

**Parameters:**
- `congress1` (int): First congress number
- `congress2` (int): Second congress number

**Returns:** Dict with congress comparison and bill type distribution.

**Example:**
```python
comparison = client.compare_congresses(117, 118)
print(f"118th Congress: {comparison['congress_comparison'][118]['total_bills']} bills")
```

#### `export_congress_data(congress=None, bill_type=None, format="csv", output_path=None)`
Exports Congress bills data with filtering.

**Parameters:**
- `congress` (int, optional): Congress number filter
- `bill_type` (str, optional): Bill type filter
- `format` (str): Export format
- `output_path` (str, optional): Custom output path

**Returns:** Dict with export status and details.

**Example:**
```python
export = client.export_congress_data(congress=118, format="json")
print(f"Exported to {export['file']}")
```

### GovInfo Functions

#### `query_govinfo_documents(collection=None, start_date=None, end_date=None, limit=100)`
Queries GovInfo documents from database with filtering.

**Parameters:**
- `collection` (str, optional): Collection filter
- `start_date` (str, optional): Start date filter
- `end_date` (str, optional): End date filter
- `limit` (int): Maximum results to return

**Returns:** Dict with query results and metadata.

**Example:**
```python
docs = client.query_govinfo_documents(collection="BILLS", limit=100)
print(f"Found {docs['count']} documents")
```

#### `analyze_document_collections()`
Analyzes document distribution across GovInfo collections.

**Returns:** Dict with collection analysis and summary statistics.

**Example:**
```python
analysis = client.analyze_document_collections()
print(f"Most active collection: {analysis['summary']['most_active_collection']}")
```

#### `get_document_trends(collection=None, group_by="month")`
Analyzes document publication trends over time.

**Parameters:**
- `collection` (str, optional): Collection filter
- `group_by` (str): Time grouping period

**Returns:** Dict with trend data and summary statistics.

**Example:**
```python
trends = client.get_document_trends(collection="BILLS", group_by="quarter")
print(f"Total documents: {trends['summary']['total_documents']}")
```

#### `search_documents_advanced(keywords=None, collection=None, start_date=None, end_date=None, limit=100)`
Advanced search for GovInfo documents.

**Parameters:**
- `keywords` (List[str], optional): Keywords to search in titles
- `collection` (str, optional): Collection filter
- `start_date` (str, optional): Start date filter
- `end_date` (str, optional): End date filter
- `limit` (int): Maximum results to return

**Returns:** Dict with search results and criteria.

**Example:**
```python
results = client.search_documents_advanced(
    keywords=["executive", "order"],
    collection="FR",
    limit=50
)
```

#### `analyze_document_metadata(collection=None)`
Analyzes metadata patterns in GovInfo documents.

**Parameters:**
- `collection` (str, optional): Collection filter

**Returns:** Dict with metadata analysis and word frequency data.

**Example:**
```python
metadata = client.analyze_document_metadata(collection="BILLS")
print(f"Average title length: {metadata['metadata_analysis'][0]['avg_title_length']:.1f}")
```

#### `compare_collections(collection1, collection2)`
Compares document characteristics between two GovInfo collections.

**Parameters:**
- `collection1` (str): First collection code
- `collection2` (str): Second collection code

**Returns:** Dict with collection comparison and differences.

**Example:**
```python
comparison = client.compare_collections("BILLS", "PLAW")
print(f"Collection 1 has {comparison['collection_comparison'][collection1]['document_count']} documents")
```

#### `export_govinfo_data(collection=None, start_date=None, end_date=None, format="csv", output_path=None)`
Exports GovInfo documents data with filtering.

**Parameters:**
- `collection` (str, optional): Collection filter
- `start_date` (str, optional): Start date filter
- `end_date` (str, optional): End date filter
- `format` (str): Export format
- `output_path` (str, optional): Custom output path

**Returns:** Dict with export status and details.

**Example:**
```python
export = client.export_govinfo_data(collection="BILLS", format="parquet")
print(f"Exported {export['records']} documents")
```

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

## Advanced Usage Examples

This section provides comprehensive examples of using the MCP server for advanced legislative data analysis, including data ingestion, complex queries, analytics, and export operations.

### Data Ingestion

#### Ingest OpenStates Data
```bash
curl -X POST http://localhost:8080/mcp/ingest_data \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "openstates",
    "jurisdiction": "nc",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

#### Ingest Congress Data
```bash
curl -X POST http://localhost:8080/mcp/ingest_data \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "congress",
    "congress": 118,
    "bill_type": "hr"
  }'
```

#### Ingest GovInfo Data
```bash
curl -X POST http://localhost:8080/mcp/ingest_data \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "govinfo",
    "collection": "BILLS",
    "start_date": "2023-01-01",
    "end_date": "2023-12-31"
  }'
```

### Advanced Analytics

#### Analyze Bill Sponsors (OpenStates)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "openstates",
    "function": "analyze_bill_sponsors",
    "args": {"jurisdiction": "nc", "limit": 10}
  }'
```

#### Get Legislative Trends (OpenStates)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "openstates",
    "function": "get_legislative_trends",
    "args": {"jurisdiction": "nc", "start_year": 2020, "end_year": 2023}
  }'
```

#### Analyze Bill Sponsors (Congress)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "congress",
    "function": "analyze_bill_sponsors_congress",
    "args": {"congress": 118}
  }'
```

#### Get Congressional Trends
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "congress",
    "function": "get_congressional_trends",
    "args": {"start_congress": 115, "end_congress": 118}
  }'
```

#### Advanced Bill Search (Congress)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "congress",
    "function": "search_congress_bills_advanced",
    "args": {
      "keywords": ["infrastructure", "transportation"],
      "congress": 118,
      "limit": 25
    }
  }'
```

#### Analyze Member Activity
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "congress",
    "function": "analyze_member_activity",
    "args": {"bioguide_id": "S001227", "congress": 118}
  }'
```

#### Compare Congresses
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "congress",
    "function": "compare_congresses",
    "args": {"congress1": 117, "congress2": 118}
  }'
```

#### Analyze Document Collections (GovInfo)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "govinfo",
    "function": "analyze_document_collections",
    "args": {}
  }'
```

#### Get Document Trends (GovInfo)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "govinfo",
    "function": "get_document_trends",
    "args": {"collection": "BILLS", "group_by": "quarter"}
  }'
```

#### Advanced Document Search (GovInfo)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "govinfo",
    "function": "search_documents_advanced",
    "args": {
      "keywords": ["executive", "order"],
      "collection": "FR",
      "limit": 50
    }
  }'
```

#### Analyze Document Metadata (GovInfo)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "govinfo",
    "function": "analyze_document_metadata",
    "args": {"collection": "BILLS"}
  }'
```

#### Compare Collections (GovInfo)
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "govinfo",
    "function": "compare_collections",
    "args": {"collection1": "BILLS", "collection2": "PLAW"}
  }'
```

### Data Export

#### Export OpenStates Data
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "openstates",
    "function": "export_openstates_data",
    "args": {
      "jurisdiction": "nc",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "format": "csv"
    }
  }'
```

#### Export Congress Data
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "congress",
    "function": "export_congress_data",
    "args": {
      "congress": 118,
      "bill_type": "hr",
      "format": "json"
    }
  }'
```

#### Export GovInfo Data
```bash
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "site": "govinfo",
    "function": "export_govinfo_data",
    "args": {
      "collection": "BILLS",
      "start_date": "2023-01-01",
      "end_date": "2023-12-31",
      "format": "parquet"
    }
  }'
```

### Complex Multi-Step Analysis

#### Cross-Site Legislative Analysis Workflow
```bash
# 1. Register tokens for all sites
curl -X POST http://localhost:8080/mcp/register_token \
  -H "Content-Type: application/json" \
  -d '{"site": "openstates", "user_id": "alice", "api_key": "your_openstates_key"}'

curl -X POST http://localhost:8080/mcp/register_token \
  -H "Content-Type: application/json" \
  -d '{"site": "congress", "user_id": "alice", "api_key": "your_congress_key"}'

curl -X POST http://localhost:8080/mcp/register_token \
  -H "Content-Type: application/json" \
  -d '{"site": "govinfo", "user_id": "alice", "api_key": "your_govinfo_key"}'

# 2. Ingest data from multiple sources
curl -X POST http://localhost:8080/mcp/ingest_data \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "site": "openstates", "jurisdiction": "nc"}'

curl -X POST http://localhost:8080/mcp/ingest_data \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "site": "congress", "congress": 118}'

curl -X POST http://localhost:8080/mcp/ingest_data \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "site": "govinfo", "collection": "BILLS"}'

# 3. Perform comparative analysis
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "site": "congress", "function": "compare_congresses", "args": {"congress1": 117, "congress2": 118}}'

# 4. Export results
curl -X POST http://localhost:8080/mcp/execute \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "site": "openstates", "function": "export_openstates_data", "args": {"format": "csv"}}'
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
