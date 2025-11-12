# OpenDiscourse MCP Server Development Tasks

This document outlines the detailed tasks and features for building a robust MCP (Model Context Protocol) server that reverse-engineers APIs from OpenStates, Congress.gov, and GovInfo. The server will provide LLMs with functions to query, ingest, manipulate, and transform data into flexible formats, with support for API tokens, bulk downloads, and data model exposure.

## Feature List

### Core Features
- **API Reverse Engineering**: Client libraries for OpenStates v3, Congress.gov, and GovInfo APIs
- **Data Ingestion Pipeline**: Convert API responses and XML bulk data into structured DataFrames
- **Database Storage**: Optimized PostgreSQL schemas with efficient data types for minimal storage
- **MCP Server Interface**: FastAPI-based server exposing functions to LLMs with per-user API key management
- **Bulk Data Handling**: Support for downloading and processing large legislative datasets

### Extended Features
- **Data Transformation**: Time series analysis, format conversion (CSV, Parquet, JSON)
- **Advanced Querying**: Complex filtering, aggregation, and cross-referencing capabilities
- **Error Handling & Resilience**: Rate limiting, retry logic, and graceful failure handling
- **Performance Optimization**: Connection pooling, caching, and async processing

### Future Features
- **LLM Integration**: Direct integration with popular LLM platforms
- **Real-time Updates**: Webhooks and streaming for live legislative data
- **Analytics Dashboard**: Web UI for data exploration and visualization
- **Multi-format Export**: Additional export formats and cloud storage integration
- **Advanced Security**: OAuth, encryption, and audit logging

## Overall Project Goals
- **Reverse Engineer APIs**: Create client libraries that interact with the three sites' endpoints.
- **Data Ingestion & Manipulation**: Ingest data into DataFrames, perform analysis, transform timeframes, and convert formats.
- **MCP Server**: Expose functions to LLMs via a FastAPI server, handling user API tokens and data models.
- **Database Integration**: Store ingested data in Postgres with correct datatypes and efficient queries.
- **Bulk Data Handling**: Support bulk downloads and ingestion for large datasets.

## Task Tiers

### Tier 1: Core Implementation (High Priority)
These are the foundational tasks required for basic functionality.

## Task 1: API Client Libraries
**Feature**: Build site-specific API clients for OpenStates, Congress.gov, and GovInfo.

### Microgoals
1. **Base Client Framework**
   - Criteria: `BaseClient` class with session management, API key handling, and error handling.
   - Test Criteria: Unit tests for session creation, key storage, and error responses.
   - Status: Completed (in `mcp_server/clients/base_client.py`).

2. **OpenStates Client**
   - Criteria: Methods for `get_openapi_schema`, `search_bills`, `get_bill`, `search_people`, `get_person`, `search_events`, `get_event`.
   - Test Criteria: Mocked HTTP tests for all methods, verifying parameter passing and response parsing.
   - Status: Completed (extended with people and events methods; unit tests added).

3. **Congress.gov Client**
   - Criteria: Methods for `search_bills`, `get_bill`, `get_bill_actions`, `get_bill_text`, `list_members`, `get_member`.
   - Test Criteria: Unit tests with mocked API responses for all endpoints.
   - Status: Completed (extended with actions, text, members methods; unit tests added).

4. **GovInfo Client**
   - Criteria: Methods for `list_collections`, `bulk_download`, `fetch_bulk_file`, `ingest_xml_to_df`.
   - Test Criteria: Tests for HTML parsing, file downloads, and XML processing.
   - Status: Completed (bulk listing and download implemented; refined XML ingestion; unit tests added).

### Completion Criteria for Task 1
- All clients inherit from `BaseClient`.
- Each client has at least 5 key methods covering primary endpoints.
- Error handling for API rate limits, invalid keys, and network issues.
- Unit tests for each client method (mocked HTTP responses).

## Task 2: Data Ingestion and Transformation Utilities
**Feature**: Utilities to convert API responses/XML into DataFrames, transform timeframes, and export formats.

### Microgoals
1. **JSON to DataFrame Ingestion**
   - Criteria: `json_results_to_dataframe` function with normalization and flattening.
   - Test Criteria: Test with sample JSON data, verify DataFrame structure and data types.
   - Status: Completed (in `mcp_server/utils/ingest.py`).

2. **XML to DataFrame Ingestion**
   - Criteria: `ingest_xml_to_df` function with XPath support and fallback parsing.
   - Test Criteria: Unit test with sample XML, verify DataFrame creation and data extraction.
   - Status: Completed (in `mcp_server/utils/xml_ingest.py`); unit test added.

3. **Time Series Transformation**
   - Criteria: `transform_timeframe` function for resampling DataFrames by date columns.
   - Test Criteria: Test with time series data, verify resampling logic.
   - Status: Completed (in `mcp_server/utils/time_series.py`).

4. **Format Export**
   - Criteria: `save_dataframe` function supporting CSV, Parquet, JSON.
   - Test Criteria: Test file creation and content validation for each format.
   - Status: Completed (in `mcp_server/utils/ingest.py`).

5. **Bulk Downloader**
   - Criteria: `fetch_file` function with streaming, resume, and progress bar.
   - Test Criteria: Mock file download tests with progress tracking.
   - Status: Completed (in `mcp_server/utils/downloader.py`).

### Completion Criteria for Task 2
- All utilities handle edge cases (empty data, invalid formats).
- Performance: Efficient for large datasets (streaming, chunking).
- Unit tests for each utility (e.g., XML ingest test exists).

## Task 3: Database Schema and Migration Scripts
**Feature**: SQL CREATE TABLE scripts for Postgres with correct datatypes and indexes.

### Microgoals
1. **OpenStates Schema**
   - Criteria: Tables for `openstates_bills`, `openstates_people`, `openstates_events` with TEXT, JSONB, TIMESTAMPTZ, arrays.
   - Test Criteria: Schema validation, index creation verification.
   - Status: Completed (in `mcp_server/sql/openstates_schema.sql`).

2. **Congress.gov Schema**
   - Criteria: Tables for `congress_bills`, `congress_members`, `congress_votes` with appropriate types.
   - Test Criteria: Table creation and data type verification.
   - Status: Completed (in `mcp_server/sql/congress_schema.sql`).

3. **GovInfo Schema**
   - Criteria: Table for `govinfo_documents` with JSONB for metadata.
   - Test Criteria: Schema application and column type checks.
   - Status: Completed (in `mcp_server/sql/govinfo_schema.sql`).

4. **DB Initialization Helper**
   - Criteria: `db_init.py` to apply SQL files; shell script `init_db.sh`.
   - Test Criteria: Migration script execution and table existence verification.
   - Status: Completed.

### Completion Criteria for Task 3
- All tables have PRIMARY KEY, indexes on key columns (e.g., jurisdiction, date).
- Datatypes match API schemas (e.g., arrays for classifications, JSONB for raw data).
- Migration scripts are idempotent (IF NOT EXISTS).

## Task 4: Ingestion Scripts
**Feature**: Python scripts to fetch data and upsert into Postgres, with options for bulk loading.

### Microgoals
1. **OpenStates Ingestion Script**
   - Criteria: `openstates_ingest.py` with psycopg2, SQLAlchemy, COPY modes.
   - Test Criteria: Integration test with mock data insertion.
   - Status: Completed (supports all modes).

2. **Congress.gov Ingestion Script**
   - Criteria: `congress_ingest.py` with similar modes.
   - Test Criteria: Data ingestion verification and database state checks.
   - Status: Completed.

3. **GovInfo Ingestion Script**
   - Criteria: `govinfo_ingest.py` with bulk download and XML ingest.
   - Test Criteria: Bulk file processing and XML parsing validation.
   - Status: Completed.

### Completion Criteria for Task 4
- Scripts handle pagination, rate limiting, and errors.
- Environment variables control ingestion mode (USE_COPY, USE_SQLALCHEMY).
- Logging and progress indicators.

## Task 5: MCP Server Implementation
**Feature**: FastAPI server exposing functions to LLMs, with token management and data model exposure.

### Microgoals
1. **Server Scaffold**
   - Criteria: Endpoints for `/mcp/register_token`, `/mcp/functions`, `/mcp/execute`.
   - Test Criteria: API endpoint tests with mock requests.
   - Status: Completed (in `mcp_server/main.py`).

2. **Token Management**
   - Criteria: In-memory store for API keys per user/site (replace with secure store).
   - Test Criteria: Token registration and retrieval tests.
   - Status: Completed.

3. **Function Registry**
   - Criteria: `/mcp/functions` lists available methods; `/mcp/execute` calls them.
   - Test Criteria: Function listing and execution endpoint tests.
   - Status: Completed.

4. **Data Model Exposure**
   - Criteria: Endpoint to return field schemas for endpoints (e.g., `/mcp/data_model`).
   - Test Criteria: Schema endpoint returns correct field definitions.
   - Status: Completed (added `/mcp/data_model` endpoint returning table schemas).

### Completion Criteria for Task 5
- Server handles user authentication via tokens.
- Functions are callable by LLMs with JSON args.
- Data model endpoint provides field types and examples.

### Tier 2: Extended Features (Medium Priority)
These enhance the core functionality with better usability and performance.

## Task 6: Testing and Validation
**Feature**: Comprehensive testing framework including unit tests, integration tests, and validation of ingestion pipelines.

### Microgoals
1. **Unit Tests**
   - Criteria: Tests for XML ingest, downloader, db_copy, and all client methods.
   - Test Criteria: All tests pass with >80% coverage.
   - Status: Completed (unit tests added for all clients and XML ingest).

2. **Integration Tests**
   - Criteria: Mocked API tests for clients; smoke tests for ingestion.
   - Test Criteria: End-to-end pipeline tests with mock data.
   - Status: Not started.

3. **Validation**
   - Criteria: Run ingestion scripts and verify data in DB.
   - Test Criteria: Data integrity checks and schema validation.
   - Status: Not started.

### Test Setup Details
#### Testing Framework Configuration
- **pytest Configuration**: Use `pytest.ini` for test discovery and coverage settings
- **Coverage Requirements**: Target >80% coverage for `mcp_server/` and `tests/` directories
- **Test Organization**: Group tests by module (clients, utils, server) in `tests/` directory

#### Mocking Strategy
- **HTTP Mocking**: Use `responses` or `httpx-mock` for API client testing
- **Database Mocking**: Use `pytest-postgresql` for integration tests with temporary databases
- **File System Mocking**: Use `tmp_path` fixtures for file operations testing

#### Integration Test Design
- **End-to-End Pipeline Tests**: Test complete flow from API call to database insertion
- **Mock Data**: Use realistic sample data for OpenStates, Congress.gov, and GovInfo responses
- **Database Validation**: Verify data integrity and schema compliance after ingestion

#### Test Data Management
- **Sample Datasets**: Create `tests/fixtures/` with JSON/XML samples from each API
- **Database Fixtures**: Use pytest fixtures to set up/cleanup test databases
- **API Response Fixtures**: Store mock responses for consistent testing

### Data Interaction Functions
#### MCP Server Endpoints
- **`/mcp/ingest_data`**: Trigger data ingestion from APIs to user-specified databases
- **`/mcp/query_data`**: Query data from database tables with flexible filtering
- **`/mcp/export_data`**: Export data from database tables to various formats
- **`/mcp/execute`**: Execute client methods for API interactions

#### Client Data Methods
- **`query_bills`**: Query bills from database with filtering options
- **`export_bills`**: Export bills data to CSV, Parquet, or JSON formats
- **`analyze_bill_sponsors`**: Analyze bill sponsorship patterns and statistics
- **`find_related_bills`**: Find bills related by sponsors, subjects, or keywords
- **`get_legislative_trends`**: Analyze legislative activity trends over time
- **`search_bills_advanced`**: Advanced bill search with multiple criteria
- **`get_bill_statistics`**: Get comprehensive statistics on bill data
- **`export_filtered_data`**: Export data with advanced filtering options
- **`compare_legislatures`**: Compare legislative activity between jurisdictions
- **`generate_bill_report`**: Generate detailed reports for specific bills
- **`query_congress_bills`**: Query Congress bills with filtering
- **`analyze_bill_sponsors_congress`**: Analyze Congress bill sponsorship patterns
- **`get_congressional_trends`**: Analyze congressional activity by congress number
- **`search_congress_bills_advanced`**: Advanced search for Congress bills
- **`analyze_member_activity`**: Analyze legislative activity for members
- **`compare_congresses`**: Compare activity between different congresses
- **`export_congress_data`**: Export Congress data with filtering
- **`query_govinfo_documents`**: Query GovInfo documents from database
- **`analyze_document_collections`**: Analyze document distribution across collections
- **`get_document_trends`**: Analyze document publication trends over time
- **`search_documents_advanced`**: Advanced search for GovInfo documents
- **`analyze_document_metadata`**: Analyze metadata patterns in documents
- **`compare_collections`**: Compare document characteristics between collections
- **`export_govinfo_data`**: Export GovInfo documents with filtering

### Completion Criteria for Task 6
- pytest suite passes.
- Coverage >80% for utilities and clients.
- Manual validation of sample data ingestion.
- Integration tests cover critical paths (client → ingest → DB).
- Data interaction functions work with user-specified database URLs.

## Implementation Approach for Core Features

### API Client Libraries Implementation
- **Inheritance Pattern**: All clients extend `BaseClient` for common functionality
- **Error Handling**: Implement exponential backoff for rate limits, custom exceptions for API errors
- **Response Processing**: Use pandas for JSON normalization, lxml/beautifulsoup for XML parsing
- **Configuration**: Environment variables for API keys, configurable timeouts and retries

### Data Ingestion Pipeline Implementation
- **Streaming Processing**: Use generators for large file processing to minimize memory usage
- **Type Safety**: Implement data validation schemas with pydantic or marshmallow
- **Performance Optimization**: Chunked reading for large files, parallel processing where applicable
- **Format Flexibility**: Abstract export interface to easily add new formats (e.g., Excel, SQLite)

### Database Integration Implementation
- **Schema Optimization**: Use PostgreSQL-specific types (JSONB, arrays) for flexible data storage
- **Indexing Strategy**: Composite indexes on commonly queried fields (date + jurisdiction)
- **Migration Management**: Version-controlled schema changes with rollback capabilities
- **Connection Pooling**: Implement connection reuse to handle concurrent requests efficiently

### MCP Server Implementation
- **Authentication**: JWT tokens for user sessions, API key validation per request
- **Function Registry**: Dynamic registration of client methods with metadata (parameters, return types)
- **Async Processing**: Use FastAPI's async capabilities for non-blocking I/O operations
- **Monitoring**: Integrate logging and metrics collection for operational visibility

### Bulk Data Handling Implementation
- **Download Management**: Resume-capable downloads with progress tracking and checksum validation
- **Storage Strategy**: Local caching with configurable retention policies
- **Processing Pipeline**: Queue-based architecture for handling multiple concurrent downloads
- **Error Recovery**: Checkpointing and restart capabilities for interrupted operations

## Task 7: Documentation and Examples
**Feature**: README, usage examples, and LLM integration guides.

### Microgoals
1. **README Updates**
   - Criteria: Installation, setup, API docs.
   - Test Criteria: Documentation accuracy and completeness checks.
   - Status: Completed (expanded README with full API docs, examples, schemas).

2. **Usage Examples**
   - Criteria: Scripts to register tokens, call functions, ingest data.
   - Test Criteria: Example scripts execute successfully.
   - Status: Not started.

3. **LLM Integration**
   - Criteria: Guide on how LLMs can use the MCP server.
   - Test Criteria: Integration examples work with test LLMs.
   - Status: Not started.

### Completion Criteria for Task 7
- README covers all features.
- Example scripts runnable.
- Clear instructions for API token setup.

### Tier 3: Future Enhancements (Low Priority)
These are nice-to-have features for production deployment and advanced use cases.

## Task 8: Production Hardening
**Feature**: Security, performance, and scalability improvements.

### Microgoals
1. **Security**
   - Criteria: Encrypt API keys, rate limiting, input validation.
   - Test Criteria: Security audit and penetration testing.
   - Status: Not started.

2. **Performance**
   - Criteria: Optimize queries, use connection pooling.
   - Test Criteria: Benchmark tests showing improved throughput.
   - Status: Not started.

3. **Scalability**
   - Criteria: Handle large datasets, async processing.
   - Test Criteria: Load testing with large data volumes.
   - Status: Not started.

### Completion Criteria for Task 8
- Secure token storage (e.g., Vault or encrypted DB).
- Benchmarks show efficient ingestion for 100k+ records.
- Server handles concurrent requests.

## Task 9: Advanced Analytics Features
**Feature**: Add data analysis and transformation capabilities.

### Microgoals
1. **Query Builder**
   - Criteria: API for complex queries across tables.
   - Test Criteria: Query execution and result validation.
   - Status: Not started.

2. **Data Export API**
   - Criteria: REST endpoints for data export in multiple formats.
   - Test Criteria: Export functionality and file integrity.
   - Status: Not started.

3. **Real-time Monitoring**
   - Criteria: Metrics and logging for API usage and performance.
   - Test Criteria: Monitoring dashboard and alert testing.
   - Status: Not started.

### Completion Criteria for Task 9
- Advanced queries execute efficiently.
- Export supports all major formats.
- Monitoring provides actionable insights.

## Task 10: LLM Integration Enhancements
**Feature**: Better support for LLM workflows and automation.

### Microgoals
1. **Workflow Templates**
   - Criteria: Predefined ingestion and analysis workflows.
   - Test Criteria: Template execution and customization.
   - Status: Not started.

2. **Context Awareness**
   - Criteria: Intelligent data suggestions based on LLM context.
   - Test Criteria: Context-aware response accuracy.
   - Status: Not started.

3. **Batch Processing**
   - Criteria: Queue and process large ingestion jobs asynchronously.
   - Test Criteria: Batch job completion and error handling.
   - Status: Not started.

### Completion Criteria for Task 10
- Workflows reduce manual configuration.
- Context awareness improves user experience.
- Batch processing handles large volumes reliably.

## Overall Completion Criteria
- All Tier 1 tasks completed with microgoals met.
- End-to-end pipeline: Fetch from API -> Ingest to DB -> Transform -> Expose to LLM.
- Code is documented, tested, and production-ready.
- Performance benchmarks meet requirements.
- Security audit passes.
