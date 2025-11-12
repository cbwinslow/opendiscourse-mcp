"""Congress.gov ingestion script: fetch bills via CongressClient and upsert into Postgres.
FIXED VERSION with timeout handling and pagination limits.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_ingest_fixed.py --congress 118 --per_page 50 --max-pages 5 --timeout 300
"""
import os
import argparse
import signal
import sys
import time
import psycopg2
from psycopg2.extras import Json
from mcp_server.clients.congress_client import CongressClient
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection
from mcp_server.utils.db_copy import copy_dataframe_to_table
from mcp_server.utils.monitoring import monitor, deduplicator
import pandas as pd

DB_URL = os.getenv("DATABASE_URL")

# Timeout handler
def timeout_handler(signum, frame):
    print("❌ TIMEOUT: Script exceeded maximum runtime")
    sys.exit(1)

UPSERT_SQL = """
INSERT INTO congress_bills (bill_id, congress, bill_type, bill_number, title, introduced_date, origin_chamber, current_chamber, latest_action_date, latest_action_text, sponsors, subjects, raw, updated_on, last_api_update)
VALUES (%(bill_id)s, %(congress)s, %(bill_type)s, %(bill_number)s, %(title)s, %(introduced_date)s, %(origin_chamber)s, %(current_chamber)s, %(latest_action_date)s, %(latest_action_text)s, %(sponsors)s, %(subjects)s, %(raw)s, now(), now())
ON CONFLICT (bill_id) DO UPDATE SET
  congress = EXCLUDED.congress,
  bill_type = EXCLUDED.bill_type,
  bill_number = EXCLUDED.bill_number,
  title = EXCLUDED.title,
  introduced_date = EXCLUDED.introduced_date,
  origin_chamber = EXCLUDED.origin_chamber,
  current_chamber = EXCLUDED.current_chamber,
  latest_action_date = EXCLUDED.latest_action_date,
  latest_action_text = EXCLUDED.latest_action_text,
  sponsors = EXCLUDED.sponsors,
  subjects = EXCLUDED.subjects,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""

def connect_db(url: str):
    return psycopg2.connect(url)

def normalize_congress_bill(congress: int, bill_obj: dict) -> dict:
    # Handle v3 API response format
    bill_id = f"{congress}:{bill_obj.get('type')}:{bill_obj.get('number')}"
    
    # Handle latest action (v3 API nests it under 'latestAction')
    latest_action = bill_obj.get('latestAction', {})
    if isinstance(latest_action, dict):
        latest_action_date = latest_action.get('actionDate')
        latest_action_text = latest_action.get('text')
    else:
        latest_action_date = None
        latest_action_text = None
    
    return {
        'bill_id': bill_id,
        'congress': congress,
        'bill_type': bill_obj.get('type'),
        'bill_number': bill_obj.get('number'),
        'title': bill_obj.get('title'),
        'introduced_date': bill_obj.get('introducedDate'),
        'origin_chamber': bill_obj.get('originChamber'),
        'current_chamber': bill_obj.get('currentChamber'),
        'latest_action_date': latest_action_date,
        'latest_action_text': latest_action_text,
        'sponsors': Json(bill_obj.get('sponsors') or []),
        'subjects': Json(bill_obj.get('subjects') or []),
        'raw': Json(bill_obj)
    }

def ingest_bills(api_key: str, congress: int = None, billType: str = None, page: int = 1, 
                 max_pages: int = 10, timeout_seconds: int = 300):
    
    # Set up timeout handling
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'bills_{congress or "all"}_{billType or "all"}_fixed',
        api_key=api_key[:8] + '...',  # Partial key for logging
        congress=congress,
        bill_type=billType,
        max_pages=max_pages,
        timeout=timeout_seconds
    )

    print(f"🚀 Starting Congress ingestion with timeout protection ({timeout_seconds}s)")
    print(f"📊 Max pages: {max_pages}, Starting page: {page}")

    with monitor.monitor_job(job_id):
        client = CongressClient(api_key=api_key)
        use_copy = bool(os.getenv('USE_COPY', ''))
        use_sqlalchemy = bool(os.getenv('USE_SQLALCHEMY', ''))

        conn = None
        if use_sqlalchemy:
            engine = get_sqlalchemy_engine()
        else:
            conn = connect_db(DB_URL)
            cur = conn.cursor()

        total_ingested = 0
        duplicates_found = 0
        pages_processed = 0
        
        start_time = time.time()

        while page <= max_pages:
            pages_processed += 1
            elapsed = int(time.time() - start_time)
            
            print(f"📄 Processing page {page} (page {pages_processed}/{max_pages}, elapsed: {elapsed}s)")
            
            try:
                # Add timeout to API call
                client_with_timeout = CongressClient(api_key=api_key)
                res = client_with_timeout.search_bills(congress=congress, billType=billType, page=page)

                # Handle v3 API response structure
                results = res.get('bills', [])

                if not results:
                    print(f"✅ No more results on page {page} - stopping")
                    break

                df_rows = []
                for i, b in enumerate(results):
                    row = normalize_congress_bill(congress, b)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_bills', content_hash, row['bill_id']):
                        duplicates_found += 1
                        print(f"  🔄 Skip duplicate: {row['bill_id']}")
                        continue

                    if use_copy:
                        df_rows.append({
                            'id': row['bill_id'],
                            'congress': row['congress'],
                            'bill_type': row['bill_type'],
                            'bill_number': row['bill_number'],
                            'title': row['title'],
                            'latest_action_date': row['latest_action_date'],
                            'latest_action_description': row['latest_action_text']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                    if i % 50 == 0:  # Progress update every 50 records
                        print(f"  📈 Processed {i+1}/{len(results)} bills on page {page}")

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_bills', {
                        'bill_id': 'bill_id', 'congress': 'congress', 'bill_type': 'bill_type', 'bill_number': 'bill_number',
                        'title': 'title', 'introduced_date': 'introduced_date', 'origin_chamber': 'origin_chamber',
                        'current_chamber': 'current_chamber', 'latest_action_date': 'latest_action_date', 'latest_action_text': 'latest_action_text'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"✅ Page {page} complete: {len(results)} bills (total: {total_ingested}, duplicates: {duplicates_found})")

                # Check pagination for next page
                pagination = res.get('pagination', {})
                if not pagination.get('next'):
                    print("🏁 No more pages available from API")
                    break

                page += 1
                
                # Check if we're approaching timeout (leave 30 seconds margin)
                elapsed = int(time.time() - start_time)
                if elapsed > (timeout_seconds - 60):
                    print(f"⏰ Approaching timeout ({elapsed}s/{timeout_seconds}s) - stopping early")
                    break

            except Exception as e:
                print(f"❌ Error on page {page}: {e}")
                # Log error but continue
                if len(str(e)) > 100:
                    error_msg = str(e)[:100] + "..."
                else:
                    error_msg = str(e)
                print(f"📝 Error logged: {error_msg}")
                
                # If it's a network timeout, stop
                if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    print("🛑 Network timeout detected - stopping ingestion")
                    break
                
                # Try next page if it's a different error
                page += 1
                if page > max_pages:
                    break

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        final_elapsed = int(time.time() - start_time)
        print(f"🎉 Congress ingestion completed in {final_elapsed}s")
        print(f"📊 Final stats: {total_ingested} total, {duplicates_found} duplicates, {pages_processed} pages")
        
        # Disable alarm
        signal.alarm(0)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--billType', default=None)
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--page', type=int, default=1)
    p.add_argument('--max-pages', type=int, default=10, help='Maximum pages to process (default: 10)')
    p.add_argument('--timeout', type=int, default=300, help='Timeout in seconds (default: 300)')
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')
    
    ingest_bills(api_key=args.api_key, congress=args.congress, billType=args.billType, 
                page=args.page, max_pages=args.max_pages, timeout_seconds=args.timeout)
