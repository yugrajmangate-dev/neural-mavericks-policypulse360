"""Snowflake connection helper.

Resolution order:
  1. SNOWFLAKE_CONNECTION env var -> named connection in ~/.snowflake/connections.toml
     (same file the Snowflake CLI and CoCo CLI use)
  2. default connection in ~/.snowflake/connections.toml
Credentials never live in this repo.
"""
import os
from pathlib import Path

import snowflake.connector


def connect():
    name = os.environ.get("SNOWFLAKE_CONNECTION")
    kwargs = {"connection_name": name} if name else {}
    conn = snowflake.connector.connect(**kwargs)
    return conn


def run_sql_file(conn, path: str | Path, verbose: bool = True):
    """Execute every statement in a .sql file (PUT supported). Returns the last cursor's rows."""
    sql = Path(path).read_text(encoding="utf-8")
    last = None
    for cur in conn.execute_string(sql, remove_comments=True):
        if verbose:
            q = " ".join(cur.query.split())[:90]
            print(f"  ✓ {q}")
        last = cur
    try:
        return last.fetchall() if last else None
    except Exception:
        return None
