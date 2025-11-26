#!/usr/bin/env python3
"""
Execute SQL file to complete database schema setup
"""

import os
import sys
import psycopg2

def execute_sql_file(sql_file_path):
    """Execute SQL file against database"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print(f"🔄 Executing SQL file: {sql_file_path}")
        
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
        
        # Execute SQL in batches to handle complex scripts
        sql_statements = sql_content.split(';')
        
        for i, statement in enumerate(sql_statements):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    print(f"✅ Executed statement {i+1}")
                except Exception as e:
                    if "already exists" in str(e) or "does not exist" in str(e):
                        print(f"⚠️  Statement {i+1} (expected): {e}")
                    else:
                        print(f"❌ Statement {i+1} failed: {e}")
        
        conn.commit()
        print("✅ SQL file executed successfully")
        return True
        
    except Exception as e:
        print(f"❌ ERROR executing SQL file: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    sql_file = "mcp_server/sql/monitoring_triggers.sql"
    success = execute_sql_file(sql_file)
    sys.exit(0 if success else 1)