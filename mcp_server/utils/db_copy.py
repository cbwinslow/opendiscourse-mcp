"""Helpers to perform high-performance bulk COPY operations into Postgres."""
import io
import pandas as pd
from typing import Dict, Any


def copy_dataframe_to_table(conn, df: pd.DataFrame, table: str, columns: Dict[str, str]) -> Dict[str, Any]:
    """Use psycopg2 COPY FROM STDIN to load a DataFrame into `table`.

    - `conn` should be a psycopg2 connection (raw connection) or any object with .cursor()
    - `df` is the pandas DataFrame
    - `columns` is an ordered mapping of table_column -> df_column
    """
    # Build CSV in memory with correct column order
    ordered_cols = list(columns.keys())
    df_cols = [columns[c] for c in ordered_cols]
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, columns=df_cols, header=False, index=False)
    csv_buffer.seek(0)

    copy_sql = f"COPY {table} ({', '.join(ordered_cols)}) FROM STDIN WITH (FORMAT csv)"

    cur = conn.cursor()
    try:
        cur.copy_expert(copy_sql, csv_buffer)
        conn.commit()
    finally:
        cur.close()
    return {"status": "ok", "rows": len(df)}
