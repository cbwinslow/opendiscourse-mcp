# OpenDiscourse MCP Scripts

This directory contains all scripts for the OpenDiscourse legislative data system, organized by function.

## Directory Structure

```
scripts/
├── ingestion/          # Data ingestion scripts
│   ├── congress/       # Congress.gov data ingestion
│   ├── govinfo/        # GovInfo data ingestion
│   ├── openstates/     # OpenStates data ingestion
│   └── unified/        # Unified/comprehensive ingestion
├── setup/              # Setup and configuration scripts
├── monitoring/         # Monitoring and performance tracking
├── server/             # Server management (start/stop/restart)
├── utilities/          # General utility scripts
│   └── database/       # Database utilities and fixes
└── deprecated/         # Old or deprecated scripts
```

## Quick Reference

### Common Tasks

**Start the MCP server:**
```bash
./scripts/server/start_server.sh
```

**Run Congress data ingestion:**
```bash
python scripts/ingestion/congress/congress_ingest.py
```

**Monitor ingestion progress:**
```bash
./scripts/monitoring/monitor_ingestion.sh
```

**Verify API keys:**
```bash
python scripts/utilities/verify_api_keys.py
```

## Categories

### Ingestion Scripts (`ingestion/`)

Scripts for ingesting legislative data from various sources.

- **Congress** (`congress/`) - Federal legislative data
  - `congress_ingest.py` - Main congress ingestion
  - `bulk/` - Bulk ingestion scripts for multiple congresses
  - `by_congress/` - Individual congress ingestion (109-119)
  
- **GovInfo** (`govinfo/`) - Government publications
  - `govinfo_ingest.py` - Main govinfo ingestion
  - `swarm_ingest*.py` - Multi-threaded ingestion
  
- **Unified** (`unified/`) - Comprehensive ingestion
  - `unified_ingestion.py` - Unified ingestion orchestrator
  - `comprehensive_ingest.sh` - Shell-based comprehensive ingestion

### Setup Scripts (`setup/`)

Scripts for initial setup and configuration.

- `setup_ingestion.sh` - Configure ingestion environment
- `setup_universal_ai_gateway.sh` - AI gateway configuration
- `update_api_keys.sh` - Update API key configuration

### Monitoring Scripts (`monitoring/`)

Scripts for monitoring system health and performance.

- `monitor_ingestion.sh` - Monitor ingestion progress
- `monitor_congress_ingestion.sh` - Congress-specific monitoring
- `congress_ingestion_performance_system.py` - Performance tracking

### Server Scripts (`server/`)

Scripts for managing the MCP server.

- `start_server.sh` - Start the MCP FastAPI server
- `stop_server.sh` - Stop the running server

### Utility Scripts (`utilities/`)

General-purpose utility scripts.

- `coverage_analysis.py` - Analyze data coverage
- `validate_api_schemas.py` - Validate API response schemas
- `verify_api_keys.py` - Verify API key configuration
- `verify_dependencies.py` - Check system dependencies
- `ingestion_cli.py` - Command-line ingestion interface
- `docker_*.sh` - Docker management utilities

**Database Utilities** (`utilities/database/`)
- `check_*.py` - Database state checking
- `fix_*.py` - Database schema fixes
- `add_*.py` - Add database features (triggers, functions)
- `execute_sql.py` - Execute SQL scripts

## Usage Guidelines

### Running Python Scripts

Most Python scripts can be run directly:
```bash
python scripts/ingestion/congress/congress_ingest.py
```

Some require environment variables:
```bash
export DATABASE_URL="postgresql://user:pass@localhost/opendiscourse"
python scripts/ingestion/unified/unified_ingestion.py
```

### Running Shell Scripts

Shell scripts should be executable:
```bash
chmod +x scripts/server/start_server.sh
./scripts/server/start_server.sh
```

### Environment Requirements

- **Python 3.10+** required for all Python scripts
- **PostgreSQL 14+** database connection
- **API Keys** for Congress.gov, GovInfo, OpenStates

Required environment variables:
- `DATABASE_URL` - PostgreSQL connection string
- `CONGRESS_API_KEY` - Congress.gov API key (optional but recommended)
- `GOVINFO_API_KEY` - GovInfo API key (required for GovInfo ingestion)
- `OPENSTATES_API_KEY` - OpenStates API key (optional)

## Script Management

Use the script management tool for advanced operations:
```bash
python scripts/manage_scripts.py --list
python scripts/manage_scripts.py --run <script_name>
python scripts/manage_scripts.py --info <script_name>
```

## Development

When adding new scripts:

1. Place in appropriate category directory
2. Use descriptive names (snake_case for Python, kebab-case for shell)
3. Add docstring/header comment with:
   - Purpose
   - Usage instructions
   - Required environment variables
   - Dependencies
4. Update category README.md
5. Make shell scripts executable (`chmod +x`)

## Migration Notes

Scripts were reorganized on 2025-11-23:
- All root-level scripts moved to categorized directories
- `mcp_server/scripts/` contents moved to `scripts/ingestion/`
- Test scripts moved to `tests/` directory
- Import paths updated to reflect new structure

For backward compatibility, symlinks may exist in the root directory but will be removed in a future update.

## See Also

- [Ingestion Documentation](ingestion/README.md)
- [Testing Documentation](../tests/README.md)
- [MCP Server Documentation](../mcp_server/README.md)
- [Database Schema](../mcp_server/sql/README.md)
