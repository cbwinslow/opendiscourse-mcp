"""Congress.gov ingestion script: fetch bills via CongressClient and upsert into Postgres.
Enhanced with comprehensive monitoring, observability, and feature flags.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_ingest.py --congress 118 --per_page 50
"""
import os
import argparse
import psycopg2
from psycopg2.extras import Json
from mcp_server.clients.congress_client import CongressClient
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection
from mcp_server.utils.db_copy import copy_dataframe_to_table
from mcp_server.utils.monitoring import monitor, deduplicator
from mcp_server.utils.monitoring_framework import (
    FeatureFlags, get_monitor, monitor_ingestion, benchmark_function
)
import pandas as pd
import time
import json

DB_URL = os.getenv("DATABASE_URL")

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


@monitor_ingestion(data_type="bills", congress=None)
@benchmark_function
def ingest_bills(api_key: str, congress: int = None, billType: str = None, page: int = 1, max_pages: int = 10):
    # Initialize monitoring framework
    monitor_framework = get_monitor()
    flags = FeatureFlags.from_env()
    
    # Create monitoring job
    job_id = f"congress_bills_{congress or 'all'}_{billType or 'all'}_{int(time.time())}"
    
    # Set database job context for triggers
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_ingestion_job_context(%s)", (job_id,))
            conn.commit()
    except Exception as e:
        monitor_framework.logger.warning(f"Failed to set job context: {e}")
    
    # Create legacy monitoring job for compatibility
    job_id_legacy = monitor.create_job(
        source='congress',
        collection=f'bills_{congress or "all"}_{billType or "all"}',
        api_key=api_key[:8] + '...',  # Partial key for logging
        congress=congress,
        bill_type=billType
    )

    with monitor.monitor_job(job_id_legacy):
        client = CongressClient(api_key=api_key)
        use_copy = bool(os.getenv('USE_COPY', '') )
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

        while pages_processed < max_pages:
            res = client.search_bills(congress=congress, billType=billType, page=page)

            # Handle v3 API response structure
            results = res.get('bills', [])

            if not results:
                break

            pages_processed += 1

            df_rows = []
            for b in results:
                row = normalize_congress_bill(congress, b)

                # Check for duplicates using content hashing
                content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                if deduplicator.is_duplicate('congress_bills', content_hash, row['bill_id']):
                    duplicates_found += 1
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
            print(f"Ingested {len(results)} bills (total: {total_ingested}, duplicates: {duplicates_found})")

            # Check pagination for next page
            pagination = res.get('pagination', {})
            if not pagination.get('next') or pages_processed >= max_pages:
                break

            page += 1  # Continue to next page

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        print(f"Ingestion complete. Total bills processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--billType', default=None)
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--page', type=int, default=1)
    p.add_argument('--max_pages', type=int, default=10)  # Limit pages for testing
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')
    ingest_bills(api_key=args.api_key, congress=args.congress, billType=args.billType, page=args.page, max_pages=args.max_pages)
