"""Comprehensive Congress.gov ingestion procedure: orchestrate all data ingestion.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_comprehensive_ingest.py --congress 118
"""
import os
import argparse
import subprocess
import sys
from pathlib import Path

# Available ingestion scripts (only existing ones for now)
INGESTION_SCRIPTS = {
    'bills': 'congress_ingest.py',
    'members': 'congress_members_ingest.py',
    'committees': 'congress_committees_ingest.py',
    'votes': 'congress_votes_ingest.py',
    'bill_actions': 'congress_bill_actions_ingest.py',
    'bill_text': 'congress_bill_text_ingest.py',
    'summaries': 'congress_summaries_ingest.py',
    'treaties': 'congress_treaties_ingest.py',
    'nominations': 'congress_nominations_ingest.py',
    'hearings': 'congress_hearings_ingest.py',
    'congress': 'congress_congress_ingest.py'
    # New scripts to be added:
    # 'laws': 'congress_laws_ingest.py',
    # 'amendments': 'congress_amendments_ingest.py',
    # 'committee_reports': 'congress_committee_reports_ingest.py',
    # 'congressional_record': 'congress_congressional_record_ingest.py',
    # 'communications': 'congress_communications_ingest.py',
    # 'crs_reports': 'congress_crs_reports_ingest.py',
    # 'committee_prints': 'congress_committee_prints_ingest.py',
    # 'committee_meetings': 'congress_committee_meetings_ingest.py',
    # 'house_requirements': 'congress_house_requirements_ingest.py'
}

# Dependencies: some scripts need others to run first
DEPENDENCIES = {
    'bill_actions': ['bills'],
    'bill_text': ['bills'],
    'summaries': ['bills']
}

def run_ingestion_script(script_name: str, congress: int = None, api_key: str = None, extra_args: list = None):
    """Run a single ingestion script."""
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f"Warning: Script {script_name} not found at {script_path}")
        return False

    cmd = [sys.executable, str(script_path)]

    if congress:
        cmd.extend(['--congress', str(congress)])

    if api_key:
        cmd.extend(['--api_key', api_key])

    if extra_args:
        cmd.extend(extra_args)

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout

        if result.returncode == 0:
            print(f"✓ {script_name} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"✗ {script_name} failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr}")
            if result.stdout:
                print(f"Standard output: {result.stdout}")
            return False

    except subprocess.TimeoutExpired:
        print(f"✗ {script_name} timed out after 1 hour")
        return False
    except Exception as e:
        print(f"✗ {script_name} failed with exception: {e}")
        return False

def resolve_dependencies(scripts_to_run: list) -> list:
    """Resolve script dependencies and return ordered list."""
    ordered_scripts = []
    processed = set()

    def add_script(script):
        if script in processed:
            return
        # Add dependencies first
        if script in DEPENDENCIES:
            for dep in DEPENDENCIES[script]:
                if dep in scripts_to_run:
                    add_script(dep)
        ordered_scripts.append(script)
        processed.add(script)

    for script in scripts_to_run:
        add_script(script)

    return ordered_scripts

def ingest_all_congress_data(congress: int = None, api_key: str = None, scripts: list = None,
                           skip_dependencies: bool = False, max_pages: int = 999999):
    """Ingest all available Congress data."""

    if scripts is None:
        scripts = list(INGESTION_SCRIPTS.keys())

    # Validate script names
    invalid_scripts = [s for s in scripts if s not in INGESTION_SCRIPTS]
    if invalid_scripts:
        print(f"Error: Invalid script names: {invalid_scripts}")
        print(f"Available scripts: {list(INGESTION_SCRIPTS.keys())}")
        return False

    # Resolve dependencies
    if not skip_dependencies:
        scripts = resolve_dependencies(scripts)

    print(f"Will run scripts in order: {scripts}")

    # Prepare common arguments
    extra_args = ['--max_pages', str(max_pages)]

    success_count = 0
    total_count = len(scripts)

    for script_key in scripts:
        script_name = INGESTION_SCRIPTS[script_key]
        print(f"\n{'='*50}")
        print(f"Starting {script_key} ingestion ({success_count + 1}/{total_count})")
        print(f"{'='*50}")

        if run_ingestion_script(script_name, congress=congress, api_key=api_key, extra_args=extra_args):
            success_count += 1
        else:
            print(f"Failed to complete {script_key} ingestion")
            # Continue with other scripts unless it's a critical dependency

    print(f"\n{'='*50}")
    print(f"Ingestion Summary: {success_count}/{total_count} scripts completed successfully")
    print(f"{'='*50}")

    return success_count == total_count

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Comprehensive Congress.gov data ingestion')
    p.add_argument('--congress', type=int, default=None, help='Congress number to ingest')
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'), help='Congress.gov API key')
    p.add_argument('--scripts', nargs='+', choices=list(INGESTION_SCRIPTS.keys()) + ['all'],
                   default=['all'], help='Specific scripts to run (default: all)')
    p.add_argument('--skip-dependencies', action='store_true',
                   help='Skip dependency resolution (run scripts in specified order)')
    p.add_argument('--max_pages', type=int, default=999999,
                   help='Maximum pages to fetch for each script')
    p.add_argument('--list-scripts', action='store_true',
                   help='List available scripts and exit')

    args = p.parse_args()

    if args.list_scripts:
        print("Available ingestion scripts:")
        for key, script in INGESTION_SCRIPTS.items():
            deps = DEPENDENCIES.get(key, [])
            dep_str = f" (depends on: {', '.join(deps)})" if deps else ""
            print(f"  {key}: {script}{dep_str}")
        sys.exit(0)

    if not os.getenv('DATABASE_URL'):
        raise SystemExit('Please set DATABASE_URL environment variable')

    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY environment variable or pass --api_key')

    scripts_to_run = args.scripts if 'all' not in args.scripts else None

    success = ingest_all_congress_data(
        congress=args.congress,
        api_key=args.api_key,
        scripts=scripts_to_run,
        skip_dependencies=args.skip_dependencies,
        max_pages=args.max_pages
    )

    sys.exit(0 if success else 1)
