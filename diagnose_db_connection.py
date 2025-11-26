import os
import subprocess
import sys
import psycopg2
from dotenv import load_dotenv, find_dotenv
from urllib.parse import urlparse
import time

def run_command(command, description):
    print(f"\n--- {description} ---")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        print(f"STDOUT:\n{result.stdout.strip()}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr.strip()}")
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}.")
        print(f"STDOUT:\n{e.stdout.strip()}")
        print(f"STDERR:\n{e.stderr.strip()}")
        return False, e.stderr.strip()
    except FileNotFoundError:
        print(f"Error: Command '{command.split()[0]}' not found. Please ensure it's installed and in your PATH.")
        return False, f"Command '{command.split()[0]}' not found."
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False, str(e)

def diagnose_db_connection():
    report = []

    report.append("--- Database Connection Diagnostic Report ---")
    report.append(f"Timestamp: {time.ctime()}")
    report.append(f"Current Working Directory: {os.getcwd()}")

    # 1. Load Environment Variables
    report.append("\n--- 1. Environment Variable Check ---")
    if load_dotenv(find_dotenv(usecwd=True)):
        report.append("Loaded .env from current directory.")
    elif load_dotenv(find_dotenv(filename=".env", raise_error_if_not_found=False)):
        report.append("Loaded .env from parent directory.")
    else:
        report.append("No .env file found in current or parent directory.")
        report.append("Cannot proceed without DATABASE_URL. Please ensure .env exists.")
        print("\n".join(report))
        return

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        report.append("Error: DATABASE_URL not found in environment variables.")
        report.append("Please ensure DATABASE_URL is set in your .env file.")
        print("\n".join(report))
        return
    report.append(f"DATABASE_URL: {db_url}")

    # Parse DB URL
    try:
        parsed_url = urlparse(db_url)
        db_host = parsed_url.hostname
        db_port = parsed_url.port or 5432
        db_user = parsed_url.username
        db_name = parsed_url.path.strip('/')
        report.append(f"Parsed DB Host: {db_host}")
        report.append(f"Parsed DB Port: {db_port}")
        report.append(f"Parsed DB User: {db_user}")
        report.append(f"Parsed DB Name: {db_name}")
    except Exception as e:
        report.append(f"Error parsing DATABASE_URL: {e}")
        print("\n".join(report))
        return

    if not db_host:
        report.append("Error: Could not extract database host from DATABASE_URL.")
        print("\n".join(report))
        return

    # 2. Network Connectivity Checks
    report.append("\n--- 2. Network Connectivity Checks ---")
    
    # Ping
    ping_success, ping_output = run_command(f"ping -c 4 {db_host}", f"Pinging {db_host}")
    if ping_success:
        report.append(f"Ping to {db_host} successful.")
    else:
        report.append(f"Ping to {db_host} failed. Host may be unreachable.")

    # Netcat (nc) to check port
    netcat_cmd = f"nc -vz {db_host} {db_port}"
    netcat_success, netcat_output = run_command(netcat_cmd, f"Checking port {db_port} on {db_host} with netcat")
    if netcat_success and "succeeded" in netcat_output.lower():
        report.append(f"Port {db_port} on {db_host} is open and accepting connections (via netcat).")
    else:
        report.append(f"Port {db_port} on {db_host} is NOT open or connection refused (via netcat).")

    # 3. Python Psycopg2 Connection Attempt
    report.append("\n--- 3. Python Psycopg2 Connection Attempt ---")
    try:
        conn = psycopg2.connect(db_url)
        conn.close()
        report.append("Psycopg2 connection successful.")
    except psycopg2.OperationalError as e:
        report.append(f"Psycopg2 connection failed: OperationalError.\nDetails: {e}")
    except Exception as e:
        report.append(f"Psycopg2 connection failed: {type(e).__name__}.\nDetails: {e}")

    report.append("\n--- Diagnostic Report End ---")
    print("\n".join(report))

if __name__ == "__main__":
    diagnose_db_connection()
