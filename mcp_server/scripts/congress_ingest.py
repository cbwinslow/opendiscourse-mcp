"""Congress.gov ingestion script: fetch bills via CongressClient and upsert into Postgres.

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
import pandas as pd

DB_URL = os.getenv("DATABASE_URL")

UPSERT_SQL = """
INSERT INTO congress_bills (id, congress, bill_type, bill_number, title, latest_action_date, latest_action_description, subjects, sponsors, raw, updated_on)
VALUES (%(id)s, %(congress)s, %(bill_type)s, %(bill_number)s, %(title)s, %(latest_action_date)s, %(latest_action_description)s, %(subjects)s, %(sponsors)s, %(raw)s, now())
ON CONFLICT (id) DO UPDATE SET
  congress = EXCLUDED.congress,
  bill_type = EXCLUDED.bill_type,
  bill_number = EXCLUDED.bill_number,
  title = EXCLUDED.title,
  latest_action_date = EXCLUDED.latest_action_date,
  latest_action_description = EXCLUDED.latest_action_description,
  subjects = EXCLUDED.subjects,
  sponsors = EXCLUDED.sponsors,
  raw = EXCLUDED.raw,
  updated_on = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_bill(congress: int, bill_obj: dict) -> dict:
    # The Congress API returns variable structures; we store raw JSON and pick some fields
    bill_id = f"{congress}:{bill_obj.get('billType')}:{bill_obj.get('billNumber')}"
    return {
        'id': bill_id,
        'congress': congress,
        'bill_type': bill_obj.get('billType'),
        'bill_number': bill_obj.get('billNumber'),
        'title': bill_obj.get('title'),
        'latest_action_date': bill_obj.get('latestActionDate'),
        'latest_action_description': bill_obj.get('latestActionDescription'),
        'subjects': bill_obj.get('subjects') or [],
        'sponsors': Json(bill_obj.get('sponsors') or {}),
        'raw': Json(bill_obj)
    }


def ingest_bills(api_key: str, congress: int = None, billType: str = None, page: int = 1):
    client = CongressClient(api_key=api_key)
    use_copy = bool(os.getenv('USE_COPY', '') )
    use_sqlalchemy = bool(os.getenv('USE_SQLALCHEMY', ''))

    conn = None
    if use_sqlalchemy:
        engine = get_sqlalchemy_engine()
    else:
        conn = connect_db(DB_URL)
        cur = conn.cursor()

    while True:
        res = client.search_bills(congress=congress, billType=billType, page=page)
        # Congress API may return different top-level structure; try to find list
        results = []
        if isinstance(res, dict):
            for k in ('bills', 'results', 'data'):
                if k in res and isinstance(res[k], list):
                    results = res[k]
                    break
        elif isinstance(res, list):
            results = res

        if not results:
            break

        df_rows = []
        for b in results:
            row = normalize_congress_bill(congress, b)
            if use_copy:
                df_rows.append({
                    'id': row['id'],
                    'congress': row['congress'],
                    'bill_type': row['bill_type'],
                    'bill_number': row['bill_number'],
                    'title': row['title'],
                    'latest_action_date': row['latest_action_date'],
                    'latest_action_description': row['latest_action_description']
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
                'id': 'id', 'congress': 'congress', 'bill_type': 'bill_type', 'bill_number': 'bill_number',
                'title': 'title', 'latest_action_date': 'latest_action_date', 'latest_action_description': 'latest_action_description'
            })
            raw_conn.close()

        if not use_sqlalchemy and not use_copy:
            conn.commit()

        if len(results) == 0:
            break
        page += 1

    if not use_sqlalchemy and not use_copy:
        cur.close()
        conn.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--billType', default=None)
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--page', type=int, default=1)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')
    ingest_bills(api_key=args.api_key, congress=args.congress, billType=args.billType, page=args.page)
