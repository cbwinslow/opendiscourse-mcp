"""Congress.gov summaries ingestion script: fetch bill summaries and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_summaries_ingest.py --congress 118
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
INSERT INTO congress_summaries (summary_id, bill_id, congress, bill_type, bill_number, bill_version, action_desc, action_date, text, as_of_date, update_date, categories, topics, raw, updated_on, last_api_update)
VALUES (%(summary_id)s, %(bill_id)s, %(congress)s, %(bill_type)s, %(bill_number)s, %(bill_version)s, %(action_desc)s, %(action_date)s, %(text)s, %(as_of_date)s, %(update_date)s, %(categories)s, %(topics)s, %(raw)s, now(), now())
ON CONFLICT (summary_id) DO UPDATE SET
  bill_id = EXCLUDED.bill_id,
  congress = EXCLUDED.congress,
  bill_type = EXCLUDED.bill_type,
  bill_number = EXCLUDED.bill_number,
  bill_version = EXCLUDED.bill_version,
  action_desc = EXCLUDED.action_desc,
  action_date = EXCLUDED.action_date,
  text = EXCLUDED.text,
  as_of_date = EXCLUDED.as_of_date,
  update_date = EXCLUDED.update_date,
  categories = EXCLUDED.categories,
  topics = EXCLUDED.topics,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_summary(summary_obj: dict) -> dict:
    """Normalize a congress summary object for database insertion."""
    # Extract bill information
    bill = summary_obj.get('bill', {})
    congress = bill.get('congress')
    bill_type = bill.get('type')
    bill_number = bill.get('number')
    bill_version = summary_obj.get('billVersion')

    # Create identifiers
    bill_id = f"{congress}:{bill_type}:{bill_number}" if congress and bill_type and bill_number else None
    summary_id = f"{congress}-{bill_type}{bill_number}-{bill_version}" if congress and bill_type and bill_number and bill_version else summary_obj.get('summaryId', '')

    return {
        'summary_id': summary_id,
        'bill_id': bill_id,
        'congress': congress,
        'bill_type': bill_type,
        'bill_number': bill_number,
        'bill_version': bill_version,
        'action_desc': summary_obj.get('actionDesc'),
        'action_date': summary_obj.get('actionDate'),
        'text': summary_obj.get('text'),
        'as_of_date': summary_obj.get('asOfDate'),
        'update_date': summary_obj.get('updateDate'),
        'categories': Json(summary_obj.get('categories', [])),
        'topics': Json(summary_obj.get('topics', [])),
        'raw': Json(summary_obj)
    }


def ingest_summaries(api_key: str, congress: int = None, max_pages: int = 999999):
    """Ingest bill summaries from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'summaries_{congress or "all"}',
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

        total_ingested = 0
        duplicates_found = 0
        page = 1

        while True:
            try:
                # Use the summaries endpoint
                url = f"{client.BASE}/summaries"
                params = {"page": page, "limit": 250}
                if congress:
                    params["congress"] = congress
                if client.api_key:
                    params["api_key"] = client.api_key

                response = client.session.get(url, params=params, timeout=client.timeout)
                response.raise_for_status()
                res = response.json()

                # Handle API response structure
                results = res.get('summaries', [])

                if not results:
                    break

                df_rows = []
                for summary in results:
                    row = normalize_congress_summary(summary)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_summaries', content_hash, row['summary_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'summary_id': row['summary_id'],
                            'bill_id': row['bill_id'],
                            'congress': row['congress'],
                            'bill_type': row['bill_type'],
                            'bill_number': row['bill_number'],
                            'bill_version': row['bill_version'],
                            'action_desc': row['action_desc'],
                            'action_date': row['action_date'],
                            'text': row['text'],
                            'as_of_date': row['as_of_date'],
                            'update_date': row['update_date']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_summaries', {
                        'summary_id': 'summary_id', 'bill_id': 'bill_id', 'congress': 'congress',
                        'bill_type': 'bill_type', 'bill_number': 'bill_number', 'bill_version': 'bill_version',
                        'action_desc': 'action_desc', 'action_date': 'action_date', 'text': 'text',
                        'as_of_date': 'as_of_date', 'update_date': 'update_date'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"Ingested {len(results)} summaries (total: {total_ingested}, duplicates: {duplicates_found})")

                # Check pagination
                pagination = res.get('pagination', {})
                if not pagination.get('next'):
                    break

                page += 1

            except Exception as e:
                print(f"Error on page {page}: {e}")
                break

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        print(f"Ingestion complete. Total summaries processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--max_pages', type=int, default=999999)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_summaries(api_key=args.api_key, congress=args.congress, max_pages=args.max_pages)