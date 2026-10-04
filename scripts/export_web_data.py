"""Export demo_data/*.parquet -> web/public/data/*.json for the React Command Center.

Reads the same parquet files the Streamlit app uses. Re-run after a real Cortex export
(scripts/export_demo_data.py) and rebuild the site: no code changes needed.

    python scripts/export_web_data.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "demo_data"
OUT = ROOT / "web" / "public" / "data"


def clean(df: pd.DataFrame) -> list[dict]:
    df = df.copy()
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%dT%H:%M:%S")
        elif df[c].dtype == object:
            df[c] = df[c].map(lambda v: v.replace("�", "—") if isinstance(v, str) else v)
    df = df.replace({np.nan: None})
    return json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False))


def parse_json_col(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return v
    if isinstance(v, (list, np.ndarray)):
        return [x for x in v]
    return v or []


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    meta = json.loads((SRC / "meta.json").read_text(encoding="utf-8"))
    source = meta.get("source", "unknown")

    c360 = pd.read_parquet(SRC / "customer_360.parquet")
    ins = pd.read_parquet(SRC / "interaction_insights.parquet")
    nba = pd.read_parquet(SRC / "next_best_actions.parquet")
    pol = pd.read_parquet(SRC / "policies.parquet")
    clm = pd.read_parquet(SRC / "claims.parquet")
    pay = pd.read_parquet(SRC / "payments.parquet")

    nba_recs = clean(nba)
    for r in nba_recs:
        r["RISK_DRIVERS"] = parse_json_col(r.get("RISK_DRIVERS"))
        r["EVIDENCE"] = parse_json_col(r.get("EVIDENCE"))

    ins = ins.sort_values("CALL_TS")
    pay = pay.sort_values("DUE_DATE")

    files = {
        "customers_360": clean(c360),
        "next_best_actions": nba_recs,
        "interaction_insights": clean(ins),
        "policies": clean(pol),
        "claims": clean(clm),
        "payments": clean(pay),
    }

    band = nba["RISK_BAND"].value_counts().to_dict()
    portfolio = {
        "source": source,
        "as_of": meta.get("as_of"),
        "n_customers": int(len(c360)),
        "pct_high_risk": float((nba["RISK_BAND"] == "High").mean() * 100),
        "premium_at_risk": float(nba["PREMIUM_AT_RISK"].fillna(0).sum()),
        "expected_premium_loss": float(nba["EXPECTED_PREMIUM_LOSS"].fillna(0).sum()),
        "total_premium": float(c360["TOTAL_ANNUAL_PREMIUM"].fillna(0).sum()),
        "avg_sentiment": float(ins["SENTIMENT_SCORE"].mean()),
        "n_transcripts": int(len(ins)),
        "risk_bands": {k: int(band.get(k, 0)) for k in ["High", "Medium", "Low"]},
        "intents": {k: int(v) for k, v in ins["PRIMARY_INTENT"].value_counts().items()},
        "actions": {k: int(v) for k, v in nba["ACTION_CATEGORY"].value_counts().items()},
        "risk_histogram": [
            {"bucket": f"{b}-{b + 9}", "count": int(((nba["RISK_SCORE"] >= b) & (nba["RISK_SCORE"] < b + 10)).sum())}
            for b in range(0, 100, 10)
        ],
    }
    files["portfolio"] = portfolio
    files["meta"] = {**meta, "source": source}

    for name, payload in files.items():
        (OUT / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"wrote {name}.json ({len(payload) if isinstance(payload, list) else 'obj'})")
    print(f"source = {source}")


if __name__ == "__main__":
    main()
