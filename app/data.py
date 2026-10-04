"""Data access for PolicyPulse 360.

DEMO MODE  (default, no secrets): reads demo_data/*.parquet exported from Snowflake
LIVE MODE  ([snowflake] in st.secrets): queries POLICYPULSE in Snowflake, and can call Cortex on demand
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo_data"
AS_OF = pd.Timestamp("2026-10-04")

TABLES = {
    "c360": "SELECT * FROM POLICYPULSE.CURATED.CUSTOMER_360",
    "ins": "SELECT * FROM POLICYPULSE.CURATED.INTERACTION_INSIGHTS",
    "nba": """SELECT * EXCLUDE (RISK_DRIVERS, EVIDENCE),
                     TO_JSON(RISK_DRIVERS) AS RISK_DRIVERS, TO_JSON(EVIDENCE) AS EVIDENCE
              FROM POLICYPULSE.APP.NEXT_BEST_ACTIONS""",
    "pol": "SELECT * FROM POLICYPULSE.RAW.POLICIES",
    "clm": "SELECT * FROM POLICYPULSE.RAW.CLAIMS",
    "pay": "SELECT * FROM POLICYPULSE.RAW.PAYMENTS",
}
FILES = {"c360": "customer_360", "ins": "interaction_insights", "nba": "next_best_actions",
         "pol": "policies", "clm": "claims", "pay": "payments"}
DATE_COLS = ["CUSTOMER_SINCE", "NEXT_RENEWAL_DATE", "START_DATE", "RENEWAL_DATE", "CLAIM_DATE",
             "SETTLED_DATE", "DUE_DATE", "PAID_DATE", "CALL_TS", "LAST_CALL_TS"]


def is_live() -> bool:
    try:
        return "snowflake" in st.secrets
    except Exception:  # no secrets file at all
        return False


@st.cache_resource(show_spinner=False)
def _conn():
    import snowflake.connector
    cfg = dict(st.secrets["snowflake"])
    return snowflake.connector.connect(**cfg, client_session_keep_alive=False)


def sql(q: str, params=None) -> pd.DataFrame:
    cur = _conn().cursor()
    cur.execute(q, params or None)
    return cur.fetch_pandas_all()


def _normalise(d: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    for df in d.values():
        for c in df.columns:
            if c in DATE_COLS:
                df[c] = pd.to_datetime(df[c], errors="coerce")
    nba = d["nba"]
    nba["RISK_DRIVERS"] = nba["RISK_DRIVERS"].map(lambda s: sorted(json.loads(s) if isinstance(s, str) else (s or []),
                                                                    key=lambda x: -float(x["points"])))
    nba["EVIDENCE"] = nba["EVIDENCE"].map(lambda s: json.loads(s) if isinstance(s, str) else list(s or []))
    return d


@st.cache_data(ttl=600, show_spinner="Loading PolicyPulse data…")
def load(live: bool) -> dict[str, pd.DataFrame]:
    if live:
        d = {k: sql(q) for k, q in TABLES.items()}
    else:
        d = {k: pd.read_parquet(DEMO / f"{f}.parquet") for k, f in FILES.items()}
    return _normalise(d)


def meta(live: bool) -> dict:
    if live:
        return {"source": "snowflake-live"}
    try:
        return json.loads((DEMO / "meta.json").read_text())
    except Exception:
        return {"source": "unknown"}


# --------------------------------------------------------------------- live-only Cortex calls
def regenerate_nba(customer_id: str) -> dict | None:
    """LIVE: run AI_COMPLETE on the grounded prompt for one customer (Skill 3 single-customer mode)."""
    q = """SELECT TRY_PARSE_JSON(REGEXP_SUBSTR(AI_COMPLETE('mistral-large2', PROMPT), '\\\\{.*\\\\}', 1, 1, 's')) AS J
           FROM POLICYPULSE.APP.NBA_CONTEXT WHERE CUSTOMER_ID = %s"""
    df = sql(q, (customer_id,))
    if df.empty or df.iloc[0, 0] is None:
        return None
    j = df.iloc[0, 0]
    return json.loads(j) if isinstance(j, str) else j


def cortex_complete(prompt: str, model: str = "mistral-large2") -> str:
    return sql("SELECT AI_COMPLETE(%s, %s) AS R", (model, prompt)).iloc[0, 0]
