"""OpenStates ingestion script: fetch bills and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python scripts/ingestion/openstates/openstates_ingest.py --jurisdiction nc --per_page 50
"""
import os
import argparse
import json
import psycopg2
from psycopg2.extras import Json
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection
from mcp_server.utils.db_copy import copy_dataframe_to_table
from mcp_server.utils.monitoring import monitor, deduplicator
import pandas as pd
from mcp_server.clients.openstates_client import OpenStatesClient
from mcp_server.utils.ingest import json_results_to_dataframe

DB_URL = os.getenv("DATABASE_URL")

UPSERT_BILL_SQL = """
INSERT INTO openstates_bills (id, session, jurisdiction, identifier, title, classification, subjects, created_at, updated_at, first_action_date, latest_action_date, latest_action_description, openstates_url, raw, updated_on)
VALUES (%(id)s, %(session)s, %(jurisdiction)s, %(identifier)s, %(title)s, %(classification)s, %(subject)s, %(created_at)s, %(updated_at)s, %(first_action_date)s, %(latest_action_date)s, %(latest_action_description)s, %(openstates_url)s, %(raw)s, now())
ON CONFLICT (id) DO UPDATE SET
  session = EXCLUDED.session,
  jurisdiction = EXCLUDED.jurisdiction,
  identifier = EXCLUDED.identifier,
  title = EXCLUDED.title,
  classification = EXCLUDED.classification,
  subjects = EXCLUDED.subjects,
  created_at = EXCLUDED.created_at,
  updated_at = EXCLUDED.updated_at,
  first_action_date = EXCLUDED.first_action_date,
  latest_action_date = EXCLUDED.latest_action_date,
  latest_action_description = EXCLUDED.latest_action_description,
  openstates_url = EXCLUDED.openstates_url,
  raw = EXCLUDED.raw,
  updated_on = now()
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_bill(bill: dict) -> dict:
    """Normalize OpenStates bill data with proper type handling and validation."""
    
    # Handle jurisdiction field safely
    jurisdiction = None
    if 'jurisdiction' in bill:
        if isinstance(bill['jurisdiction'], dict):
            jurisdiction = bill['jurisdiction'].get('id')
        elif isinstance(bill['jurisdiction'], str):
            jurisdiction = bill['jurisdiction']
    
    # Handle classification field - ensure it's a list
    classification = bill.get('classification', [])
    if classification is None:
        classification = []
    elif not isinstance(classification, list):
        classification = [str(classification)]
    
    # Handle subject field - ensure it's a list
    subject = bill.get('subject', [])
    if subject is None:
        subject = []
    elif not isinstance(subject, list):
        subject = [str(subject)]
    
    # Safely extract dates
    def safe_date(date_field):
        date_val = bill.get(date_field)
        if date_val is None:
            return None
        if isinstance(date_val, str):
            return date_val
        # Convert other types to string if needed
        return str(date_val)
    
    return {
        'id': bill.get('id'),
        'session': bill.get('session'),
        'jurisdiction': jurisdiction,
        'identifier': bill.get('identifier'),
        'title': bill.get('title'),
        'classification': classification,
        'subject': subject,
        'created_at': safe_date('created_at'),
        'updated_at': safe_date('updated_at'),
        'first_action_date': safe_date('first_action_date'),
        'latest_action_date': safe_date('latest_action_date'),
        'latest_action_description': bill.get('latest_action_description'),
        'openstates_url': bill.get('openstates_url'),
        'raw': Json(bill)
    }


def ingest_bills(api_key: str, jurisdiction: str = None, q: str = None, page: int = 1, per_page: int = 999999):
    # Create monitoring job
    job_id = monitor.create_job(
        source='openstates',
        collection=f'bills_{jurisdiction or "all"}_{q or "all"}',
        api_key=api_key[:8] + '...',  # Partial key for logging
        jurisdiction=jurisdiction,
        query=q
    )

    with monitor.monitor_job(job_id):
        client = OpenStatesClient(api_key=api_key)
        use_copy = bool(os.getenv('USE_COPY', '') )
        use_sqlalchemy = bool(os.getenv('USE_SQLALCHEMY', ''))

        buffer_rows = []
        conn = None
        raw_conn = None
        if use_sqlalchemy:
            engine = get_sqlalchemy_engine()
        else:
            conn = connect_db(DB_URL)
            cur = conn.cursor()

        total_ingested = 0
        duplicates_found = 0

        while True:
            res = client.search_bills(jurisdiction=jurisdiction, q=q, page=page, per_page=per_page)
            results = res.get('results') or res.get('data') or res.get('results', [])
            if not results:
                break

            df_rows = []
            for b in results:
                try:
                    row = normalize_bill(b)

                    # Skip if missing required fields
                    if not row.get('id') or not row.get('jurisdiction'):
                        continue

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('openstates_bills', content_hash, row['id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        # Convert lists to PostgreSQL array format safely
                        classification_str = None
                        if row['classification']:
                            classification_str = '{' + ','.join(str(x) for x in row['classification']) + '}'
                        
                        subjects_str = None
                        if row['subject']:
                            subjects_str = '{' + ','.join(str(x) for x in row['subject']) + '}'
                        
                        df_rows.append({
                            'id': row['id'],
                            'session': row['session'],
                            'jurisdiction': row['jurisdiction'],
                            'identifier': row['identifier'],
                            'title': row['title'],
                            'classification': classification_str,
                            'subjects': subjects_str,
                            'created_at': row['created_at'],
                            'updated_at': row['updated_at'],
                            'first_action_date': row['first_action_date'],
                            'latest_action_date': row['latest_action_date'],
                            'latest_action_description': row['latest_action_description'],
                            'openstates_url': row['openstates_url'],
                        })
                    elif use_sqlalchemy:
                        # SQLAlchemy path - use engine.execute with parameterized statements
                        with engine.begin() as connection:
                            connection.execute(UPSERT_BILL_SQL, row)
                    else:
                        cur.execute(UPSERT_BILL_SQL, row)
                        
                except Exception as e:
                    logger.warning(f"Error processing bill {b.get('id', 'unknown')}: {e}")
                    continue

            if use_copy and df_rows:
                df = pd.DataFrame(df_rows)
                raw_conn = get_raw_connection()
                copy_dataframe_to_table(raw_conn, df, 'openstates_bills', {
                    'id': 'id', 'session': 'session', 'jurisdiction': 'jurisdiction', 'identifier': 'identifier',
                    'title': 'title', 'classification': 'classification', 'subjects': 'subjects', 'created_at': 'created_at',
                    'updated_at': 'updated_at', 'first_action_date': 'first_action_date', 'latest_action_date': 'latest_action_date',
                    'latest_action_description': 'latest_action_description', 'openstates_url': 'openstates_url'
                })
                raw_conn.close()

            if not use_sqlalchemy and not use_copy:
                conn.commit()

            total_ingested += len(results)
            monitor.update_progress(job_id, total_ingested, duplicates_found)
            print(f"Ingested {len(results)} bills (total: {total_ingested}, duplicates: {duplicates_found})")

            if len(results) < per_page:
                break
            page += 1

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        print(f"Ingestion complete. Total bills processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--jurisdiction', default=None)
    p.add_argument('--q', default=None)
    p.add_argument('--api_key', default=os.getenv('OPENSTATES_API_KEY'))
    p.add_argument('--page', type=int, default=1)
    p.add_argument('--per_page', type=int, default=999999)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set OPENSTATES_API_KEY or pass --api_key')
    ingest_bills(api_key=args.api_key, jurisdiction=args.jurisdiction, q=args.q, page=args.page, per_page=args.per_page)
