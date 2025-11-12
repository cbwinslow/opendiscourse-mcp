"""GovInfo ingestion script: list bulk files and ingest XML to Postgres.

Usage:
  export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
  python mcp_server/scripts/govinfo_ingest.py --collection BILLS --year 2025 --download_dir ./data
"""
import os
import argparse
import psycopg2
from psycopg2.extras import Json
from mcp_server.clients.govinfo_client import GovInfoClient
from mcp_server.db import get_sqlalchemy_engine, get_raw_connection
from mcp_server.utils.db_copy import copy_dataframe_to_table
from mcp_server.utils.monitoring import monitor, deduplicator
import pandas as pd

DB_URL = os.getenv("DATABASE_URL")

UPSERT_SQL = """
INSERT INTO govinfo_documents (id, collection, date, title, url, metadata, raw, created_on)
VALUES (%(id)s, %(collection)s, %(date)s, %(title)s, %(url)s, %(metadata)s, %(raw)s, now())
ON CONFLICT (id) DO UPDATE SET
  collection = EXCLUDED.collection,
  date = EXCLUDED.date,
  title = EXCLUDED.title,
  url = EXCLUDED.url,
  metadata = EXCLUDED.metadata,
  raw = EXCLUDED.raw;
"""


def connect_db(url: str):
    return psycopg2.connect(url)


def ingest_collection(api_key: str, collection: str, year: int = None, download_dir: str = './data'):
    # Create monitoring job
    job_id = monitor.create_job(
        source='govinfo',
        collection=f'{collection}_{year or "all"}',
        api_key=api_key[:8] + '...',  # Partial key for logging
        collection=collection,
        year=year,
        download_dir=download_dir
    )

    with monitor.monitor_job(job_id):
        client = GovInfoClient(api_key=api_key)
        listing = client.bulk_download(collection, year=year)
        files = listing.get('files') or []
        os.makedirs(download_dir, exist_ok=True)

        conn = connect_db(DB_URL)
        cur = conn.cursor()
        use_copy = bool(os.getenv('USE_COPY', ''))
        use_sqlalchemy = bool(os.getenv('USE_SQLALCHEMY', ''))
        engine = None
        if use_sqlalchemy:
            engine = get_sqlalchemy_engine()

        total_ingested = 0
        duplicates_found = 0

        for f in files:
            fn = os.path.basename(f)
            out_path = os.path.join(download_dir, fn)
            client.fetch_bulk_file(f, out_path)
            try:
                df = client.ingest_xml_to_df(out_path)
            except Exception as e:
                print(f"Failed to process {fn}: {e}")
                continue

            if df.empty:
                continue

            if use_copy:
                # Attempt to map a few common columns
                df_local = df.copy()
                # best-effort mapping
                df_local['id'] = df_local.get('id') if 'id' in df_local.columns else df_local.index.astype(str)
                df_local['collection'] = collection
                df_local['date'] = df_local.get('date') if 'date' in df_local.columns else None
                df_local['title'] = df_local.get('title') if 'title' in df_local.columns else None
                cols_map = {'id': 'id', 'collection': 'collection', 'date': 'date', 'title': 'title'}
                raw_conn = get_raw_connection()
                copy_dataframe_to_table(raw_conn, df_local, 'govinfo_documents', cols_map)
                raw_conn.close()
                total_ingested += len(df_local)
            elif use_sqlalchemy and engine is not None:
                with engine.begin() as connection:
                    for _, row in df.iterrows():
                        doc_id = str(row.get('id') or row.get('documentId') or os.path.splitext(fn)[0])

                        # Check for duplicates using content hashing
                        content_data = {
                            'collection': collection,
                            'date': row.get('date') or None,
                            'title': row.get('title') or None,
                            'url': f,
                            'metadata': row.to_dict()
                        }
                        content_hash = deduplicator.get_content_hash(content_data)
                        if deduplicator.is_duplicate('govinfo_documents', content_hash, doc_id):
                            duplicates_found += 1
                            continue

                        rec = {
                            'id': doc_id,
                            'collection': collection,
                            'date': row.get('date') or None,
                            'title': row.get('title') or None,
                            'url': f,
                            'metadata': Json(row.to_dict()),
                            'raw': Json(row.to_dict())
                        }
                        connection.execute(UPSERT_SQL, rec)
                        total_ingested += 1
            else:
                for _, row in df.iterrows():
                    doc_id = str(row.get('id') or row.get('documentId') or os.path.splitext(fn)[0])

                    # Check for duplicates using content hashing
                    content_data = {
                        'collection': collection,
                        'date': row.get('date') or None,
                        'title': row.get('title') or None,
                        'url': f,
                        'metadata': row.to_dict()
                    }
                    content_hash = deduplicator.get_content_hash(content_data)
                    if deduplicator.is_duplicate('govinfo_documents', content_hash, doc_id):
                        duplicates_found += 1
                        continue

                    rec = {
                        'id': doc_id,
                        'collection': collection,
                        'date': row.get('date') or None,
                        'title': row.get('title') or None,
                        'url': f,
                        'metadata': Json(row.to_dict()),
                        'raw': Json(row.to_dict())
                    }
                    cur.execute(UPSERT_SQL, rec)
                    total_ingested += 1
                conn.commit()

            monitor.update_progress(job_id, total_ingested, duplicates_found)
            print(f"Processed {fn}: {len(df)} records (total: {total_ingested}, duplicates: {duplicates_found})")

        cur.close()
        conn.close()

        print(f"Ingestion complete. Total documents processed: {total_ingested}, duplicates found: {duplicates_found}")


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--collection', required=True)
    p.add_argument('--year', type=int, default=None)
    p.add_argument('--download_dir', default='./data')
    p.add_argument('--api_key', default=os.getenv('GOVINFO_API_KEY'))
    args = p.parse_args()

    if not DB_URL:
        raise SystemExit('Please set DATABASE_URL')
    if not args.api_key:
        raise SystemExit('Please set GOVINFO_API_KEY or pass --api_key')

    ingest_collection(api_key=args.api_key, collection=args.collection, year=args.year, download_dir=args.download_dir)
