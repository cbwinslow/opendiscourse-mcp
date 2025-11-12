"""Congress.gov treaties ingestion script: fetch treaties and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_treaties_ingest.py --congress 118
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
INSERT INTO congress_treaties (treaty_id, congress, treaty_number, title, suffix, receiving_chamber, receiving_chamber_calendar, transmission_date, referral_date, referral_chamber, committee_referral, resolution_text, resolution_date, actions, committee_reports, current_status, current_status_date, current_status_description, raw, updated_on, last_api_update)
VALUES (%(treaty_id)s, %(congress)s, %(treaty_number)s, %(title)s, %(suffix)s, %(receiving_chamber)s, %(receiving_chamber_calendar)s, %(transmission_date)s, %(referral_date)s, %(referral_chamber)s, %(committee_referral)s, %(resolution_text)s, %(resolution_date)s, %(actions)s, %(committee_reports)s, %(current_status)s, %(current_status_date)s, %(current_status_description)s, %(raw)s, now(), now())
ON CONFLICT (treaty_id) DO UPDATE SET
  congress = EXCLUDED.congress,
  treaty_number = EXCLUDED.treaty_number,
  title = EXCLUDED.title,
  suffix = EXCLUDED.suffix,
  receiving_chamber = EXCLUDED.receiving_chamber,
  receiving_chamber_calendar = EXCLUDED.receiving_chamber_calendar,
  transmission_date = EXCLUDED.transmission_date,
  referral_date = EXCLUDED.referral_date,
  referral_chamber = EXCLUDED.referral_chamber,
  committee_referral = EXCLUDED.committee_referral,
  resolution_text = EXCLUDED.resolution_text,
  resolution_date = EXCLUDED.resolution_date,
  actions = EXCLUDED.actions,
  committee_reports = EXCLUDED.committee_reports,
  current_status = EXCLUDED.current_status,
  current_status_date = EXCLUDED.current_status_date,
  current_status_description = EXCLUDED.current_status_description,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_treaty(treaty_obj: dict) -> dict:
    """Normalize a congress treaty object for database insertion."""
    return {
        'treaty_id': treaty_obj.get('treatyId', ''),
        'congress': treaty_obj.get('congress'),
        'treaty_number': treaty_obj.get('treatyNumber'),
        'title': treaty_obj.get('title'),
        'suffix': treaty_obj.get('suffix'),
        'receiving_chamber': treaty_obj.get('receivingChamber'),
        'receiving_chamber_calendar': treaty_obj.get('receivingChamberCalendar'),
        'transmission_date': treaty_obj.get('transmissionDate'),
        'referral_date': treaty_obj.get('referralDate'),
        'referral_chamber': treaty_obj.get('referralChamber'),
        'committee_referral': Json(treaty_obj.get('committeeReferral')),
        'resolution_text': treaty_obj.get('resolutionText'),
        'resolution_date': treaty_obj.get('resolutionDate'),
        'actions': Json(treaty_obj.get('actions', [])),
        'committee_reports': Json(treaty_obj.get('committeeReports', [])),
        'current_status': treaty_obj.get('currentStatus'),
        'current_status_date': treaty_obj.get('currentStatusDate'),
        'current_status_description': treaty_obj.get('currentStatusDescription'),
        'raw': Json(treaty_obj)
    }


def ingest_treaties(api_key: str, congress: int = None, max_pages: int = 10):
    """Ingest treaties from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'treaties_{congress or "all"}',
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
                # Use the treaty endpoint
                url = f"{client.BASE}/treaty"
                params = {"page": page, "limit": 250}
                if congress:
                    params["congress"] = congress
                if client.api_key:
                    params["api_key"] = client.api_key

                response = client.session.get(url, params=params, timeout=client.timeout)
                response.raise_for_status()
                res = response.json()

                # Handle API response structure
                results = res.get('treaties', [])

                if not results:
                    break

                df_rows = []
                for treaty in results:
                    row = normalize_congress_treaty(treaty)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_treaties', content_hash, row['treaty_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'treaty_id': row['treaty_id'],
                            'congress': row['congress'],
                            'treaty_number': row['treaty_number'],
                            'title': row['title'],
                            'suffix': row['suffix'],
                            'receiving_chamber': row['receiving_chamber'],
                            'transmission_date': row['transmission_date'],
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
                    copy_dataframe_to_table(raw_conn, df, 'congress_treaties', {
                        'treaty_id': 'treaty_id', 'congress': 'congress', 'treaty_number': 'treaty_number',
                        'title': 'title', 'suffix': 'suffix', 'receiving_chamber': 'receiving_chamber',
                        'transmission_date': 'transmission_date', 'current_status': 'current_status'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"Ingested {len(results)} treaties (total: {total_ingested}, duplicates: {duplicates_found})")

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

        print(f"Ingestion complete. Total treaties processed: {total_ingested}, duplicates found: {duplicates_found}")


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

    ingest_treaties(api_key=args.api_key, congress=args.congress, max_pages=args.max_pages)