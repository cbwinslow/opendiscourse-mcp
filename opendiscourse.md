# Script Organization Plan
## Problem Statement
The opendiscourse-mcp project has ~166 scripts scattered across the repository, with many loose scripts in the root directory. This creates:
* Difficulty finding specific scripts
* Unclear separation between tests, utilities, and production code
* Duplicate or outdated scripts with unclear purpose
* Poor maintainability and discoverability
## Current State Overview
**Root Directory Issues:**
* 40+ loose Python and shell scripts in project root
* Mix of test scripts, ingestion scripts, monitoring scripts, and utilities
* Multiple versions of similar scripts (e.g., `govinfo_swarm_ingest.py`, `govinfo_swarm_ingest_v_2.py`)
* Setup and server management scripts mixed with data processing
**Existing Structure:**
* `mcp_server/scripts/` - Contains congress ingestion scripts and shell scripts for different congresses
* `mcp_server/utils/` - Utility modules for ingestion, monitoring, etc.
* `mcp_server/clients/` - API client implementations
* `tests/` - Test suite (may have overlap with root test scripts)
* `scripts/` - Empty or minimal content
* `monitoring/` - Monitoring configurations
## Proposed Organization
### Directory Structure
```warp-runnable-command
opendiscourse-mcp/
├── scripts/
│   ├── ingestion/
│   │   ├── congress/
│   │   │   ├── bills.py
│   │   │   ├── members.py
│   │   │   ├── committees.py
│   │   │   ├── votes.py
│   │   │   ├── hearings.py
│   │   │   ├── treaties.py
│   │   │   └── bulk/
│   │   │       ├── ingest_20_years.sh
│   │   │       └── by_congress/ (109-119.sh)
│   │   ├── govinfo/
│   │   │   ├── govinfo_ingest.py
│   │   │   ├── swarm_ingest.py
│   │   │   └── bulk_ingest.py
│   │   ├── openstates/
│   │   │   └── openstates_ingest.py
│   │   └── unified/
│   │       ├── unified_ingestion.py
│   │       └── comprehensive_ingest.sh
│   ├── setup/
│   │   ├── setup_ingestion.sh
│   │   ├── setup_universal_ai_gateway.sh
│   │   ├── update_api_keys.sh
│   │   └── install_dependencies.sh
│   ├── monitoring/
│   │   ├── monitor_ingestion.sh
│   │   ├── monitor_congress_ingestion.sh
│   │   └── performance_monitor.py
│   ├── server/
│   │   ├── start_server.sh
│   │   ├── stop_server.sh
│   │   └── restart_server.sh
│   ├── utilities/
│   │   ├── coverage_analysis.py
│   │   ├── validate_api_schemas.py
│   │   └── database/
│   │       ├── test_connectivity.py
│   │       └── db_operations.py
│   └── deprecated/
│       └── (old versions, temp files)
├── tests/
│   ├── unit/
│   ├── integration/
│   │   ├── test_data_ingestion.py
│   │   ├── test_api.py
│   │   └── comprehensive_test.py
│   ├── end_to_end/
│   │   └── end_to_end_tests.py
│   └── harness/
│       └── test_unified_ingestion.sh
├── mcp_server/ (keep existing structure)
│   ├── scripts/ → reference to ../scripts/ingestion/
│   ├── utils/
│   ├── clients/
│   └── sql/
└── docs/
    └── scripts/
        └── README.md (script documentation)
```
### Migration Strategy
**Phase 1: Create New Structure**
1. Create new directory hierarchy under `scripts/`
2. Create subdirectories for each category
3. Create README files for each section
**Phase 2: Categorize and Move Scripts**
1. **Ingestion scripts** → `scripts/ingestion/`
    * Congress-specific → `scripts/ingestion/congress/`
    * GovInfo → `scripts/ingestion/govinfo/`
    * Unified/comprehensive → `scripts/ingestion/unified/`
2. **Test scripts** → `tests/` with proper subcategories
    * Unit tests → `tests/unit/`
    * Integration tests → `tests/integration/`
    * End-to-end → `tests/end_to_end/`
3. **Setup scripts** → `scripts/setup/`
4. **Monitoring scripts** → `scripts/monitoring/`
5. **Server management** → `scripts/server/`
6. **Utilities** → `scripts/utilities/`
7. **Deprecated/old versions** → `scripts/deprecated/`
**Phase 3: Update References**
1. Update import statements in Python files
2. Update shell script paths
3. Update documentation references
4. Update any CI/CD configurations
**Phase 4: Create Management Tools**
1. Create `scripts/manage_scripts.py` - Script inventory and management
2. Create `scripts/README.md` - Complete documentation
3. Add script execution wrappers if needed
### Implementation Details
**File Naming Conventions:**
* Use snake_case for Python scripts
* Use kebab-case or snake_case for shell scripts
* Remove version suffixes from filenames (use git for versioning)
* Prefix test files with `test_`
**Documentation Requirements:**
* Each script category gets a README.md
* Each script should have a docstring/header comment explaining:
    * Purpose
    * Usage
    * Dependencies
    * Example invocation
**Symlinks for Backward Compatibility:**
* Create symlinks in root for frequently-used scripts
* Add deprecation notices
* Plan to remove after transition period
### Verification Steps
1. All scripts are categorized and moved
2. No broken imports or path references
3. All tests still pass
4. Documentation is complete
5. No duplicate scripts remain
6. Git history is preserved**c**
