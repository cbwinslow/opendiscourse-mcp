#!/usr/bin/env python3
"""
Script Name: congress_gov_pg_ingest.py
Author: ChatGPT for cbwinslow
Date: 2025-11-15 (upgraded)

Summary:
    Unbounded ingestion from Congress.gov v3 collections directly into PostgreSQL,
    with incremental sync support via a watermark table, plus optional NDJSON mirror.

    - Follows API pagination until there is no `next` link.
    - Stores each record as a JSONB row in a per-collection table.
    - Maintains a per-collection watermark of the latest record date seen.
    - Can run in:
        * full         : always ingest from the beginning (best-effort date filters)
        * incremental  : only ingest records newer than the stored watermark date

Inputs:
    - Environment:
        * CONGRESS_API_KEY        (required)
        * CONGRESS_PG_DSN         (optional DSN, e.g. postgresql://user:pass@host:5432/db)
          OR standard libpq vars: PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE

    - CLI:
        * --collection   : name (bills, members, ...) or "all"
        * --mode         : full | incremental
        * --outdir       : NDJSON output directory (can be disabled with --no-file)
        * --pg-schema    : PostgreSQL schema for tables (default: public)
        * --since        : optional YYYY-MM-DD hard floor (in addition to watermark)
        * --timeout      : HTTP timeout
        * --retries      : transient error retries
        * --no-file      : do not write NDJSON files
        * --verbose      : debug logging

Outputs:
    - PostgreSQL tables:
        * <schema>.<collection> with columns:
            id          TEXT PRIMARY KEY
            raw         JSONB
            ingested_at TIMESTAMPTZ DEFAULT now()

    - Watermark table:
        * <schema>.congress_ingest_watermark
            collection       TEXT PRIMARY KEY
            last_record_date DATE
            last_run_at      TIMESTAMPTZ DEFAULT now()

    - Optional NDJSON:
        * <outdir>/<collection>.ndjson
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen

import psycopg2
import psycopg2.extras

# ==============================
# Constants / Defaults
# ==============================
CONGRESS_BASE = "https://api.congress.gov/v3"
USER_AGENT = "OpenDiscourse-PGIngest/1.1 (+https://cloudcurio.cc)"
API_PAGE_LIMIT = 250  # Max allowed per API docs
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 5
POLITE_SLEEP = 0.25

FALLBACK_COLLECTIONS = [
    "bills",
    "amendments",
    "summaries",
    "congress",
    "members",
    "committees",
    "committee-reports",
    "committee-prints",
    "committee-meetings",
    "house-communication",
    "senate-communication",
    "nominations",
    "treaties",
    "congressional-record",
    "daily-congressional-record",
    "laws",
]

WATERMARK_TABLE_NAME = "congress_ingest_watermark"

ARGS: argparse.Namespace  # set in main()


# ==============================
# Logging helpers
# ==============================

def log(msg: str, level: str = "INFO") -> None:
    ts = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print(f"[{ts}] {level}: {msg}", flush=True)


def dbg(msg: str) -> None:
    if getattr(ARGS, "verbose", False):
        log(msg, "DEBUG")


class Retryable(Exception):
    """Signals a transient HTTP/network error worth retrying."""


# ==============================
# HTTP utilities
# ==============================

def build_url(path: str, params: Dict[str, Any]) -> str:
    api_key = os.getenv("CONGRESS_API_KEY")
    if not api_key:
        log("CONGRESS_API_KEY is not set in the environment.", "ERROR")
        sys.exit(2)

    qs = {k: v for k, v in params.items() if v not in (None, "")}
    qs.setdefault("format", "json")
    qs.setdefault("limit", API_PAGE_LIMIT)
    qs["api_key"] = api_key

    return f"{CONGRESS_BASE}{path}?{urlencode(qs)}"


def http_fetch(url: str, timeout: int) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except HTTPError as e:
        snippet = ""
        try:
            snippet = e.read().decode("utf-8", errors="ignore")[:200]
        except Exception:
            pass
        if e.code in (429, 500, 502, 503, 504):
            raise Retryable(f"HTTP {e.code} for {url}: {snippet}")
        raise
    except URLError as e:
        raise Retryable(f"URLError for {url}: {e.reason}")


def fetch_with_retries(url: str, retries: int, timeout: int) -> Dict[str, Any]:
    attempt = 0
    backoff = 1.0
    while True:
        try:
            return http_fetch(url, timeout=timeout)
        except Retryable as e:
            attempt += 1
            if attempt > retries:
                log(f"Giving up after {attempt - 1} retries: {e}", "ERROR")
                raise
            sleep_for = backoff * (2 ** (attempt - 1))
            log(
                f"Transient error ({attempt}/{retries}): {e}. Sleeping {sleep_for:.1f}s",
                "WARN",
            )
            time.sleep(sleep_for)


# ==============================
# Discovery & pagination
# ==============================

def discover_collections() -> List[str]:
    """Try to discover collections from API root. Fallback to static list."""
    try:
        root_url = build_url("/", {"format": "json"})
        data = fetch_with_retries(root_url, ARGS.retries, ARGS.timeout)
        found: List[str] = []
        for value in data.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        name = item.get("collection") or item.get("name")
                        if name:
                            found.append(str(name))
        if found:
            unique = sorted(set(found))
            dbg("Discovered collections: " + ", ".join(unique))
            return unique
    except Exception as e:
        dbg(f"Collection discovery failed: {e!r}")

    log("Falling back to static collection list.", "WARN")
    return FALLBACK_COLLECTIONS


def extract_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Heuristic: find the primary list of records in a collection response."""
    for value in payload.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value  # type: ignore[return-value]
    for value in payload.values():
        if isinstance(value, dict):
            for sub in value.values():
                if isinstance(sub, list) and sub and isinstance(sub[0], dict):
                    return sub  # type: ignore[return-value]
    return []


def get_next_url(payload: Dict[str, Any]) -> Optional[str]:
    pag = payload.get("pagination") or payload.get("Pagination") or {}
    nxt = pag.get("next") or pag.get("nextUrl")
    if not nxt:
        return None

    parsed = urlparse(nxt)
    qs = parse_qs(parsed.query)
    api_key = os.getenv("CONGRESS_API_KEY", "")
    if api_key and "api_key" not in qs:
        sep = "&" if parsed.query else "?"
        nxt = f"{nxt}{sep}api_key={api_key}"
    if "format" not in qs:
        sep = "&" if urlparse(nxt).query else "?"
        nxt = f"{nxt}{sep}format=json"
    if "limit" not in qs:
        sep = "&" if urlparse(nxt).query else "?"
        nxt = f"{nxt}{sep}limit={API_PAGE_LIMIT}"
    return nxt


# ==============================
# Date extraction / watermark helper
# ==============================
CANDIDATE_DATE_KEYS = [
    "updateDate",
    "updateDateTime",
    "lastModified",
    "lastModifiedDateTime",
    "latestActionDate",
    "actionDate",
    "date",
    "introducedDate",
    "receivedDate",
]


def extract_record_date(rec: Dict[str, Any]) -> Optional[dt.date]:
    """"""
    Try to pull a reasonable 'record date' from common fields.
    Returns a date or None if nothing parseable found.
    """"""
    for key in CANDIDATE_DATE_KEYS:
        if key in rec:
            raw_val = rec.get(key)
            if not isinstance(raw_val, str):
                continue
            txt = raw_val.strip()
            if not txt:
                continue
            # If there's a time part, split on 'T'
            if "T" in txt:
                txt = txt.split("T", 1)[0]
            try:
                return dt.date.fromisoformat(txt)
            except ValueError:
                continue
    return None


# ==============================
# PostgreSQL sink
# ==============================


class PgSink:
    """
    PostgreSQL sink that:
      - Opens a connection (using DSN or libpq env)
      - Ensures per-collection tables exist
      - Maintains a watermark table per schema
      - Upserts rows with a JSONB `raw` column
    """

    def __init__(self, dsn: Optional[str], schema: str = "public") -> None:
        self.schema = schema
        if dsn:
            self.conn = psycopg2.connect(dsn)
        else:
            # psycopg2 will use PG* environment variables if DSN is empty
            self.conn = psycopg2.connect("")
        self.conn.autocommit = False
        self._ensure_schema()
        self._ensure_watermark_table()

    def _ensure_schema(self) -> None:
        # Basic safety: restrict schema name to alphanumerics + underscore
        if not self.schema.replace("_", "").isalnum():
            raise ValueError(f"Unsafe schema name: {self.schema!r}")
        with self.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema};")
        self.conn.commit()

    def _ensure_watermark_table(self) -> None:
        table_name = self._wm_table_name()
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    collection       TEXT PRIMARY KEY,
                    last_record_date DATE,
                    last_run_at      TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
        self.conn.commit()

    def _wm_table_name(self) -> str:
        return f"{self.schema}.{WATERMARK_TABLE_NAME}"

    def ensure_table(self, collection: str) -> None:
        table_name = self._table_name(collection)
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id          TEXT PRIMARY KEY,
                    raw         JSONB NOT NULL,
                    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
        self.conn.commit()

    def _table_name(self, collection: str) -> str:
        safe = collection.replace("-", "_")
        return f"{self.schema}.{safe}"

    def upsert_batch(self, collection: str, records: List[Dict[str, Any]]) -> int:
        if not records:
            return 0
        self.ensure_table(collection)
        table_name = self._table_name(collection)

        # Determine a stable id field if possible
        def rec_id(rec: Dict[str, Any]) -> str:
            for key in ("url", "itemId", "id", "number", "identifier"):
                if key in rec:
                    return str(rec[key])
            return str(hash(json.dumps(rec, sort_keys=True)))

        rows = [(rec_id(r), psycopg2.extras.Json(r)) for r in records]

        with self.conn.cursor() as cur:
            psycopg2.extras.execute_batch(
                cur,
                f"""
                INSERT INTO {table_name} (id, raw)
                VALUES (%s, %s)
                ON CONFLICT (id) DO UPDATE
                SET raw = EXCLUDED.raw,
                    ingested_at = now();
                """,
                rows,
                page_size=100,
            )
        self.conn.commit()
        return len(rows)

    # ---- Watermark helpers ----
    def get_watermark(self, collection: str) -> Optional[dt.date]:
        table_name = self._wm_table_name()
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT last_record_date FROM {table_name} WHERE collection = %s;",
                (collection,),
            )
            row = cur.fetchone()
        if not row:
            return None
        value = row[0]
        if isinstance(value, dt.date):
            return value
        return None

    def update_watermark(
        self, collection: str, last_record_date: Optional[dt.date]
    ) -> None:
        table_name = self._wm_table_name()
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {table_name} (collection, last_record_date, last_run_at)
                VALUES (%s, %s, now())
                ON CONFLICT (collection) DO UPDATE
                SET last_record_date = EXCLUDED.last_record_date,
                    last_run_at      = now();
                """,
                (collection, last_record_date),
            )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.commit()
        finally:
            self.conn.close()


# ==============================
# NDJSON helpers
# ==============================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def ndjson_path(outdir: str, collection: str) -> str:
    return os.path.join(outdir, f"{collection}.ndjson")


def append_ndjson(path: str, records: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


# ==============================
# Core ingestion
# ==============================

def ingest_collection(
    collection: str,
    since: Optional[dt.date],
    pg: PgSink,
    write_files: bool,
) -> Dict[str, Any]:
    """"""
    Ingest ONE collection until there are no further pages.

    `since` is a date floor (combined from CLI --since and watermark).
    It is mapped into a few common query parameters (fromDate, fromDateTime, from).
    """"""
    started = time.time()
    if write_files:
        ensure_dir(ARGS.outdir)
        nd_path = ndjson_path(ARGS.outdir, collection)
    else:
        nd_path = ""

    params: Dict[str, Any] = {"limit": API_PAGE_LIMIT}
    if since:
        since_str = since.isoformat()
        params.update(
            {
                "fromDate": since_str,
                "fromDateTime": since_str,
                "from": since_str,
            }
        )

    url = build_url(f"/{collection}", params)

    total_items = 0
    total_pages = 0
    errors = 0
    max_record_date: Optional[dt.date] = None

    while True:
        dbg(f"Requesting page {total_pages + 1} for '{collection}' → {url}")
        try:
            payload = fetch_with_retries(url, ARGS.retries, ARGS.timeout)
        except Exception as e:
            errors += 1
            log(f"Stopping ingestion for {collection} due to error: {e}", "ERROR")
            break

        records = extract_records(payload)
        if not isinstance(records, list):
            records = []

        # Track max record date
        for rec in records:
            d = extract_record_date(rec)
            if d:
                if max_record_date is None or d > max_record_date:
                    max_record_date = d

        # Write to PostgreSQL
        inserted = pg.upsert_batch(collection, records)
        total_items += inserted

        # Optional NDJSON mirror
        if write_files and records:
            append_ndjson(nd_path, records)

        total_pages += 1
        nxt = get_next_url(payload)
        if not nxt:
            dbg(f"No further pages for '{collection}'. Ingestion complete.")
            break

        url = nxt
        time.sleep(POLITE_SLEEP)

    # Update watermark with the best date we saw (if any)
    if max_record_date is not None:
        pg.update_watermark(collection, max_record_date)
    else:
        # Still update run time but leave last_record_date unchanged
        pg.update_watermark(collection, None)

    duration = round(time.time() - started, 2)
    stats = {
        "collection": collection,
        "items": total_items,
        "pages": total_pages,
        "errors": errors,
        "seconds": duration,
        "max_record_date": max_record_date.isoformat() if max_record_date else None,
    }
    return stats


# ==============================
# CLI / main
# ==============================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest FULL datasets from Congress.gov v3 collections "
            "directly into PostgreSQL (JSONB), with incremental watermarking."
        )
    )
    parser.add_argument(
        "--collection",
        required=True,
        help="Collection name (e.g., bills, members) or 'all' to ingest everything.",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="Ingestion mode: 'full' (ignore watermark) or 'incremental' (use watermark).",
    )
    parser.add_argument(
        "--outdir",
        default="./data/congress",
        help="Directory for NDJSON output (default: ./data/congress).",
    )
    parser.add_argument(
        "--pg-dsn",
        default=os.getenv("CONGRESS_PG_DSN", ""),
        help=(
            "PostgreSQL DSN (overrides libpq env vars). "
            "Default: use CONGRESS_PG_DSN or PG* environment."
        ),
    )
    parser.add_argument(
        "--pg-schema",
        default="public",
        help="PostgreSQL schema for tables (default: public).",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Optional ISO date (YYYY-MM-DD). Acts as a hard lower bound.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout per request in seconds (default: 30).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Max retry attempts for transient errors (default: 5).",
    )
    parser.add_argument(
        "--no-file",
        action="store_true",
        help="Disable NDJSON file output (PostgreSQL only).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def main() -> None:
    global ARGS
    ARGS = parse_args()  # type: ignore[assignment]

    if not os.getenv("CONGRESS_API_KEY"):
        log("Environment variable CONGRESS_API_KEY is required.", "ERROR")
        sys.exit(2)

    # Validate since date if provided (CLI)
    cli_since: Optional[dt.date] = None
    if ARGS.since:
        try:
            cli_since = dt.date.fromisoformat(ARGS.since)
        except ValueError:
            log("--since must be in YYYY-MM-DD format.", "ERROR")
            sys.exit(2)

    # Connect to PostgreSQL
    try:
        pg = PgSink(ARGS.pg_dsn, schema=ARGS.pg_schema)
    except Exception as e:
        log(f"Failed to connect to PostgreSQL: {e}", "ERROR")
        sys.exit(3)

    # Resolve collections
    if ARGS.collection.lower() == "all":
        collections = discover_collections()
    else:
        collections = [ARGS.collection]

    if not collections:
        log("No collections resolved for ingestion.", "ERROR")
        sys.exit(2)

    log(
        "Starting PostgreSQL-backed ingestion (mode="
        + ARGS.mode
        + ") for collections: "
        + ", ".join(collections)
    )

    write_files = not ARGS.no_file
    if write_files:
        ensure_dir(ARGS.outdir)

    all_stats: List[Dict[str, Any]] = []
    try:
        for col in collections:
            # Resolve effective 'since' based on mode
            effective_since: Optional[dt.date] = cli_since
            if ARGS.mode == "incremental":
                wm = pg.get_watermark(col)
                if wm and cli_since:
                    effective_since = max(wm, cli_since)
                elif wm:
                    effective_since = wm
                # if no watermark, fall back to cli_since (which may be None -> full)
            log(
                f"→ Ingesting collection: {col} "
                f"(effective since: {effective_since.isoformat() if effective_since else 'None'})"
            )
            try:
                stats = ingest_collection(col, effective_since, pg, write_files)
                all_stats.append(stats)
                log(
                    f"✓ {col}: {stats['items']} items across {stats['pages']} pages "
                    f"in {stats['seconds']}s (errors: {stats['errors']}, "
                    f"max_record_date={stats['max_record_date']})"
                )
            except Exception as e:
                log(f"✗ Failed to ingest {col}: {e}", "ERROR")
    finally:
        pg.close()

    # Write manifest file if NDJSON is enabled
    if write_files:
        manifest = {
            "run_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "mode": ARGS.mode,
            "collections": collections,
            "stats": all_stats,
        }
        manifest_path = os.path.join(ARGS.outdir, "manifest_pg_ingest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        log(f"Run complete. Manifest written to {manifest_path}")
    else:
        log("Run complete. NDJSON output disabled (--no-file).")


if __name__ == "__main__":
    main()
