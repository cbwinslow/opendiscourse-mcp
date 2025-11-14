"""Congress.gov hearings ingestion script: fetch committee hearings and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_hearings_ingest.py --congress 118
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
INSERT INTO congress_hearings (hearing_id, congress, chamber, committee_code, committee_name, subcommittee_name, hearing_title, hearing_date, hearing_type, location, room, video_url, transcript_url, witnesses, topics, related_bills, documents, status, raw, updated_on, last_api_update)
VALUES (%(hearing_id)s, %(congress)s, %(chamber)s, %(committee_code)s, %(committee_name)s, %(subcommittee_name)s, %(hearing_title)s, %(hearing_date)s, %(hearing_type)s, %(location)s, %(room)s, %(video_url)s, %(transcript_url)s, %(witnesses)s, %(topics)s, %(related_bills)s, %(documents)s, %(status)s, %(raw)s, now(), now())
ON CONFLICT (hearing_id) DO UPDATE SET
  congress = EXCLUDED.congress,
  chamber = EXCLUDED.chamber,
  committee_code = EXCLUDED.committee_code,
  committee_name = EXCLUDED.committee_name,
  subcommittee_name = EXCLUDED.subcommittee_name,
  hearing_title = EXCLUDED.hearing_title,
  hearing_date = EXCLUDED.hearing_date,
  hearing_type = EXCLUDED.hearing_type,
  location = EXCLUDED.location,
  room = EXCLUDED.room,
  video_url = EXCLUDED.video_url,
  transcript_url = EXCLUDED.transcript_url,
  witnesses = EXCLUDED.witnesses,
  topics = EXCLUDED.topics,
  related_bills = EXCLUDED.related_bills,
  documents = EXCLUDED.documents,
  status = EXCLUDED.status,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_hearing(hearing_obj: dict) -> dict:
    """Normalize a congress hearing object for database insertion."""
    return {
        'hearing_id': hearing_obj.get('hearingId', ''),
        'congress': hearing_obj.get('congress'),
        'chamber': hearing_obj.get('chamber'),
        'committee_code': hearing_obj.get('committeeCode'),
        'committee_name': hearing_obj.get('committeeName'),
        'subcommittee_name': hearing_obj.get('subcommitteeName'),
        'hearing_title': hearing_obj.get('hearingTitle'),
        'hearing_date': hearing_obj.get('hearingDate'),
        'hearing_type': hearing_obj.get('hearingType'),
        'location': hearing_obj.get('location'),
        'room': hearing_obj.get('room'),
        'video_url': hearing_obj.get('videoUrl'),
        'transcript_url': hearing_obj.get('transcriptUrl'),
        'witnesses': Json(hearing_obj.get('witnesses', [])),
        'topics': Json(hearing_obj.get('topics', [])),
        'related_bills': Json(hearing_obj.get('relatedBills', [])),
        'documents': Json(hearing_obj.get('documents', [])),
        'status': hearing_obj.get('status'),
        'raw': Json(hearing_obj)
    }


def ingest_hearings(api_key: str, congress: int = None, max_pages: int = 999999):
    """Ingest committee hearings from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'hearings_{congress or "all"}',
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
                # Use the hearing endpoint
                url = f"{client.BASE}/hearing"
                params = {"page": page, "limit": 250}
                if congress:
                    params["congress"] = congress
                if client.api_key:
                    params["api_key"] = client.api_key

                response = client.session.get(url, params=params, timeout=client.timeout)
                response.raise_for_status()
                res = response.json()

                # Handle API response structure
                results = res.get('hearings', [])

                if not results:
                    break

                df_rows = []
                for hearing in results:
                    row = normalize_congress_hearing(hearing)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_hearings', content_hash, row['hearing_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'hearing_id': row['hearing_id'],
                            'congress': row['congress'],
                            'chamber': row['chamber'],
                            'committee_code': row['committee_code'],
                            'committee_name': row['committee_name'],
                            'hearing_title': row['hearing_title'],
                            'hearing_date': row['hearing_date'],
                            'hearing_type': row['hearing_type'],
                            'status': row['status']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_hearings', {
                        'hearing_id': 'hearing_id', 'congress': 'congress', 'chamber': 'chamber',
                        'committee_code': 'committee_code', 'committee_name': 'committee_name',
                        'hearing_title': 'hearing_title', 'hearing_date': 'hearing_date',
                        'hearing_type': 'hearing_type', 'status': 'status'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"Ingested {len(results)} hearings (total: {total_ingested}, duplicates: {duplicates_found})")

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

        print(f"Ingestion complete. Total hearings processed: {total_ingested}, duplicates found: {duplicates_found}")


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

    ingest_hearings(api_key=args.api_key, congress=args.congress, max_pages=args.max_pages)