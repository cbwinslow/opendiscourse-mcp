#!/usr/bin/env python3
"""
Generate an offset/page plan for downloading Congress.gov bills.

- Pulls pagination.count from the API using CONGRESS_API_KEY.
- Outputs a plan file with lines: offset=<start> pages=<pages_per_job>
- Helps schedule NDJSON batches without manual math.
"""
import argparse
import math
import os
import pathlib
import sys
from typing import List

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate bill download plan.")
    parser.add_argument("--from-date", required=True, help="Date filter (YYYY-MM-DD).")
    parser.add_argument("--limit", type=int, default=50, help="Records per page (max 250).")
    parser.add_argument("--pages-per-job", type=int, default=20, help="Pages each job should fetch.")
    parser.add_argument(
        "--plan-path",
        default="data/congress/plan/bill_plan.txt",
        help="Where to write the plan file.",
    )
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout (seconds).")
    return parser.parse_args()


def fetch_total_count(api_key: str, from_date: str, limit: int, timeout: int) -> int:
    url = "https://api.congress.gov/v3/bill"
    params = {"fromDate": from_date, "limit": 1, "format": "json", "api_key": api_key}
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    pagination = resp.json().get("pagination") or {}
    return int(pagination.get("count", 0))


def build_offsets(total: int, limit: int, pages_per_job: int) -> List[int]:
    step = limit * pages_per_job
    jobs = math.ceil(total / step) if step else 0
    return [i * step for i in range(jobs)]


def main() -> int:
    args = parse_args()
    api_key = os.getenv("CONGRESS_API_KEY")
    if not api_key:
        print("CONGRESS_API_KEY is required in the environment.", file=sys.stderr)
        return 1

    total = fetch_total_count(api_key, args.from_date, args.limit, args.timeout)
    offsets = build_offsets(total, args.limit, args.pages_per_job)

    plan_path = pathlib.Path(args.plan_path)
    plan_path.parent.mkdir(parents=True, exist_ok=True)

    with plan_path.open("w", encoding="utf-8") as f:
        f.write(f"# Bill download plan generated from count={total}, limit={args.limit}, pages/job={args.pages_per_job}\n")
        for off in offsets:
            f.write(f"offset={off} pages={args.pages_per_job}\n")

    print(f"✅ Wrote {len(offsets)} jobs to {plan_path} (total_count={total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
