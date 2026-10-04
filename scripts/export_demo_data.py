"""Export real pipeline outputs (Cortex-enriched) from Snowflake -> demo_data/*.parquet

Run after the 3 skills have executed in Snowflake. The public Streamlit app (DEMO MODE)
reads these files, so judges see genuine Cortex outputs without a Snowflake login.

    python scripts/export_demo_data.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sf_conn import connect  # noqa: E402

OUT = ROOT / "demo_data"
QUERIES = {
    "customer_360": "SELECT * FROM POLICYPULSE.CURATED.CUSTOMER_360",
    "interaction_insights": "SELECT * FROM POLICYPULSE.CURATED.INTERACTION_INSIGHTS",
    "next_best_actions": """SELECT * EXCLUDE (RISK_DRIVERS, EVIDENCE),
                                   TO_JSON(RISK_DRIVERS) AS RISK_DRIVERS, TO_JSON(EVIDENCE) AS EVIDENCE
                            FROM POLICYPULSE.APP.NEXT_BEST_ACTIONS""",
    "policies": "SELECT * FROM POLICYPULSE.RAW.POLICIES",
    "claims": "SELECT * FROM POLICYPULSE.RAW.CLAIMS",
    "payments": "SELECT * FROM POLICYPULSE.RAW.PAYMENTS",
}
DATE_COLS = ["CUSTOMER_SINCE", "NEXT_RENEWAL_DATE", "START_DATE", "RENEWAL_DATE", "CLAIM_DATE",
             "SETTLED_DATE", "DUE_DATE", "PAID_DATE"]

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    conn = connect()
    cur = conn.cursor()
    cur.execute("USE WAREHOUSE POLICYPULSE_WH")
    for name, q in QUERIES.items():
        df = cur.execute(q).fetch_pandas_all()
        for c in df.columns:
            if c in DATE_COLS:
                df[c] = pd.to_datetime(df[c])
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"  {name:22s} {len(df):5d} rows")
    acc = cur.execute("""SELECT ROUND(AVG(IFF(i.PRIMARY_INTENT = l.TRUE_INTENT, 1, 0)) * 100, 1)
                         FROM POLICYPULSE.CURATED.INTERACTION_INSIGHTS i
                         JOIN POLICYPULSE.RAW.EVAL_TRANSCRIPT_LABELS l USING (TRANSCRIPT_ID)""").fetchone()[0]
    (OUT / "meta.json").write_text(json.dumps({
        "source": "snowflake-cortex", "as_of": "2026-10-04",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "intent_accuracy_pct": float(acc) if acc is not None else None,
        "note": "Exported from POLICYPULSE (Cortex SENTIMENT + AI_CLASSIFY + AI_COMPLETE).",
    }, indent=2))
    print(f"✓ demo_data refreshed from Snowflake (AI_CLASSIFY accuracy {acc}%)")
    conn.close()
