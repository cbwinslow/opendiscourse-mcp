"""Congress.gov congress information ingestion script: fetch congress metadata and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_congress_ingest.py --congress 118
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
INSERT INTO congress_congress (congress_id, congress_number, start_date, end_date, sessions, house_leadership, senate_leadership, committee_chairs, bills_introduced, bills_enacted, nominations_received, nominations_confirmed, major_legislation, raw, updated_on, last_api_update)
VALUES (%(congress_id)s, %(congress_number)s, %(start_date)s, %(end_date)s, %(sessions)s, %(house_leadership)s, %(senate_leadership)s, %(committee_chairs)s, %(bills_introduced)s, %(bills_enacted)s, %(nominations_received)s, %(nominations_confirmed)s, %(major_legislation)s, %(raw)s, now(), now())
ON CONFLICT (congress_id) DO UPDATE SET
  congress_number = EXCLUDED.congress_number,
  start_date = EXCLUDED.start_date,
  end_date = EXCLUDED.end_date,
  sessions = EXCLUDED.sessions,
  house_leadership = EXCLUDED.house_leadership,
  senate_leadership = EXCLUDED.senate_leadership,
  committee_chairs = EXCLUDED.committee_chairs,
  bills_introduced = EXCLUDED.bills_introduced,
  bills_enacted = EXCLUDED.bills_enacted,
  nominations_received = EXCLUDED.nominations_received,
  nominations_confirmed = EXCLUDED.nominations_confirmed,
  major_legislation = EXCLUDED.major_legislation,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_info(congress_obj: dict) -> dict:
    """Normalize a congress information object for database insertion."""
    return {
        'congress_id': congress_obj.get('congress'),
        'congress_number': congress_obj.get('congress'),
        'start_date': congress_obj.get('startDate'),
        'end_date': congress_obj.get('endDate'),
        'sessions': Json(congress_obj.get('sessions', [])),
        'house_leadership': Json(congress_obj.get('houseLeadership', [])),
        'senate_leadership': Json(congress_obj.get('senateLeadership', [])),
        'committee_chairs': Json(congress_obj.get('committeeChairs', [])),
        'bills_introduced': congress_obj.get('billsIntroduced'),
        'bills_enacted': congress_obj.get('billsEnacted'),
        'nominations_received': congress_obj.get('nominationsReceived'),
        'nominations_confirmed': congress_obj.get('nominationsConfirmed'),
        'major_legislation': Json(congress_obj.get('majorLegislation', [])),
        'raw': Json(congress_obj)
    }


def ingest_congress_info(api_key: str, congress: int = None):
    """Ingest congress information from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'congress_info_{congress or "all"}',
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

        try:
            # Use the congress endpoint
            if congress:
                url = f"{client.BASE}/congress/{congress}"
            else:
                url = f"{client.BASE}/congress"

            params = {}
            if client.api_key:
                params["api_key"] = client.api_key

            response = client.session.get(url, params=params, timeout=client.timeout)
            response.raise_for_status()
            res = response.json()

            # Handle API response structure
            if congress:
                # Single congress response
                results = [res]
            else:
                # Multiple congresses response
                results = res.get('congresses', [])

            df_rows = []
            for congress_info in results:
                row = normalize_congress_info(congress_info)

                # Check for duplicates using content hashing
                content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                if deduplicator.is_duplicate('congress_congress', content_hash, str(row['congress_id'])):
                    duplicates_found += 1
                    continue

                if use_copy:
                    df_rows.append({
                        'congress_id': row['congress_id'],
                        'congress_number': row['congress_number'],
                        'start_date': row['start_date'],
                        'end_date': row['end_date'],
                        'bills_introduced': row['bills_introduced'],
                        'bills_enacted': row['bills_enacted'],
                        'nominations_received': row['nominations_received'],
                        'nominations_confirmed': row['nominations_confirmed']
                    })
                elif use_sqlalchemy:
                    with engine.begin() as connection:
                        connection.execute(UPSERT_SQL, row)
                else:
                    cur.execute(UPSERT_SQL, row)

            if use_copy and df_rows:
                df = pd.DataFrame(df_rows)
                raw_conn = get_raw_connection()
                copy_dataframe_to_table(raw_conn, df, 'congress_congress', {
                    'congress_id': 'congress_id', 'congress_number': 'congress_number',
                    'start_date': 'start_date', 'end_date': 'end_date',
                    'bills_introduced': 'bills_introduced', 'bills_enacted': 'bills_enacted',
                    'nominations_received': 'nominations_received', 'nominations_confirmed': 'nominations_confirmed'
                })
                raw_conn.close()

            if not use_sqlalchemy and not use_copy:
                conn.commit()

            total_ingested = len(results)
            monitor.update_progress(job_id, total_ingested, duplicates_found)
            print(f"Ingested {total_ingested} congress records, duplicates found: {duplicates_found}")

        except Exception as e:
            print(f"Error: {e}")

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        print(f"Ingestion complete. Total congress records processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_congress_info(api_key=args.api_key, congress=args.congress)