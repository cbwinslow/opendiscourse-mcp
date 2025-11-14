"""Congress.gov bill actions ingestion script: fetch bill actions and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_bill_actions_ingest.py --congress 118
"""
import os
import argparse
import psycopg2
from psycopg2.extras import Json
from mcp_server.clients.congress_client import CongressClient
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection
from mcp_server.utils.db_copy import copy_dataframe_to_table
from mcp_server.utils.monitoring import monitor, deduplicator
import pandas as pd

DB_URL = os.getenv("DATABASE_URL")

UPSERT_SQL = """
INSERT INTO congress_bill_actions (action_id, bill_id, action_date, sequence_number, action_code, action_text, action_type, chamber, committee, source_system_code, source_system_name, created_on, updated_on)
VALUES (%(action_id)s, %(bill_id)s, %(action_date)s, %(sequence_number)s, %(action_code)s, %(action_text)s, %(action_type)s, %(chamber)s, %(committee)s, %(source_system_code)s, %(source_system_name)s, now(), now())
ON CONFLICT (action_id) DO UPDATE SET
  bill_id = EXCLUDED.bill_id,
  action_date = EXCLUDED.action_date,
  sequence_number = EXCLUDED.sequence_number,
  action_code = EXCLUDED.action_code,
  action_text = EXCLUDED.action_text,
  action_type = EXCLUDED.action_type,
  chamber = EXCLUDED.chamber,
  committee = EXCLUDED.committee,
  source_system_code = EXCLUDED.source_system_code,
  source_system_name = EXCLUDED.source_system_name,
  updated_on = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_bill_action(bill_id: str, action_obj: dict) -> dict:
    """Normalize a congress bill action object for database insertion."""
    # Create composite action ID
    action_date = action_obj.get('actionDate')
    sequence_number = action_obj.get('sequenceNumber', 0)
    action_id = f"{bill_id}_{action_date}_{sequence_number}"

    # Action details
    action_code = action_obj.get('actionCode')
    action_text = action_obj.get('text')
    action_type = action_obj.get('type')

    # Chamber and committee information
    chamber = action_obj.get('chamber')
    committee = Json(action_obj.get('committee'))

    # Source system
    source_system_code = action_obj.get('sourceSystem', {}).get('code')
    source_system_name = action_obj.get('sourceSystem', {}).get('name')

    return {
        'action_id': action_id,
        'bill_id': bill_id,
        'action_date': action_date,
        'sequence_number': sequence_number,
        'action_code': action_code,
        'action_text': action_text,
        'action_type': action_type,
        'chamber': chamber,
        'committee': committee,
        'source_system_code': source_system_code,
        'source_system_name': source_system_name
    }


def get_bills_to_process(congress: int = None, limit: int = None):
    """Get bills that need action processing."""
    engine = get_sqlalchemy_engine()

    query = "SELECT bill_id, congress, bill_type, bill_number FROM congress_bills WHERE 1=1"
    params = {}

    if congress:
        query += " AND congress = %(congress)s"
        params["congress"] = congress

    query += " ORDER BY congress DESC, bill_number DESC"

    if limit:
        query += f" LIMIT {limit}"

    with engine.connect() as conn:
        result = conn.execute(query, params)
        bills = result.fetchall()

    return bills


def ingest_bill_actions(api_key: str, congress: int = None, limit: int = None, max_pages: int = 999999):
    """Ingest bill actions from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'bill_actions_{congress or "all"}',
        api_key=api_key[:8] + '...',
        congress=congress
    )

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

        # Get bills to process
        bills = get_bills_to_process(congress=congress, limit=limit)
        print(f"Processing actions for {len(bills)} bills")

        total_actions_ingested = 0
        duplicates_found = 0
        bills_processed = 0

        for bill_row in bills:
            bill_id, bill_congress, bill_type, bill_number = bill_row
            bills_processed += 1

            try:
                # Get actions for this bill
                res = client.get_bill_actions(bill_congress, bill_type.lower(), bill_number)

                # Handle API response structure
                actions = res.get('actions', [])

                if not actions:
                    continue

                df_rows = []
                for action in actions:
                    row = normalize_congress_bill_action(bill_id, action)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=[])
                    if deduplicator.is_duplicate('congress_bill_actions', content_hash, row['action_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'action_id': row['action_id'],
                            'bill_id': row['bill_id'],
                            'action_date': row['action_date'],
                            'sequence_number': row['sequence_number'],
                            'action_code': row['action_code'],
                            'action_text': row['action_text'],
                            'action_type': row['action_type'],
                            'chamber': row['chamber']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_bill_actions', {
                        'action_id': 'action_id', 'bill_id': 'bill_id', 'action_date': 'action_date',
                        'sequence_number': 'sequence_number', 'action_code': 'action_code',
                        'action_text': 'action_text', 'action_type': 'action_type', 'chamber': 'chamber'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_actions_ingested += len(actions)
                monitor.update_progress(job_id, total_actions_ingested, duplicates_found)

                if bills_processed % 100 == 0:
                    print(f"Processed {bills_processed} bills, ingested {total_actions_ingested} actions (duplicates: {duplicates_found})")

            except Exception as e:
                print(f"Error processing bill {bill_id}: {e}")
                continue

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        print(f"Ingestion complete. Processed {bills_processed} bills, total actions: {total_actions_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--limit', type=int, default=None, help='Limit number of bills to process')
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--max_pages', type=int, default=999999)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_bill_actions(api_key=args.api_key, congress=args.congress, limit=args.limit, max_pages=args.max_pages)