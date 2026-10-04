"""One-shot: create Snowflake objects and load the synthetic data.

    python data/generate_data.py          # 1. make CSVs
    python scripts/load_to_snowflake.py   # 2. setup + PUT + COPY

Uses ~/.snowflake/connections.toml (set SNOWFLAKE_CONNECTION=<name> to pick one).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
os.chdir(ROOT)  # PUT file:// paths in 01_load_from_stage.sql are relative to repo root

from sf_conn import connect, run_sql_file  # noqa: E402

if __name__ == "__main__":
    conn = connect()
    print("▶ 00_setup.sql")
    run_sql_file(conn, "sql/00_setup.sql")
    print("▶ 01_load_from_stage.sql")
    rows = run_sql_file(conn, "sql/01_load_from_stage.sql")
    for t, n in rows or []:
        print(f"  {t:18s} {n}")
    conn.close()
