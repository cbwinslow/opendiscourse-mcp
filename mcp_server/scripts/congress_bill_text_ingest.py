"""Congress.gov bill text ingestion script: fetch bill text and upsert into Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/congress_bill_text_ingest.py --congress 118
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
INSERT INTO congress_bill_text (text_id, bill_id, text_type, text_format, date_issued, congress, bill_type, bill_number, bill_version, full_text, extracted_text, file_path, file_size, mime_type, processing_status, processing_attempts, last_processing_attempt, created_on, updated_on)
VALUES (%(text_id)s, %(bill_id)s, %(text_type)s, %(text_format)s, %(date_issued)s, %(congress)s, %(bill_type)s, %(bill_number)s, %(bill_version)s, %(full_text)s, %(extracted_text)s, %(file_path)s, %(file_size)s, %(mime_type)s, %(processing_status)s, %(processing_attempts)s, %(last_processing_attempt)s, now(), now())
ON CONFLICT (text_id) DO UPDATE SET
  bill_id = EXCLUDED.bill_id,
  text_type = EXCLUDED.text_type,
  text_format = EXCLUDED.text_format,
  date_issued = EXCLUDED.date_issued,
  congress = EXCLUDED.congress,
  bill_type = EXCLUDED.bill_type,
  bill_number = EXCLUDED.bill_number,
  bill_version = EXCLUDED.bill_version,
  full_text = EXCLUDED.full_text,
  extracted_text = EXCLUDED.extracted_text,
  file_path = EXCLUDED.file_path,
  file_size = EXCLUDED.file_size,
  mime_type = EXCLUDED.mime_type,
  processing_status = EXCLUDED.processing_status,
  processing_attempts = EXCLUDED.processing_attempts,
  last_processing_attempt = EXCLUDED.last_processing_attempt,
  updated_on = now();
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def normalize_congress_bill_text(bill_id: str, text_obj: dict) -> dict:
    """Normalize a congress bill text object for database insertion."""
    # Create text ID
    text_type = text_obj.get('type')
    text_format = text_obj.get('format')
    bill_version = text_obj.get('version', 'original')
    text_id = f"{bill_id}_{text_type}_{text_format}_{bill_version}"

    # Extract bill information from the text object
    congress = text_obj.get('congress')
    bill_type = text_obj.get('billType')
    bill_number = text_obj.get('billNumber')
    bill_version = text_obj.get('version', 'original')

    # Text metadata
    date_issued = text_obj.get('dateIssued')
    text_type = text_obj.get('type')
    text_format = text_obj.get('format')

    # Content (if available directly)
    full_text = text_obj.get('text')  # Direct text content if available
    extracted_text = None  # Would be populated by OCR processing

    # File information
    file_path = text_obj.get('url')  # URL to the text file
    file_size = None  # Would be populated when downloading
    mime_type = text_obj.get('format', '').lower()
    if mime_type == 'xml':
        mime_type = 'application/xml'
    elif mime_type == 'html':
        mime_type = 'text/html'
    elif mime_type == 'pdf':
        mime_type = 'application/pdf'
    else:
        mime_type = f'text/{mime_type}' if mime_type else None

    # Processing status
    processing_status = 'pending'  # pending, processing, completed, failed
    processing_attempts = 0
    last_processing_attempt = None

    return {
        'text_id': text_id,
        'bill_id': bill_id,
        'text_type': text_type,
        'text_format': text_format,
        'date_issued': date_issued,
        'congress': congress,
        'bill_type': bill_type,
        'bill_number': bill_number,
        'bill_version': bill_version,
        'full_text': full_text,
        'extracted_text': extracted_text,
        'file_path': file_path,
        'file_size': file_size,
        'mime_type': mime_type,
        'processing_status': processing_status,
        'processing_attempts': processing_attempts,
        'last_processing_attempt': last_processing_attempt
    }


def get_bills_to_process(congress: int = None, limit: int = None):
    """Get bills that need text processing."""
    engine = get_sqlalchemy_engine()

    query = "SELECT bill_id, congress, bill_type, bill_number FROM congress_bills WHERE 1=1"
    params = {}

    if congress:
        query += " AND congress = %(congress)s"
        params["congress"] = congress

    query += " ORDER BY congress DESC, bill_number DESC"

    if limit:
        query += f" LIMIT {limit}"

    with engine.connect() as conn:
        result = conn.execute(query, params)
        bills = result.fetchall()

    return bills


def ingest_bill_text(api_key: str, congress: int = None, limit: int = None, max_pages: int = 999999):
    """Ingest bill text from Congress API."""
    # Create monitoring job
    job_id = monitor.create_job(
        source='congress',
        collection=f'bill_text_{congress or "all"}',
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

        # Get bills to process
        bills = get_bills_to_process(congress=congress, limit=limit)
        print(f"Processing text for {len(bills)} bills")

        total_texts_ingested = 0
        duplicates_found = 0
        bills_processed = 0

        for bill_row in bills:
            bill_id, bill_congress, bill_type, bill_number = bill_row
            bills_processed += 1

            try:
                # Get text for this bill
                res = client.get_bill_text(bill_congress, bill_type.lower(), bill_number)

                # Handle API response structure
                texts = res.get('textVersions', [])

                if not texts:
                    continue

                df_rows = []
                for text_version in texts:
                    row = normalize_congress_bill_text(bill_id, text_version)

                    # Check for duplicates using content hashing
                    content_hash = deduplicator.get_content_hash(row, exclude_fields=['full_text', 'extracted_text'])
                    if deduplicator.is_duplicate('congress_bill_text', content_hash, row['text_id']):
                        duplicates_found += 1
                        continue

                    if use_copy:
                        df_rows.append({
                            'text_id': row['text_id'],
                            'bill_id': row['bill_id'],
                            'text_type': row['text_type'],
                            'text_format': row['text_format'],
                            'date_issued': row['date_issued'],
                            'congress': row['congress'],
                            'bill_type': row['bill_type'],
                            'bill_number': row['bill_number'],
                            'bill_version': row['bill_version'],
                            'file_path': row['file_path'],
                            'mime_type': row['mime_type'],
                            'processing_status': row['processing_status']
                        })
                    elif use_sqlalchemy:
                        with engine.begin() as connection:
                            connection.execute(UPSERT_SQL, row)
                    else:
                        cur.execute(UPSERT_SQL, row)

                if use_copy and df_rows:
                    df = pd.DataFrame(df_rows)
                    raw_conn = get_raw_connection()
                    copy_dataframe_to_table(raw_conn, df, 'congress_bill_text', {
                        'text_id': 'text_id', 'bill_id': 'bill_id', 'text_type': 'text_type',
                        'text_format': 'text_format', 'date_issued': 'date_issued', 'congress': 'congress',
                        'bill_type': 'bill_type', 'bill_number': 'bill_number', 'bill_version': 'bill_version',
                        'file_path': 'file_path', 'mime_type': 'mime_type', 'processing_status': 'processing_status'
                    })
                    raw_conn.close()

                if not use_sqlalchemy and not use_copy:
                    conn.commit()

                total_texts_ingested += len(texts)
                monitor.update_progress(job_id, total_texts_ingested, duplicates_found)

                if bills_processed % 50 == 0:
                    print(f"Processed {bills_processed} bills, ingested {total_texts_ingested} text versions (duplicates: {duplicates_found})")

            except Exception as e:
                print(f"Error processing bill {bill_id}: {e}")
                continue

        if not use_sqlalchemy and not use_copy:
            cur.close()
            conn.close()

        print(f"Ingestion complete. Processed {bills_processed} bills, total text versions: {total_texts_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--congress', type=int, default=None)
    p.add_argument('--limit', type=int, default=None, help='Limit number of bills to process')
    p.add_argument('--api_key', default=os.getenv('CONGRESS_API_KEY'))
    p.add_argument('--max_pages', type=int, default=999999)
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set CONGRESS_API_KEY or pass --api_key')

    ingest_bill_text(api_key=args.api_key, congress=args.congress, limit=args.limit, max_pages=args.max_pages)