"""Initialize the Postgres database by applying SQL migration files found in `mcp_server/sql/`.

Usage:
  export DATABASE_URL='postgresql://user:pass@host:5432/db'
  python mcp_server/db_init.py

Options:
  --files FILE1,FILE2   Comma-separated SQL files (relative to mcp_server/sql/) to apply in order
  --all                 Apply all SQL files in `mcp_server/sql/` in alphabetical order (default)
"""
import os
import argparse
import glob
import psycopg2


def apply_sql_file(conn, path: str):
    with open(path, "r", encoding="utf-8") as fh:
        sql = fh.read()
    with conn.cursor() as cur:
        cur.execute(sql)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--files", default=None, help="Comma-separated SQL filenames in mcp_server/sql/")
    p.add_argument("--all", action="store_true", help="Apply all SQL files in mcp_server/sql/")
    args = p.parse_args()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("Please set DATABASE_URL environment variable (e.g. export DATABASE_URL=postgresql://user:pass@host/db)")

    sql_dir = os.path.join(os.path.dirname(__file__), "sql")
    if args.files:
        files = [os.path.join(sql_dir, f.strip()) for f in args.files.split(",")]
    elif args.all or not args.files:
        files = sorted(glob.glob(os.path.join(sql_dir, "*.sql")))

    if not files:
        raise SystemExit("No SQL files found to apply")

    print("Applying SQL files:")
    for f in files:
        print(" -", f)

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    try:
        for f in files:
            print(f"Applying {f}...")
            apply_sql_file(conn, f)
        print("All migrations applied successfully.")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
