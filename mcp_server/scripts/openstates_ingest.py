"""OpenStates ingestion script: fetch bills and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/openstates_ingest.py --jurisdiction nc --per_page 50
"""
import os
import argparse
import json
import psycopg2
from psycopg2.extras import Json
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection
from mcp_server.utils.db_copy import copy_dataframe_to_table
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
    return {
        'id': bill.get('id'),
        'session': bill.get('session'),
        'jurisdiction': bill.get('jurisdiction', {}).get('id') if isinstance(bill.get('jurisdiction'), dict) else bill.get('jurisdiction'),
        'identifier': bill.get('identifier'),
        'title': bill.get('title'),
        'classification': bill.get('classification') or [],
        'subject': bill.get('subject') or [],
        'created_at': bill.get('created_at'),
        'updated_at': bill.get('updated_at'),
        'first_action_date': bill.get('first_action_date') or None,
        'latest_action_date': bill.get('latest_action_date') or None,
        'latest_action_description': bill.get('latest_action_description'),
        'openstates_url': bill.get('openstates_url'),
        'raw': Json(bill)
    }


def ingest_bills(api_key: str, jurisdiction: str = None, q: str = None, page: int = 1, per_page: int = 50):
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

    while True:
        res = client.search_bills(jurisdiction=jurisdiction, q=q, page=page, per_page=per_page)
        results = res.get('results') or res.get('data') or res.get('results', [])
        if not results:
            break

        df_rows = []
        for b in results:
            row = normalize_bill(b)
            if use_copy:
                df_rows.append({
                    'id': row['id'],
                    'session': row['session'],
                    'jurisdiction': row['jurisdiction'],
                    'identifier': row['identifier'],
                    'title': row['title'],
                    'classification': '{' + ','.join(row['classification']) + '}' if row['classification'] else None,
                    'subjects': '{' + ','.join(row['subject']) + '}' if row['subject'] else None,
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

        if len(results) < per_page:
            break
        page += 1

    if not use_sqlalchemy and not use_copy:
        cur.close()
        conn.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--jurisdiction', default=None)
    p.add_argument('--q', default=None)
    p.add_argument('--api_key', default=os.getenv('OPENSTATES_API_KEY'))
    p.add_argument('--page', type=int, default=1)
    p.add_argument('--per_page', type=int, default=50)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set OPENSTATES_API_KEY or pass --api_key')
    ingest_bills(api_key=args.api_key, jurisdiction=args.jurisdiction, q=args.q, page=args.page, per_page=args.per_page)
