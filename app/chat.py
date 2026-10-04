"""'Ask PolicyPulse' — plain-English questions over the 360 + NBA data.

DEMO MODE: a transparent rule-based interpreter (filters are shown back to the user).
LIVE MODE: Cortex AI_COMPLETE writes a read-only SELECT over the APP/CURATED layer, which is
           validated (single SELECT, allow-listed objects) before it runs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from app.data import AS_OF

PRODUCTS = ["Health", "Motor", "Life", "Home"]
CITIES = ["Mumbai", "Pune", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", "Ahmedabad", "Jaipur",
          "Lucknow", "Kochi", "Indore", "Chandigarh", "Nagpur", "Coimbatore", "Nashik", "Mysuru", "Vadodara"]
SEGMENTS = {"hni": "HNI", "sme": "SME Owner", "mass affluent": "Mass Affluent", "affluent": "Mass Affluent"}
INTENT_WORDS = {
    "cancellation_intent": ["cancel", "port", "leave", "switch"],
    "claim_issue": ["claim", "complain", "complaint"],
    "price_concern": ["price", "premium hike", "discount", "expensive", "cheaper"],
    "upsell_interest": ["upsell", "cross-sell", "cross sell", "upgrade", "interested in", "add cover"],
    "service_praise": ["happy", "praise", "promoter", "advocate", "satisfied"],
}
EXAMPLES = [
    "Which health policyholders renewing next month are at high churn risk and why?",
    "How much premium is at risk in Bengaluru?",
    "Top 10 customers threatening to cancel",
    "Which HNI customers are interested in upsell?",
    "Customers with claim complaints renewing in the next 30 days",
    "What should I do for Arjun Shah?",
]


@dataclass
class Answer:
    text: str
    table: pd.DataFrame | None = None
    filters: list[str] = field(default_factory=list)
    sql: str | None = None
    customer_id: str | None = None


def _inr(x: float) -> str:
    x = float(x or 0)
    if x >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:.1f} L"
    return f"₹{x:,.0f}"


def answer_demo(q: str, d: dict[str, pd.DataFrame]) -> Answer:
    ql = q.lower()
    nba, pol, ins = d["nba"], d["pol"], d["ins"]

    # 1) single-customer lookup -> route to the 360/NBA card
    m = re.search(r"\bc\d{4}\b", ql)
    hit = None
    if m:
        hit = nba[nba.CUSTOMER_ID.str.lower() == m.group(0)]
    else:
        for name in nba.FULL_NAME:
            if name.lower() in ql:
                hit = nba[nba.FULL_NAME == name]
                break
    if hit is not None and len(hit):
        r = hit.iloc[0]
        drv = ", ".join([f"{x['factor']} (+{x['points']:.0f})" for x in r.RISK_DRIVERS if x["points"] > 0][:3])
        return Answer(
            text=(f"**{r.FULL_NAME}** ({r.CUSTOMER_ID}) is **{r.RISK_BAND} risk ({r.RISK_SCORE:.0f}/100)**"
                  f"{' — drivers: ' + drv if drv else ''}.\n\n**Next best action:** {r.ACTION}.\n\n"
                  f"Evidence: {', '.join(r.EVIDENCE) or '—'}. Open the *Customer 360* tab for the full card."),
            filters=[f"customer = {r.CUSTOMER_ID}"], customer_id=r.CUSTOMER_ID)

    df = nba.copy()
    filters: list[str] = []

    # 2) product + renewal window (policy-level)
    prods = [p for p in PRODUCTS if p.lower() in ql or (p == "Motor" and re.search(r"\bcar|vehicle", ql))]
    win = None
    if "next month" in ql:
        start = (AS_OF + pd.offsets.MonthBegin(1)).normalize()
        win = (start, start + pd.offsets.MonthEnd(0), start.strftime("%B %Y"))
    elif "this month" in ql:
        win = (AS_OF, AS_OF + pd.offsets.MonthEnd(0), AS_OF.strftime("%B %Y"))
    elif "next week" in ql:
        win = (AS_OF, AS_OF + pd.Timedelta(days=7), "next 7 days")
    else:
        m = re.search(r"next (\d+) days", ql)
        if m:
            n = int(m.group(1))
            win = (AS_OF, AS_OF + pd.Timedelta(days=n), f"next {n} days")
        elif "renew" in ql:
            win = (AS_OF, AS_OF + pd.Timedelta(days=60), "next 60 days")
    if prods or win:
        p = pol[pol.STATUS != "Lapsed"]
        if prods:
            p = p[p.PRODUCT_LINE.isin(prods)]
            filters.append(f"product ∈ {prods}")
        if win:
            p = p[(p.RENEWAL_DATE >= win[0]) & (p.RENEWAL_DATE <= win[1])]
            filters.append(f"renewal in {win[2]} ({win[0]:%d %b}–{win[1]:%d %b})")
        p = (p.sort_values("RENEWAL_DATE").groupby("CUSTOMER_ID")
             .agg(POLICY_IDS=("POLICY_ID", ", ".join), RENEWAL_DATE=("RENEWAL_DATE", "min"),
                  POLICY_PREMIUM=("ANNUAL_PREMIUM", "sum")).reset_index())
        df = df.merge(p, on="CUSTOMER_ID")

    # 3) risk band
    if re.search(r"high[- ]?(churn )?risk|most at risk|critical", ql):
        df = df[df.RISK_BAND == "High"]
        filters.append("risk band = High")
    elif re.search(r"medium risk", ql):
        df = df[df.RISK_BAND == "Medium"]
        filters.append("risk band = Medium")
    elif re.search(r"low risk|safe|loyal", ql):
        df = df[df.RISK_BAND == "Low"]
        filters.append("risk band = Low")
    elif re.search(r"at[- ]risk|churn|retention|leave", ql):
        df = df[df.RISK_BAND.isin(["High", "Medium"])]
        filters.append("risk band ∈ {High, Medium}")

    # 4) geography / segment
    cities = [c for c in CITIES if c.lower() in ql or (c == "Bengaluru" and "bangalore" in ql)]
    if cities:
        df = df[df.CITY.isin(cities)]
        filters.append(f"city ∈ {cities}")
    for k, v in SEGMENTS.items():
        if re.search(rf"\b{k}\b", ql):
            df = df[df.SEGMENT == v]
            filters.append(f"segment = {v}")
            break

    # 5) interaction intent (from AI insights, last 180 days)
    recent = ins[ins.CALL_TS >= AS_OF - pd.Timedelta(days=180)]
    for intent, words in INTENT_WORDS.items():
        if any(w in ql for w in words) and not (intent == "claim_issue" and "premium" in ql and "claim" not in ql):
            ids = set(recent[recent.PRIMARY_INTENT == intent].CUSTOMER_ID)
            df = df[df.CUSTOMER_ID.isin(ids)]
            filters.append(f"had a '{intent}' call (180d)")

    df = df.sort_values("RISK_SCORE", ascending=False)
    m = re.search(r"top (\d+)", ql)
    if m:
        df = df.head(int(m.group(1)))
        filters.append(f"top {m.group(1)} by risk")

    n = len(df)
    prem = df.TOTAL_ANNUAL_PREMIUM.sum()
    if n == 0:
        return Answer("No customers match that question. Try one of the examples below.", filters=filters)

    lead = f"**{n} customer{'s' if n != 1 else ''}** match, holding **{_inr(prem)}** in annual premium"
    if "how much" in ql or "premium" in ql:
        lead += f"; expected loss at current risk **{_inr(df.EXPECTED_PREMIUM_LOSS.sum())}**"
    lead += "."
    why = ""
    if "why" in ql or n <= 15:
        top_drv = (pd.Series([x["factor"] for ds in df.RISK_DRIVERS for x in ds if x["points"] > 0])
                   .value_counts().head(3))
        if len(top_drv):
            why = "\n\n**Most common risk drivers:** " + ", ".join(f"{k} ({v})" for k, v in top_drv.items()) + "."
        acts = df.ACTION_CATEGORY.value_counts().head(3)
        why += "\n\n**Recommended plays:** " + ", ".join(f"{k.replace('_', ' ').title()} ({v})" for k, v in acts.items()) + "."

    cols = ["CUSTOMER_ID", "FULL_NAME", "CITY", "SEGMENT", "RISK_SCORE", "RISK_BAND"]
    if "POLICY_IDS" in df:
        cols += ["POLICY_IDS", "RENEWAL_DATE"]
    else:
        cols += ["NEXT_RENEWAL_PRODUCT", "NEXT_RENEWAL_DATE"]
    df = df.assign(TOP_DRIVERS=df.RISK_DRIVERS.map(lambda ds: "; ".join([x["factor"] for x in ds if x["points"] > 0][:3])))
    cols += ["TOTAL_ANNUAL_PREMIUM", "TOP_DRIVERS", "ACTION"]
    return Answer(lead + why, table=df[cols].reset_index(drop=True), filters=filters)


# --------------------------------------------------------------------- LIVE: Cortex text-to-SQL
SCHEMA_DOC = """Tables (Snowflake, database POLICYPULSE):
APP.NEXT_BEST_ACTIONS(CUSTOMER_ID, FULL_NAME, SEGMENT, CITY, PRODUCT_LINES, TOTAL_ANNUAL_PREMIUM, NEXT_RENEWAL_POLICY_ID,
  NEXT_RENEWAL_PRODUCT, NEXT_RENEWAL_DATE, DAYS_TO_RENEWAL, RISK_SCORE, RISK_BAND('High'|'Medium'|'Low'), RISK_DRIVERS(ARRAY),
  EXPECTED_PREMIUM_LOSS, PREMIUM_AT_RISK, ACTION_CATEGORY, ACTION, REASON, EVIDENCE(ARRAY), CUSTOMER_MESSAGE, CHANNEL)
CURATED.CUSTOMER_360(CUSTOMER_ID, FULL_NAME, AGE, CITY, SEGMENT, TENURE_YEARS, N_ACTIVE_POLICIES, TOTAL_ANNUAL_PREMIUM,
  N_OPEN_CLAIMS, N_SLOW_CLAIMS, N_LATE_12M, N_MISSED_12M, AVG_SENTIMENT_90D, LAST_INTENT, N_CANCEL_INTENT_90D, N_UPSELL_INTEREST_180D)
CURATED.INTERACTION_INSIGHTS(TRANSCRIPT_ID, CUSTOMER_ID, CALL_TS, PRIMARY_INTENT('claim_issue'|'price_concern'|
  'cancellation_intent'|'upsell_interest'|'service_praise'|'general_service'), SENTIMENT_SCORE, SENTIMENT_LABEL, SUMMARY)
RAW.POLICIES(POLICY_ID, CUSTOMER_ID, PRODUCT_LINE('Health'|'Motor'|'Life'|'Home'), PLAN_NAME, ANNUAL_PREMIUM, RENEWAL_DATE, STATUS)
Today is POLICYPULSE.CURATED.AS_OF_DATE() (2026-10-04)."""

ALLOWED = ("POLICYPULSE.APP.", "POLICYPULSE.CURATED.", "POLICYPULSE.RAW.POLICIES", "APP.", "CURATED.", "RAW.POLICIES")


def answer_live(q: str, complete) -> Answer:
    prompt = (f"{SCHEMA_DOC}\n\nWrite ONE Snowflake SQL SELECT statement (fully-qualified names, LIMIT 50) that answers: "
              f"\"{q}\". Include FULL_NAME, RISK_SCORE, RISK_BAND and REASON when listing customers. "
              "Return only the SQL, no explanation, no markdown fences.")
    raw = complete(prompt)
    s = re.sub(r"^```(sql)?|```$", "", raw.strip(), flags=re.I | re.M).strip().rstrip(";")
    bad = re.search(r"\b(insert|update|delete|merge|drop|alter|create|grant|truncate|call|put|copy)\b", s, re.I)
    refs = re.findall(r"\b(?:from|join)\s+([\w.]+)", s, re.I)
    if not s.lower().startswith(("select", "with")) or bad or ";" in s or \
            any(not r.upper().startswith(ALLOWED) for r in refs):
        return Answer("I couldn't generate a safe read-only query for that. Try rephrasing.", sql=s)
    return Answer("", sql=s)
