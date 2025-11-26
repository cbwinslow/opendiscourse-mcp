import os
import subprocess
import time
import sys
from dotenv import load_dotenv, find_dotenv

# Load environment variables
if load_dotenv(find_dotenv(usecwd=True)):
    print("Loaded .env from current directory.")
elif load_dotenv(find_dotenv(filename=".env", raise_error_if_not_found=False)):
    print("Loaded .env from parent directory.")
else:
    print("No .env file found in current or parent directory. Exiting.")
    sys.exit(1)

# Verify essential environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
CONGRESS_API_KEY = os.getenv("CONGRESS_API_KEY")
GOVINFO_API_KEY = os.getenv("GOVINFO_API_KEY")
OPENSTATES_API_KEY = os.getenv("OPENSTATES_API_KEY")

if not all([DATABASE_URL, CONGRESS_API_KEY, GOVINFO_API_KEY, OPENSTATES_API_KEY]):
    print("Error: One or more essential environment variables are missing.")
    print(f"DATABASE_URL: {DATABASE_URL}")
    print(f"CONGRESS_API_KEY: {CONGRESS_API_KEY}")
    print(f"GOVINFO_API_KEY: {GOVINFO_API_KEY}")
    print(f"OPENSTATES_API_KEY: {OPENSTATES_API_KEY}")
    sys.exit(1)

# Ensure PYTHONPATH is set correctly for script imports
os.environ['PYTHONPATH'] = os.getcwd() + ":" + os.getenv('PYTHONPATH', '')

INGESTION_LOG_DIR = "./logs"
os.makedirs(INGESTION_LOG_DIR, exist_ok=True)

def run_ingestion_script(name, command, env_vars=None):
    """Runs an ingestion script in a subprocess and captures output."""
    full_env = os.environ.copy()
    if env_vars:
        full_env.update(env_vars)

    log_file_path = os.path.join(INGESTION_LOG_DIR, f"{name.lower().replace(' ', '_')}_ingestion.log")
    
    with open(log_file_path, "a") as log_file:
        print(f"🚀 Starting {name} ingestion. Logging to {log_file_path}")
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=log_file,
            stderr=log_file,
            env=full_env
        )
    return process, log_file_path

processes = []
log_paths = []

# 1. Congress Ingestion
congress_cmd = "python scripts/ingestion/congress/run_bulk_ingestion.py"
print("--- Scheduling Congress Ingestion ---")
congress_process, congress_log = run_ingestion_script("Congress", congress_cmd)
processes.append(("Congress", congress_process))
log_paths.append(congress_log)

# 2. GovInfo Ingestion (BILLS for years 2000-2024)
govinfo_years = range(2000, 2025)
govinfo_collection = "BILLS"
print(f"--- Scheduling GovInfo Ingestion (Collection: {govinfo_collection}, Years: {min(govinfo_years)}-{max(govinfo_years)}) ---")
for year in govinfo_years:
    govinfo_cmd = f"python scripts/ingestion/govinfo/govinfo_ingest.py --collection {govinfo_collection} --year {year}"
    govinfo_process, govinfo_log = run_ingestion_script(f"GovInfo-{govinfo_collection}-{year}", govinfo_cmd)
    processes.append((f"GovInfo-{govinfo_collection}-{year}", govinfo_process))
    log_paths.append(govinfo_log)

# 3. OpenStates Ingestion (all US states)
import us
state_abbrs = [state.abbr.lower() for state in us.states.STATES]
print(f"--- Scheduling OpenStates Ingestion (All {len(state_abbrs)} US states) ---")
for abbr in state_abbrs:
    openstates_cmd = f"python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction {abbr}"
    openstates_process, openstates_log = run_ingestion_script(f"OpenStates-{abbr}", openstates_cmd)
    processes.append((f"OpenStates-{abbr}", openstates_process))
    log_paths.append(openstates_log)

print("\n--- All Ingestion Processes Launched ---")
print("Monitoring active processes...")

# Monitor processes
running_processes = list(processes)
while running_processes:
    for name, proc in list(running_processes):
        if proc.poll() is not None:  # Process has terminated
            running_processes.remove((name, proc))
            if proc.returncode == 0:
                print(f"✅ {name} ingestion completed successfully.")
            else:
                print(f"❌ {name} ingestion failed with exit code {proc.returncode}. Check its log file.")
        else:
            print(f"⏳ {name} is still running...")
    time.sleep(10) # Check every 10 seconds

print("\n--- All Ingestion Completed ---")
print("Summary of log files:")
for path in log_paths:
    print(f"- {path}")
print("\nEnsure to check individual log files for detailed results and any errors.")
