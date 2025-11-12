"""Congress.gov committees ingestion script: fetch committees and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_committees_ingest.py --congress 118
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
INSERT INTO congress_committees (committee_code, chamber, committee_name, congress, committee_type, jurisdiction, parent_committee_code, chair, ranking_member, subcommittee_count, bills_reported, hearings_held, nominations_reported, subcommittees, current_members, establishment_date, abolition_date, raw, updated_on, last_api_update)
VALUES (%(committee_code)s, %(chamber)s, %(committee_name)s, %(congress)s, %(committee_type)s, %(jurisdiction)s, %(parent_committee_code)s, %(chair)s, %(ranking_member)s, %(subcommittee_count)s, %(bills_reported)s, %(hearings_held)s, %(nominations_reported)s, %(subcommittees)s, %(current_members)s, %(establishment_date)s, %(abolition_date)s, %(raw)s, now(), now())
ON CONFLICT (committee_code) DO UPDATE SET
  chamber = EXCLUDED.chamber,
  committee_name = EXCLUDED.committee_name,
  congress = EXCLUDED.congress,
  committee_type = EXCLUDED.committee_type,
  jurisdiction = EXCLUDED.jurisdiction,
  parent_committee_code = EXCLUDED.parent_committee_code,
  chair = EXCLUDED.chair,
  ranking_member = EXCLUDED.ranking_member,
  subcommittee_count = EXCLUDED.subcommittee_count,
  bills_reported = EXCLUDED.bills_reported,
  hearings_held = EXCLUDED.hearings_held,
  nominations_reported = EXCLUDED.nominations_reported,
  subcommittees = EXCLUDED.subcommittees,
  current_members = EXCLUDED.current_members,
  establishment_date = EXCLUDED.establishment_date,
  abolition_date = EXCLUDED.abolition_date,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_committee(committee_obj: dict) -> dict:
    """Normalize a congress committee object for database insertion."""
    # Extract committee information
    committee_code = committee_obj.get('systemCode', '')
    chamber = committee_obj.get('chamber')
    committee_name = committee_obj.get('name')
    congress = committee_obj.get('congress')
    committee_type = committee_obj.get('type')
    jurisdiction = committee_obj.get('jurisdiction')
    parent_committee_code = committee_obj.get('parentCommitteeCode')

    # Leadership
    chair = Json(committee_obj.get('chair'))
    ranking_member = Json(committee_obj.get('rankingMember'))

    # Activity counts
    subcommittee_count = committee_obj.get('subcommitteeCount', 0)
    bills_reported = Json(committee_obj.get('billsReported'))
    hearings_held = Json(committee_obj.get('hearingsHeld'))
    nominations_reported = Json(committee_obj.get('nominationsReported'))

    # Subcommittees and members
    subcommittees = Json(committee_obj.get('subcommittees', []))
    current_members = Json(committee_obj.get('currentMembers', []))

    # Historical dates
    establishment_date = committee_obj.get('establishmentDate')
    abolition_date = committee_obj.get('abolitionDate')

    return {
        'committee_code': committee_code,
        'chamber': chamber,
        'committee_name': committee_name,
        'congress': congress,
        'committee_type': committee_type,
        'jurisdiction': jurisdiction,
        'parent_committee_code': parent_committee_code,
        'chair': chair,
        'ranking_member': ranking_member,
        'subcommittee_count': subcommittee_count,
        'bills_reported': bills_reported,
        'hearings_held': hearings_held,
        'nominations_reported': nominations_reported,
        'subcommittees': subcommittees,
        'current_members': current_members,
        'establishment_date': establishment_date,
        'abolition_date': abolition_date,
        'raw': Json(committee_obj)
    }


def ingest_committees(api_key: str, congress: int = None, chamber: str = None, max_pages: int = 10):
    """Ingest committees from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'committees_{congress or "all"}_{chamber or "all"}',
        api_key=api_key[:8] + '...',
        congress=congress,
        chamber=chamber
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
                # Use the committees endpoint
                res = client.list_committees(congress=congress, chamber=chamber)

                # Handle API response structure
                results = res.get('committees', [])

                if not results:
                    break

                df_rows = []
                for committee in results:
                    row = normalize_congress_committee(committee)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_committees', content_hash, row['committee_code']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'committee_code': row['committee_code'],
                            'chamber': row['chamber'],
                            'committee_name': row['committee_name'],
                            'congress': row['congress'],
                            'committee_type': row['committee_type'],
                            'jurisdiction': row['jurisdiction'],
                            'parent_committee_code': row['parent_committee_code'],
                            'subcommittee_count': row['subcommittee_count']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_committees', {
                        'committee_code': 'committee_code', 'chamber': 'chamber',
                        'committee_name': 'committee_name', 'congress': 'congress',
                        'committee_type': 'committee_type', 'jurisdiction': 'jurisdiction',
                        'parent_committee_code': 'parent_committee_code', 'subcommittee_count': 'subcommittee_count'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"Ingested {len(results)} committees (total: {total_ingested}, duplicates: {duplicates_found})")

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

        print(f"Ingestion complete. Total committees processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--chamber', default=None, choices=['house', 'senate', 'joint'])
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--max_pages', type=int, default=10)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_committees(api_key=args.api_key, congress=args.congress, chamber=args.chamber, max_pages=args.max_pages)
