"""Congress.gov votes ingestion script: fetch roll call votes and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_votes_ingest.py --congress 118
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
INSERT INTO congress_votes (vote_id, congress, session, chamber, roll_number, vote_date, vote_time, question, description, vote_type, result, total_yes, total_no, total_present, total_not_voting, tie_breaker, document, member_votes, amendments, raw, updated_on, last_api_update)
VALUES (%(vote_id)s, %(congress)s, %(session)s, %(chamber)s, %(roll_number)s, %(vote_date)s, %(vote_time)s, %(question)s, %(description)s, %(vote_type)s, %(result)s, %(total_yes)s, %(total_no)s, %(total_present)s, %(total_not_voting)s, %(tie_breaker)s, %(document)s, %(member_votes)s, %(amendments)s, %(raw)s, now(), now())
ON CONFLICT (vote_id) DO UPDATE SET
  congress = EXCLUDED.congress,
  session = EXCLUDED.session,
  chamber = EXCLUDED.chamber,
  roll_number = EXCLUDED.roll_number,
  vote_date = EXCLUDED.vote_date,
  vote_time = EXCLUDED.vote_time,
  question = EXCLUDED.question,
  description = EXCLUDED.description,
  vote_type = EXCLUDED.vote_type,
  result = EXCLUDED.result,
  total_yes = EXCLUDED.total_yes,
  total_no = EXCLUDED.total_no,
  total_present = EXCLUDED.total_present,
  total_not_voting = EXCLUDED.total_not_voting,
  tie_breaker = EXCLUDED.tie_breaker,
  document = EXCLUDED.document,
  member_votes = EXCLUDED.member_votes,
  amendments = EXCLUDED.amendments,
  raw = EXCLUDED.raw,
  updated_on = now(),
  last_api_update = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_vote(vote_obj: dict) -> dict:
    """Normalize a congress vote object for database insertion."""
    # Extract vote information
    vote_id = vote_obj.get('voteId', '')
    congress = vote_obj.get('congress')
    session = vote_obj.get('session')
    chamber = vote_obj.get('chamber')
    roll_number = vote_obj.get('rollNumber')
    vote_date = vote_obj.get('date')
    vote_time = vote_obj.get('time')

    # Vote details
    question = vote_obj.get('question')
    description = vote_obj.get('description')
    vote_type = vote_obj.get('type')
    result = vote_obj.get('result')

    # Vote counts
    total_yes = vote_obj.get('total', {}).get('yes', 0)
    total_no = vote_obj.get('total', {}).get('no', 0)
    total_present = vote_obj.get('total', {}).get('present', 0)
    total_not_voting = vote_obj.get('total', {}).get('notVoting', 0)

    return {
        'vote_id': vote_id,
        'congress': congress,
        'session': session,
        'chamber': chamber,
        'roll_number': roll_number,
        'vote_date': vote_date,
        'vote_time': vote_time,
        'question': question,
        'description': description,
        'vote_type': vote_type,
        'result': result,
        'total_yes': total_yes,
        'total_no': total_no,
        'total_present': total_present,
        'total_not_voting': total_not_voting,
        'tie_breaker': Json(vote_obj.get('tieBreaker')),
        'document': Json(vote_obj.get('document')),
        'member_votes': Json(vote_obj.get('memberVotes')),
        'amendments': Json(vote_obj.get('amendments')),
        'raw': Json(vote_obj)
    }


def ingest_votes(api_key: str, congress: int = None, chamber: str = None, date: str = None, max_pages: int = 999999):
    """Ingest roll call votes from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'votes_{congress or "all"}_{chamber or "all"}',
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

        while True:
            try:
                # Use the votes endpoint
                res = client.list_votes(congress=congress, chamber=chamber, date=date)

                # Handle API response structure
                results = res.get('votes', [])

                if not results:
                    break

                df_rows = []
                for vote in results:
                    row = normalize_congress_vote(vote)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['raw'])
                    if deduplicator.is_duplicate('congress_votes', content_hash, row['vote_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'vote_id': row['vote_id'],
                            'congress': row['congress'],
                            'session': row['session'],
                            'chamber': row['chamber'],
                            'roll_number': row['roll_number'],
                            'vote_date': row['vote_date'],
                            'vote_time': row['vote_time'],
                            'question': row['question'],
                            'description': row['description'],
                            'vote_type': row['vote_type'],
                            'result': row['result'],
                            'total_yes': row['total_yes'],
                            'total_no': row['total_no'],
                            'total_present': row['total_present'],
                            'total_not_voting': row['total_not_voting']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_votes', {
                        'vote_id': 'vote_id', 'congress': 'congress', 'session': 'session',
                        'chamber': 'chamber', 'roll_number': 'roll_number', 'vote_date': 'vote_date',
                        'vote_time': 'vote_time', 'question': 'question', 'description': 'description',
                        'vote_type': 'vote_type', 'result': 'result', 'total_yes': 'total_yes',
                        'total_no': 'total_no', 'total_present': 'total_present', 'total_not_voting': 'total_not_voting'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_ingested += len(results)
                monitor.update_progress(job_id, total_ingested, duplicates_found)
                print(f"Ingested {len(results)} votes (total: {total_ingested}, duplicates: {duplicates_found})")

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

        print(f"Ingestion complete. Total votes processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--chamber', default=None, choices=['house', 'senate'])
    p.add_argument('--date', default=None, help='Date in YYYY-MM-DD format')
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--max_pages', type=int, default=999999)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_votes(api_key=args.api_key, congress=args.congress, chamber=args.chamber, date=args.date, max_pages=args.max_pages)
