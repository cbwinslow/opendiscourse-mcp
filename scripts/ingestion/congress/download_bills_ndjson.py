#!/usr/bin/env python3
"""
Download Congress.gov bills into NDJSON files for later DB loading.

- Uses CONGRESS_API_KEY from the environment.
- Paginates with offset/limit and writes each page to a single NDJSON file.
- Respects rate limits with configurable sleep and mild backoff on 429/5xx.
"""
import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse as up

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download Congress.gov bills to NDJSON.")
    parser.add_argument("--from-date", required=True, help="Filter results from this date (YYYY-MM-DD).")
    parser.add_argument("--offset", type=int, default=0, help="Starting offset for the first page.")
    parser.add_argument("--pages", type=int, default=10, help="Number of pages to fetch.")
    parser.add_argument("--limit", type=int, default=50, help="Records per page (max 250 per API).")
    parser.add_argument("--sleep", type=float, default=0.6, help="Seconds to sleep between pages.")
    parser.add_argument(
        "--output-dir",
        default="data/congress/ndjson/bills",
        help="Directory to store NDJSON and manifest files.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout per request (seconds).")
    parser.add_argument("--retries", type=int, default=3, help="Retry attempts for 429/5xx responses.")
    return parser.parse_args()


def ensure_output_paths(base_dir: pathlib.Path, offset: int, pages: int) -> tuple[pathlib.Path, pathlib.Path]:
    base_dir.mkdir(parents=True, exist_ok=True)
    ndjson_path = base_dir / f"bill_offset{offset}_p{pages}.ndjson"
    manifest_path = base_dir / f"bill_offset{offset}_p{pages}.manifest.json"
    return ndjson_path, manifest_path


def parse_next_offset(next_url: str, fallback: int, limit: int) -> int:
    if not next_url:
        return fallback + limit
    qs = dict(up.parse_qsl(up.urlparse(next_url).query))
    try:
        return int(qs.get("offset", fallback + limit))
    except Exception:
        return fallback + limit


def fetch_page(api_key: str, from_date: str, offset: int, limit: int, timeout: int, retries: int) -> dict:
    url = "https://api.congress.gov/v3/bill"
    params = {
        "fromDate": from_date,
        "limit": limit,
        "offset": offset,
        "format": "json",
        "api_key": api_key,
    }
    backoff = 1.0
    attempt = 0
    while True:
        attempt += 1
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code in (429, 500, 502, 503, 504):
            if attempt > retries:
                resp.raise_for_status()
            time.sleep(backoff)
            backoff *= 2
            continue
        resp.raise_for_status()
        return resp.json()


def write_manifest(path: pathlib.Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> int:
    args = parse_args()
    api_key = os.getenv("CONGRESS_API_KEY")
    if not api_key:
        print("CONGRESS_API_KEY is required in the environment.", file=sys.stderr)
        return 1

    out_dir = pathlib.Path(args.output_dir)
    ndjson_path, manifest_path = ensure_output_paths(out_dir, args.offset, args.pages)

    stats = {
        "from_date": args.from_date,
        "start_offset": args.offset,
        "limit": args.limit,
        "pages_requested": args.pages,
        "pages_fetched": 0,
        "records": 0,
        "status": "in_progress",
        "errors": [],
        "ndjson_path": str(ndjson_path),
    }

    current_offset = args.offset
    try:
        with ndjson_path.open("w", encoding="utf-8") as out:
            for _ in range(args.pages):
                payload = fetch_page(
                    api_key=api_key,
                    from_date=args.from_date,
                    offset=current_offset,
                    limit=args.limit,
                    timeout=args.timeout,
                    retries=args.retries,
                )
                bills = payload.get("bills") or []
                for bill in bills:
                    out.write(json.dumps(bill))
                    out.write("\n")
                stats["records"] += len(bills)
                stats["pages_fetched"] += 1

                next_url = (payload.get("pagination") or {}).get("next")
                if not next_url:
                    break
                current_offset = parse_next_offset(next_url, current_offset, args.limit)
                time.sleep(args.sleep)

        stats["status"] = "completed"
    except Exception as exc:  # pragma: no cover - network/FS
        stats["status"] = "failed"
        stats["errors"].append(str(exc))

    write_manifest(manifest_path, stats)
    if stats["status"] != "completed":
        return 1
    print(
        f"✅ wrote {stats['records']} records across {stats['pages_fetched']} pages "
        f"from offset {args.offset} → {ndjson_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
