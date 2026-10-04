"""Offline simulation of the 3-skill pipeline -> demo_data/*.parquet

Why: the public Streamlit app must work without a Snowflake login. The *real* demo data comes from
`scripts/export_demo_data.py` after the skills run in Snowflake (Cortex outputs). This script is a
fallback that mirrors the SQL logic 1:1 (same 360 columns, same risk weights, same rule engine)
but swaps Cortex for lightweight stand-ins:
    SENTIMENT   -> lexicon score on customer utterances
    AI_CLASSIFY -> keyword rules
    AI_COMPLETE -> templated summary / rule-engine NBA
Every row is tagged ENRICHED_BY / GENERATED_BY = 'local-sim' so it is never mistaken for Cortex output.

    python scripts/simulate_pipeline_local.py
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "demo_data"
AS_OF = pd.Timestamp(date(2026, 10, 4))

# ----------------------------------------------------------------------------- Skill 2 stand-ins
NEG = ["frustrat", "disappoint", "nightmare", "poor", "nobody", "complain", "not hopeful", "forever",
       "promised last time", "failing", "doesn't even", "not what i was promised", "can't justify",
       "stop the auto-debit", "cancel", "port", "still showing", "only ₹", "increased", "big jump",
       "higher than others", "tight budget", "not renew", "made up my mind", "nothing", "own pocket",
       "this is how claims are handled"]
POS = ["thank", "great", "wonderful", "smooth", "very easy", "convenient", "good", "perfect", "nice",
       "recommended", "keep it up", "congratulations", "happy", "all good", "sounds good"]


def customer_text(t: str) -> str:
    return " ".join(l.split(":", 1)[1].strip() for l in t.split("\n") if l.strip().startswith("Customer:"))


def sentiment(text: str, rng) -> float:
    s = text.lower()
    n = sum(s.count(w) for w in NEG)
    p = sum(s.count(w) for w in POS)
    raw = (p - 1.3 * n) / (p + n + 1.5)
    return float(np.clip(raw + rng.normal(0, 0.06), -0.95, 0.95))


def classify(text: str) -> str:
    s = text.lower()
    if re.search(r"\bcancel|\bport\b|port my|not renew|stop the auto-debit", s):
        return "cancellation_intent"
    if "claim" in s and re.search(r"still|pending|delay|surveyor|approved only|verification|nobody", s) \
            or "garage" in s:
        return "claim_issue"
    if re.search(r"premium has increased|cheaper|discount|quotes|price is higher|budget|aggregator", s):
        return "price_concern"
    if re.search(r"add her|top-up|home insurance|term plan|sum insured enough|quote\.", s):
        return "upsell_interest"
    if re.search(r"say thanks|very easy|very smooth|keep it up|recommended you", s):
        return "service_praise"
    return "general_service"


def summarise(intent: str, full: str, cust: str) -> str:
    ids = re.findall(r"(CLM-\d+|KVH-[A-Z]{2}-\d+)", full)
    amt = re.findall(r"₹([\d,]+)", cust)
    days = re.findall(r"(\d+) days", cust)
    pid = next((i for i in ids if i.startswith("KVH")), "their policy")
    cid = next((i for i in ids if i.startswith("CLM")), None)
    if intent == "claim_issue":
        if "garage" in cust:
            return (f"Angry that motor claim is stuck at garage {days[0] if days else 'several'} days and only "
                    f"₹{amt[0] if amt else '—'} approved; senior claims callback promised.")
        extra = " and threatened an IRDAI complaint" if "IRDAI" in cust else ""
        return (f"Frustrated that claim {cid or ''} is unresolved after ~{days[0] if days else 'many'} days "
                f"despite resubmitting documents{extra}; priority escalation promised.").replace("  ", " ")
    if intent == "cancellation_intent":
        if "port" in cust.lower():
            return f"Wants to port {pid} to another insurer citing poor claims and app issues; asked to stop auto-debit."
        return (f"Asked how to cancel {pid}: unhappy with claim service and premium hike, holds a quote "
                f"₹{amt[0] if amt else 'lower'} cheaper; senior advisor callback in 24h.")
    if intent == "price_concern":
        if "percent" in cust:
            pct = re.findall(r"(\d+) percent", cust)
            return (f"Questioned ~{pct[0] if pct else ''}% renewal hike on {pid} with no claims; found plan "
                    f"₹{amt[0] if amt else ''} cheaper online; revised quote to be sent.")
        return "Comparing renewal quotes, finds Kavach pricier and asked for discounts; may switch if not competitive."
    if intent == "upsell_interest":
        if "baby" in cust:
            return "Wants to add newborn to health policy and asked about higher cover; interested in super top-up quote."
        return "Bought a new home; wants Home Protect quote with multi-policy discount and is considering a term plan."
    if intent == "service_praise":
        if cid:
            return f"Called to thank Kavach — claim {cid} settled within a week via smooth cashless process; referred a relative."
        return "Praised quick 2-minute app renewal and instant policy delivery on WhatsApp."
    if "address" in cust:
        return "Requested address update on policy records; endorsement within 3 working days."
    if "certificate" in cust:
        return f"Requested premium-paid certificate for {pid} for tax filing and confirmed nominee."
    return f"Asked renewal due date for {pid} and wants e-NACH auto-debit set up."


def interaction_insights(trn: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    df = trn.copy()
    df["CUSTOMER_TEXT"] = df["TRANSCRIPT_TEXT"].map(customer_text)
    df["SENTIMENT_SCORE"] = [round(sentiment(t, rng), 3) for t in df["CUSTOMER_TEXT"]]
    df["SENTIMENT_LABEL"] = np.select([df.SENTIMENT_SCORE <= -0.25, df.SENTIMENT_SCORE >= 0.25],
                                      ["negative", "positive"], "neutral")
    df["PRIMARY_INTENT"] = df["CUSTOMER_TEXT"].map(classify)
    df["SUMMARY"] = [summarise(i, f, c) for i, f, c in zip(df.PRIMARY_INTENT, df.TRANSCRIPT_TEXT, df.CUSTOMER_TEXT)]
    df["ENRICHED_BY"] = "local-sim (lexicon sentiment + keyword intent + template summary)"
    df["ENRICHED_AT"] = pd.Timestamp(datetime.now()).floor("s")
    cols = ["TRANSCRIPT_ID", "CUSTOMER_ID", "POLICY_ID", "CALL_TS", "AGENT_ID", "CUSTOMER_TEXT", "SENTIMENT_SCORE",
            "SENTIMENT_LABEL", "PRIMARY_INTENT", "SUMMARY", "TRANSCRIPT_TEXT", "ENRICHED_BY", "ENRICHED_AT"]
    return df[cols]


# ----------------------------------------------------------------------------- Skill 1 (mirrors c360_unify.sql)
def customer_360(cus, pol, clm, pay, trn, ins) -> pd.DataFrame:
    c = cus.copy()
    live = pol[pol.STATUS != "Lapsed"]
    g = pol.groupby("CUSTOMER_ID")
    p = pd.DataFrame({
        "N_ACTIVE_POLICIES": g.STATUS.apply(lambda s: s.isin(["Active", "Grace Period", "Cancellation Requested"]).sum()),
        "PRODUCT_LINES": g.PRODUCT_LINE.apply(lambda s: ", ".join(sorted(set(s)))),
        "TOTAL_ANNUAL_PREMIUM": live.groupby("CUSTOMER_ID").ANNUAL_PREMIUM.sum(),
        "TOTAL_SUM_INSURED": g.SUM_INSURED.sum(),
        **{f"HAS_{k.upper()}": g.PRODUCT_LINE.apply(lambda s, k=k: int(k in set(s))) for k in ["Health", "Life", "Motor", "Home"]},
        "N_CANCEL_REQUESTS": g.STATUS.apply(lambda s: (s == "Cancellation Requested").sum()),
        "N_IN_GRACE": g.STATUS.apply(lambda s: (s == "Grace Period").sum()),
    })
    nr = live.sort_values("RENEWAL_DATE").groupby("CUSTOMER_ID").head(1).set_index("CUSTOMER_ID")
    nr = pd.DataFrame({
        "NEXT_RENEWAL_POLICY_ID": nr.POLICY_ID, "NEXT_RENEWAL_PRODUCT": nr.PRODUCT_LINE,
        "NEXT_RENEWAL_PLAN": nr.PLAN_NAME, "NEXT_RENEWAL_PREMIUM": nr.ANNUAL_PREMIUM,
        "NEXT_RENEWAL_DATE": nr.RENEWAL_DATE, "DAYS_TO_RENEWAL": (nr.RENEWAL_DATE - AS_OF).dt.days})

    cl = clm[clm.CLAIM_DATE >= AS_OF - pd.DateOffset(months=18)]
    open_ = cl.STATUS.isin(["Pending", "Under Review"])
    cl = cl.assign(OPEN=open_, REJ=cl.STATUS.eq("Rejected"),
                   SLOW=((cl.STATUS == "Settled") & (cl.DAYS_TO_SETTLE > 30)) | (open_ & (cl.DAYS_OPEN > 30)),
                   OPEN_DAYS=cl.DAYS_OPEN.where(open_))
    gc = cl.groupby("CUSTOMER_ID")
    k = pd.DataFrame({"N_CLAIMS": gc.size(), "N_OPEN_CLAIMS": gc.OPEN.sum(), "N_REJECTED_CLAIMS": gc.REJ.sum(),
                      "N_SLOW_CLAIMS": gc.SLOW.sum(), "TOTAL_CLAIMED": gc.CLAIM_AMOUNT.sum(),
                      "TOTAL_APPROVED": gc.APPROVED_AMOUNT.sum(), "AVG_DAYS_TO_SETTLE": gc.DAYS_TO_SETTLE.mean().round(1),
                      "MAX_OPEN_CLAIM_DAYS": gc.OPEN_DAYS.max()})

    py = pay[pay.DUE_DATE >= AS_OF - pd.DateOffset(months=12)]
    gp = py.groupby("CUSTOMER_ID")
    y = pd.DataFrame({"N_PAYMENTS_DUE_12M": gp.size(),
                      "N_LATE_12M": gp.PAYMENT_STATUS.apply(lambda s: (s == "Late").sum()),
                      "N_MISSED_12M": gp.PAYMENT_STATUS.apply(lambda s: (s == "Missed").sum()),
                      "ON_TIME_RATE_12M": gp.PAYMENT_STATUS.apply(lambda s: round((s == "On-time").mean(), 3)),
                      "AVG_DAYS_LATE": py[py.PAYMENT_STATUS == "Late"].groupby("CUSTOMER_ID").DAYS_LATE.mean().round(1)})

    t = trn[trn.CALL_TS >= AS_OF - pd.Timedelta(days=180)]
    gt = t.groupby("CUSTOMER_ID")
    calls = pd.DataFrame({"N_CALLS_180D": gt.size(), "LAST_CALL_TS": gt.CALL_TS.max(),
                          "CALL_MINUTES_180D": gt.DURATION_SEC.sum() // 60})

    i = ins[ins.CALL_TS >= AS_OF - pd.Timedelta(days=180)].sort_values("CALL_TS")
    r90 = i.CALL_TS >= AS_OF - pd.Timedelta(days=90)
    gi = i.groupby("CUSTOMER_ID")
    cnt = lambda m: i[m].groupby("CUSTOMER_ID").size()  # noqa: E731
    ai = pd.DataFrame({
        "AVG_SENTIMENT_90D": i[r90].groupby("CUSTOMER_ID").SENTIMENT_SCORE.mean().round(3),
        "AVG_SENTIMENT_180D": gi.SENTIMENT_SCORE.mean().round(3),
        "LAST_SENTIMENT": gi.SENTIMENT_SCORE.last(), "LAST_INTENT": gi.PRIMARY_INTENT.last(),
        "N_CANCEL_INTENT_90D": cnt(r90 & (i.PRIMARY_INTENT == "cancellation_intent")),
        "N_CANCEL_INTENT_180D": cnt(i.PRIMARY_INTENT == "cancellation_intent"),
        "N_PRICE_CONCERN_90D": cnt(r90 & (i.PRIMARY_INTENT == "price_concern")),
        "N_CLAIM_ISSUE_90D": cnt(r90 & (i.PRIMARY_INTENT == "claim_issue")),
        "N_UPSELL_INTEREST_180D": cnt(i.PRIMARY_INTENT == "upsell_interest"),
        "N_SERVICE_PRAISE_180D": cnt(i.PRIMARY_INTENT == "service_praise"),
    })
    ai["HAS_AI_INSIGHTS"] = True

    out = c.set_index("CUSTOMER_ID").join([p, nr, k, y, calls, ai])
    zero = ["N_ACTIVE_POLICIES", "TOTAL_ANNUAL_PREMIUM", "N_CLAIMS", "N_OPEN_CLAIMS", "N_REJECTED_CLAIMS",
            "N_SLOW_CLAIMS", "TOTAL_CLAIMED", "TOTAL_APPROVED", "N_PAYMENTS_DUE_12M", "N_LATE_12M", "N_MISSED_12M",
            "N_CALLS_180D", "N_CANCEL_INTENT_90D", "N_CANCEL_INTENT_180D", "N_PRICE_CONCERN_90D",
            "N_CLAIM_ISSUE_90D", "N_UPSELL_INTEREST_180D", "N_SERVICE_PRAISE_180D"]
    out[zero] = out[zero].fillna(0)
    out["HAS_AI_INSIGHTS"] = out["HAS_AI_INSIGHTS"].fillna(False).astype(bool)
    return out.reset_index()


# ----------------------------------------------------------------------------- Skill 3 (mirrors churn_risk.sql + next_best_action.sql)
def churn_risk(c360: pd.DataFrame) -> pd.DataFrame:
    c = c360.copy()
    s = c.AVG_SENTIMENT_90D.fillna(c.AVG_SENTIMENT_180D).fillna(0.25)
    c["P_SENTIMENT"] = (25 * ((0.25 - s) / 1.0).clip(0, 1)).round(1)
    c["P_CANCEL"] = np.select([c.N_CANCEL_INTENT_90D > 0, c.N_CANCEL_INTENT_180D > 0], [20, 8], 0)
    c["P_PRICE"] = np.where(c.N_PRICE_CONCERN_90D > 0, 10, 0)
    c["P_PAYMENT"] = (15 * ((c.N_LATE_12M + 2 * c.N_MISSED_12M) / 4).clip(upper=1)).round(1)
    c["P_CLAIMS"] = (15 * ((c.N_SLOW_CLAIMS + c.N_REJECTED_CLAIMS) / 2).clip(upper=1)).round(1)
    d = c.DAYS_TO_RENEWAL
    c["P_RENEWAL"] = np.select([d <= 30, d <= 60, d <= 90], [15, 10, 5], 0)
    c["P_LOYALTY"] = np.where(c.TENURE_YEARS >= 8, -5, 0)
    c["P_ADVOCACY"] = np.where(c.N_SERVICE_PRAISE_180D > 0, -5, 0)
    pts = ["P_SENTIMENT", "P_CANCEL", "P_PRICE", "P_PAYMENT", "P_CLAIMS", "P_RENEWAL", "P_LOYALTY", "P_ADVOCACY"]
    c["RISK_SCORE"] = c[pts].sum(axis=1).clip(0, 100).round(1)
    c["RISK_BAND"] = np.select([c.RISK_SCORE >= 55, c.RISK_SCORE >= 30], ["High", "Medium"], "Low")
    c["EXPECTED_PREMIUM_LOSS"] = (c.TOTAL_ANNUAL_PREMIUM * c.RISK_SCORE / 100).round(0)

    def drivers(r):
        out = []
        sv = r.AVG_SENTIMENT_90D if pd.notna(r.AVG_SENTIMENT_90D) else r.AVG_SENTIMENT_180D
        if r.P_SENTIMENT > 0:
            out.append(("Negative sentiment", r.P_SENTIMENT, f"Avg customer sentiment {sv:.2f} (90d)"))
        if r.P_CANCEL > 0:
            out.append(("Cancellation / porting intent", r.P_CANCEL, f"{int(r.N_CANCEL_INTENT_180D)} call(s) mentioning cancel/port"))
        if r.P_PRICE > 0:
            out.append(("Price sensitivity", r.P_PRICE, f"{int(r.N_PRICE_CONCERN_90D)} price-concern call(s) in 90d"))
        if r.P_PAYMENT > 0:
            out.append(("Payment stress", r.P_PAYMENT, f"{int(r.N_LATE_12M)} late, {int(r.N_MISSED_12M)} missed payments (12m)"))
        if r.P_CLAIMS > 0:
            out.append(("Claim friction", r.P_CLAIMS, f"{int(r.N_SLOW_CLAIMS)} slow/open >30d, {int(r.N_REJECTED_CLAIMS)} rejected"))
        if r.P_RENEWAL > 0:
            out.append(("Renewal due soon", r.P_RENEWAL, f"{r.NEXT_RENEWAL_PRODUCT} renewal in {int(r.DAYS_TO_RENEWAL)} days"))
        if r.P_LOYALTY < 0:
            out.append(("Long tenure (protective)", r.P_LOYALTY, f"{r.TENURE_YEARS} years with Kavach"))
        if r.P_ADVOCACY < 0:
            out.append(("Recent praise (protective)", r.P_ADVOCACY, "Service-praise call in last 180d"))
        return json.dumps([{"factor": f, "points": float(p), "detail": dt} for f, p, dt in out])

    c["RISK_DRIVERS"] = c.apply(drivers, axis=1)
    return c


def next_best_actions(risk: pd.DataFrame, ins: pd.DataFrame) -> pd.DataFrame:
    i = ins[ins.CALL_TS >= AS_OF - pd.Timedelta(days=180)].sort_values("CALL_TS", ascending=False)
    ev = {k: i[i.PRIMARY_INTENT == v].groupby("CUSTOMER_ID").TRANSCRIPT_ID.apply(list)
          for k, v in [("CANCEL", "cancellation_intent"), ("CLAIM", "claim_issue"), ("PRICE", "price_concern"),
                       ("UPSELL", "upsell_interest"), ("PRAISE", "service_praise")]}
    ev_any = i.groupby("CUSTOMER_ID").TRANSCRIPT_ID.apply(list)

    rows = []
    for r in risk.itertuples():
        first = r.FULL_NAME.split()[0]
        ren = r.NEXT_RENEWAL_DATE.strftime("%d %b") if pd.notna(r.NEXT_RENEWAL_DATE) else ""
        xsell = ("Health Shield Family Floater" if r.HAS_HEALTH == 0 else "Term Secure life cover" if r.HAS_LIFE == 0
                 else "Home Protect" if r.HAS_HOME == 0 else "Super Top-Up health cover")
        if r.P_CANCEL >= 20 or (r.RISK_BAND == "High" and r.P_CANCEL > 0):
            cat = "RETENTION_CALL"
        elif r.P_CLAIMS >= 7.5 and r.N_OPEN_CLAIMS > 0:
            cat = "CLAIM_ESCALATION"
        elif r.P_PRICE > 0:
            cat = "PRICE_MATCH"
        elif r.P_PAYMENT >= 7.5:
            cat = "PAYMENT_FLEX"
        elif r.P_CLAIMS >= 7.5:
            cat = "CLAIM_ESCALATION"
        elif r.DAYS_TO_RENEWAL <= 30:
            cat = "RENEWAL_NUDGE"
        elif r.RISK_BAND == "Low" and (r.N_UPSELL_INTEREST_180D > 0 or r.N_ACTIVE_POLICIES <= 2):
            cat = "CROSS_SELL"
        elif r.RISK_BAND == "Low" and r.N_SERVICE_PRAISE_180D > 0:
            cat = "ADVOCACY"
        elif r.DAYS_TO_RENEWAL <= 60:
            cat = "RENEWAL_NUDGE"
        else:
            cat = "NURTURE"
        action = {
            "RETENTION_CALL": "Senior retention call within 24h with a personalised renewal offer",
            "CLAIM_ESCALATION": "Escalate open claim to claims manager and give a proactive status callback",
            "PRICE_MATCH": "Send personalised renewal quote: loyalty discount or higher-deductible option",
            "PAYMENT_FLEX": "Offer instalment switch to monthly e-NACH and a grace-period reminder",
            "RENEWAL_NUDGE": "Early-bird renewal reminder with one-click payment link",
            "CROSS_SELL": f"Cross-sell {xsell} with multi-policy discount",
            "ADVOCACY": "Invite to refer-a-friend programme and request a review",
            "NURTURE": "No outreach needed — keep in nurture journey",
        }[cat]
        msg = {
            "RETENTION_CALL": f"Hi {first}, we are sorry your recent experience with Kavach fell short. A senior advisor will call you within 24 hours with a personalised offer on policy {r.NEXT_RENEWAL_POLICY_ID} before it renews. Reply CALL to pick a time.",
            "CLAIM_ESCALATION": f"Hi {first}, your claim has been escalated to our claims manager today. You will get a status update within 48 hours and a direct contact for any documents needed. We apologise for the delay.",
            "PRICE_MATCH": f"Hi {first}, thank you for being with Kavach. We have prepared a personalised renewal quote for {r.NEXT_RENEWAL_POLICY_ID} with a loyalty discount and a lower-premium deductible option. Tap here to compare before {ren}.",
            "PAYMENT_FLEX": f"Hi {first}, to make premiums easier we can split your payment into monthly e-NACH instalments at no extra cost. Reply YES and we will set it up so your cover stays uninterrupted.",
            "RENEWAL_NUDGE": f"Hi {first}, your {r.NEXT_RENEWAL_PRODUCT} policy {r.NEXT_RENEWAL_POLICY_ID} renews on {ren}. Renew in one click and keep your benefits: [link]",
            "CROSS_SELL": f"Hi {first}, as a valued Kavach customer you are eligible for up to 10% multi-policy discount on {xsell}. Shall our advisor share a quick quote?",
            "ADVOCACY": f"Hi {first}, thank you for your kind words about Kavach! Refer a friend and you both get a ₹500 voucher on renewal.",
            "NURTURE": None,
        }[cat]
        key = {"RETENTION_CALL": "CANCEL", "CLAIM_ESCALATION": "CLAIM", "PRICE_MATCH": "PRICE",
               "CROSS_SELL": "UPSELL", "ADVOCACY": "PRAISE"}.get(cat)
        evidence = ev[key].get(r.CUSTOMER_ID) if key else None
        evidence = (evidence or ev_any.get(r.CUSTOMER_ID) or [])[:3]
        drv = sorted(json.loads(r.RISK_DRIVERS), key=lambda d: -d["points"])
        top = "; ".join([d["factor"] for d in drv if d["points"] > 0][:2]) or "none"
        rows.append({
            "CUSTOMER_ID": r.CUSTOMER_ID, "FULL_NAME": r.FULL_NAME, "SEGMENT": r.SEGMENT, "CITY": r.CITY,
            "PRODUCT_LINES": r.PRODUCT_LINES, "TOTAL_ANNUAL_PREMIUM": r.TOTAL_ANNUAL_PREMIUM,
            "NEXT_RENEWAL_POLICY_ID": r.NEXT_RENEWAL_POLICY_ID, "NEXT_RENEWAL_PRODUCT": r.NEXT_RENEWAL_PRODUCT,
            "NEXT_RENEWAL_DATE": r.NEXT_RENEWAL_DATE, "DAYS_TO_RENEWAL": r.DAYS_TO_RENEWAL,
            "RISK_SCORE": r.RISK_SCORE, "RISK_BAND": r.RISK_BAND, "RISK_DRIVERS": r.RISK_DRIVERS,
            "EXPECTED_PREMIUM_LOSS": r.EXPECTED_PREMIUM_LOSS,
            "PREMIUM_AT_RISK": r.TOTAL_ANNUAL_PREMIUM if r.RISK_BAND == "High" else 0,
            "ACTION_CATEGORY": cat, "ACTION": action,
            "REASON": f"Rule engine: {cat} — top drivers: {top}",
            "EVIDENCE": json.dumps(evidence), "CUSTOMER_MESSAGE": msg, "CHANNEL": r.PREFERRED_CHANNEL,
            "RULE_CATEGORY": cat, "GENERATED_BY": "local-sim rule-engine",
            "GENERATED_AT": pd.Timestamp(datetime.now()).floor("s"),
        })
    return pd.DataFrame(rows)


def main():
    rd = lambda n, d=(): pd.read_csv(RAW / f"{n}.csv", parse_dates=list(d))  # noqa: E731
    cus = rd("customers", ["CUSTOMER_SINCE"])
    pol = rd("policies", ["START_DATE", "RENEWAL_DATE"])
    clm = rd("claims", ["CLAIM_DATE", "SETTLED_DATE"])
    pay = rd("payments", ["DUE_DATE", "PAID_DATE"])
    trn = rd("call_transcripts", ["CALL_TS"])

    ins = interaction_insights(trn)
    c360 = customer_360(cus, pol, clm, pay, trn, ins)
    risk = churn_risk(c360)
    nba = next_best_actions(risk, ins)

    OUT.mkdir(exist_ok=True)
    c360.to_parquet(OUT / "customer_360.parquet", index=False)
    ins.to_parquet(OUT / "interaction_insights.parquet", index=False)
    nba.to_parquet(OUT / "next_best_actions.parquet", index=False)
    pol.to_parquet(OUT / "policies.parquet", index=False)
    clm.to_parquet(OUT / "claims.parquet", index=False)
    pay.to_parquet(OUT / "payments.parquet", index=False)
    (OUT / "meta.json").write_text(json.dumps({
        "source": "local-sim", "as_of": str(AS_OF.date()), "generated_at": datetime.now().isoformat(timespec="seconds"),
        "note": "Offline simulation of the Cortex pipeline. Re-export from Snowflake with scripts/export_demo_data.py for real Cortex outputs."
    }, indent=2))

    lab = pd.read_csv(RAW / "eval_transcript_labels.csv")
    acc = (ins.merge(lab, on="TRANSCRIPT_ID").eval("PRIMARY_INTENT == TRUE_INTENT")).mean()
    arch = pd.read_csv(RAW / "eval_customer_archetype.csv")
    m = nba.merge(arch, on="CUSTOMER_ID")
    print(f"insights {len(ins)} | intent agreement (sim) {acc:.1%}")
    print(nba.RISK_BAND.value_counts().to_string())
    print(pd.crosstab(m.ARCHETYPE, m.RISK_BAND))
    print(nba.ACTION_CATEGORY.value_counts().to_string())
    print(f"premium at risk (High): ₹{nba.PREMIUM_AT_RISK.sum():,.0f} of ₹{nba.TOTAL_ANNUAL_PREMIUM.sum():,.0f}")


if __name__ == "__main__":
    main()
