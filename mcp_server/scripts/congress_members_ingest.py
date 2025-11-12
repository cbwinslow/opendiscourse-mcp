"""Congress.gov members ingestion script: fetch members and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_members_ingest.py --congress 118
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
INSERT INTO congress_members (bioguide_id, direct_order_name, inverted_order_name, honorific_name, first_name, last_name, birth_year, party_name, party_history, state, district, current_member, terms, previous_names, depiction, sponsored_legislation, cosponsored_legislation, leadership_positions, committee_assignments, voting_record, raw, updated_on, last_api_update)
VALUES (%(bioguide_id)s, %(direct_order_name)s, %(inverted_order_name)s, %(honorific_name)s, %(first_name)s, %(last_name)s, %(birth_year)s, %(party_name)s, %(party_history)s, %(state)s, %(district)s, %(current_member)s, %(terms)s, %(previous_names)s, %(depiction)s, %(sponsored_legislation)s, %(cosponsored_legislation)s, %(leadership_positions)s, %(committee_assignments)s, %(voting_record)s, %(raw)s, now(), now())
ON CONFLICT (bioguide_id) DO UPDATE SET
  direct_order_name = EXCLUDED.direct_order_name,
  inverted_order_name = EXCLUDED.inverted_order_name,
  honorific_name = EXCLUDED.honorific_name,
  first_name = EXCLUDED.first_name,
  last_name = EXCLUDED.last_name,
  birth_year = EXCLUDED.birth_year,
  party_name = EXCLUDED.party_name,
  party_history = EXCLUDED.party_history,
  state = EXCLUDED.state,
  district = EXCLUDED.district,
  current_member = EXCLUDED.current_member,
  terms = EXCLUDED.terms,
  previous_names = EXCLUDED.previous_names,
  depiction = EXCLUDED.depiction,
  sponsored_legislation = EXCLUDED.sponsored_legislation,
  cosponsored_legislation = EXCLUDED.cosponsored_legislation,
  leadership_positions = EXCLUDED.leadership_positions,
  committee_assignments = EXCLUDED.committee_assignments,
  voting_record = EXCLUDED.voting_record,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_member(member_obj: dict) -> dict:
    """Normalize a congress member object for database insertion."""
    # Extract member information
    bioguide_id = member_obj.get('bioguideId')
    direct_order_name = member_obj.get('directOrderName')
    inverted_order_name = member_obj.get('invertedOrderName')
    honorific_name = member_obj.get('honorificName')

    # Name components
    first_name = member_obj.get('firstName')
    last_name = member_obj.get('lastName')
    birth_year = member_obj.get('birthYear')

    # Political information
    party_name = member_obj.get('partyName')
    party_history = Json(member_obj.get('partyHistory', []))
    state = member_obj.get('state')
    district = member_obj.get('district')

    # Current status
    current_member = member_obj.get('currentMember', False)

    # Terms in office
    terms = Json(member_obj.get('terms', []))

    # Previous names
    previous_names = Json(member_obj.get('previousNames', []))

    # Depiction/image
    depiction = Json(member_obj.get('depiction'))

    # Legislative activity
    sponsored_legislation = Json(member_obj.get('sponsoredLegislation'))
    cosponsored_legislation = Json(member_obj.get('cosponsoredLegislation'))

    # Leadership positions
    leadership_positions = Json(member_obj.get('leadershipPositions', []))

    # Committee assignments
    committee_assignments = Json(member_obj.get('committeeAssignments', []))

    # Voting record (aggregated)
    voting_record = Json(member_obj.get('votingRecord'))

    return {
        'bioguide_id': bioguide_id,
        'direct_order_name': direct_order_name,
        'inverted_order_name': inverted_order_name,
        'honorific_name': honorific_name,
        'first_name': first_name,
        'last_name': last_name,
        'birth_year': birth_year,
        'party_name': party_name,
        'party_history': party_history,
        'state': state,
        'district': district,
        'current_member': current_member,
        'terms': terms,
        'previous_names': previous_names,
        'depiction': depiction,
        'sponsored_legislation': sponsored_legislation,
        'cosponsored_legislation': cosponsored_legislation,
        'leadership_positions': leadership_positions,
        'committee_assignments': committee_assignments,
        'voting_record': voting_record,
        'raw': Json(member_obj)
    }


def ingest_members(api_key: str, congress: int = None, chamber: str = None, current_member: bool = None, max_pages: int = 10):
    """Ingest members from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'members_{congress or "all"}_{chamber or "all"}_{current_member or "all"}',
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
                # Use the members endpoint
                res = client.list_members(congress=congress, chamber=chamber)

                # Handle API response structure
                results = res.get('members', [])

                if not results:
                    break

                df_rows = []
                for member in results:
                    # Filter by current member status if specified
                    if current_member is not None:
                        if member.get('currentMember', False) != current_member:
                            continue

                    row = normalize_congress_member(member)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_members', content_hash, row['bioguide_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'bioguide_id': row['bioguide_id'],
                            'direct_order_name': row['direct_order_name'],
                            'inverted_order_name': row['inverted_order_name'],
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'party_name': row['party_name'],
                            'state': row['state'],
                            'district': row['district'],
                            'current_member': row['current_member']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_members', {
                        'bioguide_id': 'bioguide_id', 'direct_order_name': 'direct_order_name',
                        'inverted_order_name': 'inverted_order_name', 'first_name': 'first_name',
                        'last_name': 'last_name', 'party_name': 'party_name', 'state': 'state',
                        'district': 'district', 'current_member': 'current_member'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"Ingested {len(results)} members (total: {total_ingested}, duplicates: {duplicates_found})")

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

        print(f"Ingestion complete. Total members processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--chamber', default=None, choices=['house', 'senate'])
    p.add_argument('--current_member', action='store_true', help='Only ingest current members')
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--max_pages', type=int, default=10)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_members(api_key=args.api_key, congress=args.congress, chamber=args.chamber, current_member=args.current_member, max_pages=args.max_pages)