#!/usr/bin/env python3
"""Check database tables and status"""

import os
from dotenv import load_dotenv
from mcp_server.db import get_sqlalchemy_engine
from sqlalchemy import text

# Load environment variables from .env file
load_dotenv(dotenv_path='mcp_server/.env')

def main():
    try:
        engine = get_sqlalchemy_engine()
        with engine.connect() as conn:
            # Check congress tables
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name LIKE 'congress_%'
                ORDER BY table_name;
            """))
            congress_tables = [row[0] for row in result]
            print(f"Congress tables found: {congress_tables}")

            # Check if tables have data
            for table in congress_tables:
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table};"))
                count = count_result.fetchone()[0]
                print(f"{table}: {count} records")

    except Exception as e:
        print(f"Error connecting to database: {e}")

if __name__ == "__main__":
    main()
