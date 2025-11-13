# Unified Legislative Data Ingestion System

This document describes the consolidated ingestion system that replaces all the individual ingestion scripts with a single, comprehensive interface.

## Overview

The unified ingestion system consolidates all the functionality from the following scripts into a single interface:

### Previous Scripts (Now Consolidated)

**Congress.gov Scripts:**
- `congress_ingest.py` - Bills
- `congress_members_ingest.py` - Members of Congress
- `congress_committees_ingest.py` - Committees
- `congress_votes_ingest.py` - Roll call votes
- `congress_bill_actions_ingest.py` - Bill actions
- `congress_bill_text_ingest.py` - Bill text
- `congress_summaries_ingest.py` - Bill summaries
- `congress_treaties_ingest.py` - Treaties
- `congress_nominations_ingest.py` - Nominations
- `congress_hearings_ingest.py` - Hearings
- `congress_congress_ingest.py` - Congress information

**GovInfo Scripts:**
- `govinfo_ingest.py` - GovInfo collections

**OpenStates Scripts:**
- `openstates_ingest.py` - State legislation

## The Unified Scripts

### 1. `unified_ingestion_simple.py` (Recommended)

This is the working, production-ready version that uses subprocess to call the existing scripts. It provides a clean interface while maintaining compatibility with all existing functionality.

### 2. `unified_ingestion.py` (Advanced)

This is a more advanced version that attempts to directly implement the ingestion logic. It's currently in development and may have some issues.

## Usage Examples

### Basic Usage

```bash
# Ingest Congress bills for a specific Congress
python unified_ingestion_simple.py --source congress --data-type bills --congress 118

# Ingest all Congress data types for Congress 118
python unified_ingestion_simple.py --source congress --data-type all --congress 118

# Ingest multiple Congresses
python unified_ingestion_simple.py --source congress --data-type bills --congress 116 117 118
```

### GovInfo Usage

```bash
# Ingest GovInfo BILLS collection for 2023
python unified_ingestion_simple.py --source govinfo --collection BILLS --year 2023

# Ingest all GovInfo BILLS (all years)
python unified_ingestion_simple.py --source govinfo --collection BILLS
```

### OpenStates Usage

```bash
# Ingest North Carolina legislation
python unified_ingestion_simple.py --source openstates --jurisdiction nc

# Ingest with search query
python unified_ingestion_simple.py --source openstates --jurisdiction nc --query "education"

# Ingest all jurisdictions
python unified_ingestion_simple.py --source openstates
```

### Comprehensive Usage

```bash
# Ingest everything (all sources, default parameters)
python unified_ingestion_simple.py --source all --comprehensive

# Comprehensive with custom limits
python unified_ingestion_simple.py --source all --comprehensive --max-pages 5 --timeout 600
```

### Dry Run Testing

```bash
# Test what would be executed without actually running
python unified_ingestion_simple.py --source congress --data-type all --congress 118 --dry-run

# Comprehensive dry run
python unified_ingestion_simple.py --source all --comprehensive --dry-run
```

## Parameters and Options

### Source Selection
- `--source {congress,govinfo,openstates,all}` - Data source to ingest from

### Congress Parameters
- `--data-type` - Congress data type(s): bills, members, committees, votes, bill_actions, bill_text, summaries, treaties, nominations, hearings, congress, all
- `--congress` - Congress number(s) (e.g., 116 117 118)

### GovInfo Parameters
- `--collection` - GovInfo collection: BILLS, STATUTES, CRR, CRPT, CREC, FR, GPO
- `--year` - Year for GovInfo collection

### OpenStates Parameters
- `--jurisdiction` - OpenStates jurisdiction code (e.g., nc, ca, tx)
- `--query` - OpenStates search query

### Processing Options
- `--max-pages` - Maximum pages to fetch (default: 10)
- `--per-page` - Records per page (default: 50)
- `--timeout` - Timeout in seconds (default: 300)
- `--download-dir` - Download directory for files (default: ./data)

### Special Flags
- `--dry-run` - Perform a dry run without executing scripts
- `--comprehensive` - Run comprehensive ingestion of all available data

## Migration Guide

### From Individual Scripts

**Old way:**
```bash
python mcp_server/scripts/congress_ingest.py --congress 118 --max_pages 10
python mcp_server/scripts/congress_members_ingest.py --congress 118
python mcp_server/scripts/govinfo_ingest.py --collection BILLS --year 2023
```

**New way:**
```bash
python unified_ingestion_simple.py --source congress --data-type bills members --congress 118 --max-pages 10
python unified_ingestion_simple.py --source govinfo --collection BILLS --year 2023
```

### From Shell Scripts

The existing shell scripts like `comprehensive_ingest.sh` can be replaced with:

```bash
python unified_ingestion_simple.py --source all --comprehensive
```

## Benefits of the Unified System

1. **Single Interface** - One script to rule them all
2. **Consistent Parameters** - Standardized parameter names and behavior
3. **Better Error Handling** - Centralized error reporting and logging
4. **Dry Run Support** - Test before execution
5. **Comprehensive Options** - All parameters in one place
6. **Progress Tracking** - Unified progress reporting
7. **Easier Maintenance** - Single codebase to maintain

## Environment Variables Required

The unified script requires the same environment variables as the original scripts:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
export CONGRESS_API_KEY="your_congress_api_key"
export GOVINFO_API_KEY="your_govinfo_api_key"
export OPENSTATES_API_KEY="your_openstates_api_key"  # Optional
```

## Output and Logging

The unified script provides:
- Real-time progress updates
- Comprehensive summary report
- Error collection and reporting
- Execution timing for each operation

Example output:
```
🚀 Starting ingestion for source: congress
📋 Running: python /home/cbwinslow/opendiscourse/mcp_server/scripts/congress_ingest.py --congress 118 --max_pages 10

================================================================================
🎉 UNIFIED INGESTION SUMMARY
================================================================================

✅ CONGRESS - bills_118
   📊 Records: 1,234
   ⏱️ Duration: 45.67s

✅ CONGRESS - members_118
   📊 Records: 535
   ⏱️ Duration: 12.34s

📈 TOTALS:
   📊 Records Processed: 1,769
   ⏱️ Total Duration: 58.01s
   ❌ Total Errors: 0

🎉 All ingestions completed successfully!
```

## File Structure

```
opendiscourse/
├── unified_ingestion_simple.py     # Main unified script (recommended)
├── unified_ingestion.py            # Advanced version (in development)
├── test_unified_ingestion.sh       # Test script
├── mcp_server/
│   └── scripts/                    # Original scripts (still work)
│       ├── congress_ingest.py
│       ├── congress_members_ingest.py
│       ├── govinfo_ingest.py
│       ├── openstates_ingest.py
│       └── ...
```

## Testing

Run the test script to verify functionality:

```bash
./test_unified_ingestion.sh
```

This will test:
- Help functionality
- Dry run operations
- Parameter validation
- Error handling

## Future Enhancements

The unified system is designed to accommodate future enhancements:

1. **Parallel Processing** - Run multiple ingestions concurrently
2. **Advanced Scheduling** - Built-in cron-like functionality
3. **Dependency Management** - Handle dependencies between data types
4. **Incremental Updates** - Only ingest new/changed data
5. **Performance Monitoring** - Detailed performance metrics
6. **Configuration Files** - YAML/JSON configuration support

## Troubleshooting

### Common Issues

1. **Missing API Keys**
   ```
   ERROR: CONGRESS_API_KEY environment variable must be set
   ```
   Solution: Set the required environment variables

2. **Script Not Found**
   ```
   Script not found: /path/to/script.py
   ```
   Solution: Ensure you're running from the project root directory

3. **Permission Denied**
   ```
   Permission denied
   ```
   Solution: Make the script executable with `chmod +x unified_ingestion_simple.py`

### Getting Help

```bash
python unified_ingestion_simple.py --help
```

This will show all available options and examples.

## Conclusion

The unified ingestion system provides a clean, consistent interface for all legislative data ingestion needs while maintaining backward compatibility with existing scripts. It's designed to be easier to use, maintain, and extend than the collection of individual scripts it replaces.