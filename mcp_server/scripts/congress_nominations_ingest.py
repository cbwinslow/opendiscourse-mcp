"""Congress.gov nominations ingestion script: fetch nominations and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_nominations_ingest.py --congress 118
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
INSERT INTO congress_nominations (nomination_id, congress, nomination_number, received_date, nominee_name, nominee_state, nominee_party, position_title, organization, committee_name, committee_code, current_status, current_status_date, current_status_description, confirmation_vote, cloture_vote, description, part_of_nominees, raw, updated_on, last_api_update)
VALUES (%(nomination_id)s, %(congress)s, %(nomination_number)s, %(received_date)s, %(nominee_name)s, %(nominee_state)s, %(nominee_party)s, %(position_title)s, %(organization)s, %(committee_name)s, %(committee_code)s, %(current_status)s, %(current_status_date)s, %(current_status_description)s, %(confirmation_vote)s, %(cloture_vote)s, %(description)s, %(part_of_nominees)s, %(raw)s, now(), now())
ON CONFLICT (nomination_id) DO UPDATE SET
  congress = EXCLUDED.congress,
  nomination_number = EXCLUDED.nomination_number,
  received_date = EXCLUDED.received_date,
  nominee_name = EXCLUDED.nominee_name,
  nominee_state = EXCLUDED.nominee_state,
  nominee_party = EXCLUDED.nominee_party,
  position_title = EXCLUDED.position_title,
  organization = EXCLUDED.organization,
  committee_name = EXCLUDED.committee_name,
  committee_code = EXCLUDED.committee_code,
  current_status = EXCLUDED.current_status,
  current_status_date = EXCLUDED.current_status_date,
  current_status_description = EXCLUDED.current_status_description,
  confirmation_vote = EXCLUDED.confirmation_vote,
  cloture_vote = EXCLUDED.cloture_vote,
  description = EXCLUDED.description,
  part_of_nominees = EXCLUDED.part_of_nominees,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_nomination(nomination_obj: dict) -> dict:
    """Normalize a congress nomination object for database insertion."""
    return {
        'nomination_id': nomination_obj.get('nominationId', ''),
        'congress': nomination_obj.get('congress'),
        'nomination_number': nomination_obj.get('nominationNumber'),
        'received_date': nomination_obj.get('receivedDate'),
        'nominee_name': nomination_obj.get('nomineeName'),
        'nominee_state': nomination_obj.get('nomineeState'),
        'nominee_party': nomination_obj.get('nomineeParty'),
        'position_title': nomination_obj.get('positionTitle'),
        'organization': nomination_obj.get('organization'),
        'committee_name': nomination_obj.get('committeeName'),
        'committee_code': nomination_obj.get('committeeCode'),
        'current_status': nomination_obj.get('currentStatus'),
        'current_status_date': nomination_obj.get('currentStatusDate'),
        'current_status_description': nomination_obj.get('currentStatusDescription'),
        'confirmation_vote': Json(nomination_obj.get('confirmationVote')),
        'cloture_vote': Json(nomination_obj.get('clotureVote')),
        'description': nomination_obj.get('description'),
        'part_of_nominees': Json(nomination_obj.get('partOfNominees', [])),
        'raw': Json(nomination_obj)
    }


def ingest_nominations(api_key: str, congress: int = None, max_pages: int = 10):
    """Ingest nominations from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'nominations_{congress or "all"}',
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

        while page <= max_pages:
            try:
                # Use the nomination endpoint
                url = f"{client.BASE}/nomination"
                params = {"page": page, "limit": 250}
                if congress:
                    params["congress"] = congress
                if client.api_key:
                    params["api_key"] = client.api_key

                response = client.session.get(url, params=params, timeout=client.timeout)
                response.raise_for_status()
                res = response.json()

                # Handle API response structure
                results = res.get('nominations', [])

                if not results:
                    break

                df_rows = []
                for nomination in results:
                    row = normalize_congress_nomination(nomination)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_nominations', content_hash, row['nomination_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'nomination_id': row['nomination_id'],
                            'congress': row['congress'],
                            'nomination_number': row['nomination_number'],
                            'received_date': row['received_date'],
                            'nominee_name': row['nominee_name'],
                            'nominee_state': row['nominee_state'],
                            'position_title': row['position_title'],
                            'current_status': row['current_status']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_nominations', {
                        'nomination_id': 'nomination_id', 'congress': 'congress', 'nomination_number': 'nomination_number',
                        'received_date': 'received_date', 'nominee_name': 'nominee_name', 'nominee_state': 'nominee_state',
                        'position_title': 'position_title', 'current_status': 'current_status'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"Ingested {len(results)} nominations (total: {total_ingested}, duplicates: {duplicates_found})")

                # Check pagination
                pagination = res.get('pagination', {})
                if not pagination.get('next') or page >= max_pages:
                    break

                page += 1

            except Exception as e:
                print(f"Error on page {page}: {e}")
                break

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        print(f"Ingestion complete. Total nominations processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--max_pages', type=int, default=10)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_nominations(api_key=args.api_key, congress=args.congress, max_pages=args.max_pages)