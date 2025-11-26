#!/usr/bin/env python3
"""
Script Name: congress_gov_unbounded_ingest.py
Author: ChatGPT for cbwinslow
Date: 2025-11-15

Summary:
    Ingest FULL datasets from Congress.gov v3 API collections with no
    artificial limits on pages or total records. The script follows
    the API's own pagination until there is no `next` link.

    You select a single collection ("table") or "all" via CLI.
    Each collection is written to an NDJSON file, and optionally also
    mirrored into a SQLite database (one table per collection).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
import time
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen

CONGRESS_BASE = "https://api.congress.gov/v3"
USER_AGENT = "OpenDiscourse-UnboundedIngest/1.0 (+https://cloudcurio.cc)"
API_PAGE_LIMIT = 250
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

ARGS: argparse.Namespace


def log(msg: str, level: str = "INFO") -> None:
    ts = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    print(f"[{ts}] {level}: {msg}", flush=True)


def dbg(msg: str) -> None:
    if getattr(ARGS, "verbose", False):
        log(msg, "DEBUG")


class Retryable(Exception):
    pass


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
        text = ""
        try:
            text = e.read().decode("utf-8", errors="ignore")
        except Exception:
            pass
        if e.code in (429, 500, 502, 503, 504):
            raise Retryable(f"HTTP {e.code} for {url}: {text[:200]}")
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
            log(f"Transient error ({attempt}/{retries}): {e}. Sleeping {sleep_for:.1f}s", "WARN")
            time.sleep(sleep_for)


def discover_collections() -> List[str]:
    try:
        root_url = build_url("/", {"format": "json"})
        data = fetch_with_retries(root_url, ARGS.retries, ARGS.timeout)
        found: List[str] = []
        for _, value in data.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        name = item.get("collection") or item.get("name")
                        if name:
                            found.append(str(name))
        if found:
            unique = sorted(set(found))
            dbg(f"Discovered collections from API root: {', '.join(unique)}")
            return unique
    except Exception as e:
        dbg(f"Collection discovery failed: {e!r}")
    log("Falling back to static collection list.", "WARN")
    return FALLBACK_COLLECTIONS


def extract_records(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
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


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def ndjson_path(outdir: str, collection: str) -> str:
    return os.path.join(outdir, f"{collection}.ndjson")


def append_ndjson(path: str, records: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\\n")
            count += 1
    return count


def sqlite_upsert(conn: sqlite3.Connection, table: str, record: Dict[str, Any]) -> None:
    table_name = table.replace("-", "_")
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {table_name} (id TEXT PRIMARY KEY, raw JSON)"
    )
    rec_id: Optional[str] = None
    for key in ("url", "itemId", "id", "number", "identifier"):
        if key in record:
            rec_id = str(record[key])
            break
    if rec_id is None:
        rec_id = str(hash(json.dumps(record, sort_keys=True)))
    conn.execute(
        f"INSERT OR REPLACE INTO {table_name} (id, raw) VALUES (?, ?)",
        (rec_id, json.dumps(record, ensure_ascii=False)),
    )


def ingest_collection(collection: str, since: Optional[str]) -> Dict[str, Any]:
    started = time.time()
    ensure_dir(ARGS.outdir)
    params: Dict[str, Any] = {"limit": API_PAGE_LIMIT}
    if since:
        params.update(
            {
                "fromDate": since,
                "fromDateTime": since,
                "from": since,
            }
        )
    url = build_url(f"/{collection}", params)
    nd_path = ndjson_path(ARGS.outdir, collection)
    conn: Optional[sqlite3.Connection] = None
    if ARGS.sqlite:
        conn = sqlite3.connect(ARGS.sqlite)
    total_items = 0
    total_pages = 0
    errors = 0
    while True:
        dbg(f"Requesting page {total_pages + 1} for collection '{collection}' → {url}")
        try:
            payload = fetch_with_retries(url, ARGS.retries, ARGS.timeout)
        except Exception as e:
            errors += 1
            log(f"Stopping ingestion for {collection} due to error: {e}", "ERROR")
            break
        records = extract_records(payload)
        total_items += append_ndjson(nd_path, records)
        if conn and records:
            for rec in records:
                sqlite_upsert(conn, collection, rec)
            conn.commit()
        total_pages += 1
        nxt = get_next_url(payload)
        if not nxt:
            dbg(f"No further pages for '{collection}'. Ingestion complete.")
            break
        url = nxt
        time.sleep(POLITE_SLEEP)
    if conn:
        conn.close()
    duration = round(time.time() - started, 2)
    return {
        "collection": collection,
        "items": total_items,
        "pages": total_pages,
        "errors": errors,
        "seconds": duration,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest FULL datasets from Congress.gov v3 collections without "
            "page-count limits (stops only when the API's pagination ends)."
        )
    )
    parser.add_argument(
        "--collection",
        required=True,
        help="Collection name (e.g., bills, members) or 'all' to ingest everything.",
    )
    parser.add_argument(
        "--outdir",
        default="./data/congress",
        help="Directory to write NDJSON files (default: ./data/congress)",
    )
    parser.add_argument(
        "--sqlite",
        default=None,
        help="Optional path to SQLite DB to mirror records (default: disabled)",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Optional ISO date (YYYY-MM-DD). Applied on a best-effort basis.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="HTTP timeout per request in seconds (default: 30)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Max retry attempts for transient errors (default: 5)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args()


def main() -> None:
    global ARGS
    ARGS = parse_args()
    if not os.getenv("CONGRESS_API_KEY"):
        log("Environment variable CONGRESS_API_KEY is required.", "ERROR")
        sys.exit(2)
    since: Optional[str] = None
    if ARGS.since:
        try:
            dt.date.fromisoformat(ARGS.since)
            since = ARGS.since
        except ValueError:
            log("--since must be in YYYY-MM-DD format.", "ERROR")
            sys.exit(2)
    if ARGS.collection.lower() == "all":
        collections = discover_collections()
    else:
        collections = [ARGS.collection]
    if not collections:
        log("No collections resolved for ingestion.", "ERROR")
        sys.exit(2)
    log(f"Starting unbounded ingestion for collections: {', '.join(collections)}")
    all_stats: List[Dict[str, Any]] = []
    for col in collections:
        log(f"→ Ingesting collection: {col}")
        try:
            stats = ingest_collection(col, since)
            all_stats.append(stats)
            log(
                f"✓ {col}: {stats['items']} items across {stats['pages']} pages "
                f"in {stats['seconds']}s (errors: {stats['errors']})"
            )
        except Exception as e:
            log(f"✗ Failed to ingest {col}: {e}", "ERROR")
    ensure_dir(ARGS.outdir)
    manifest = {
        "run_at": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "collections": collections,
        "stats": all_stats,
    }
    manifest_path = os.path.join(ARGS.outdir, "manifest_unbounded.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    log(f"Run complete. Manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
