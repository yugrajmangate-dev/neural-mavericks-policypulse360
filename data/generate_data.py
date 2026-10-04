"""
PolicyPulse 360 — synthetic data generator (seeded, reproducible).

Creates a realistic Indian multi-line insurer dataset for the fictional
"Kavach Insurance":
  CUSTOMERS (300) · POLICIES · CLAIMS · PAYMENTS · CALL_TRANSCRIPTS (~800)

Churn signal is baked in through a hidden customer archetype:
  at_risk        -> negative calls, cancellation threats, late payments, slow claims, renewals due soon
  price_shopper  -> price-concern calls, some late payments
  growth         -> upsell-interest calls, positive
  loyal          -> praise / routine service calls, on-time payments
The archetype is NOT loaded into the CUSTOMERS table; only per-transcript
ground-truth intent labels are written to a separate eval file so the
Cortex AI_CLASSIFY output can be scored.

Usage:  python data/generate_data.py          -> writes data/raw/*.csv
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
AS_OF = date(2026, 10, 4)          # fixed "today" so the dataset is reproducible
N_CUSTOMERS = 300
OUT = Path(__file__).parent / "raw"

rng = np.random.default_rng(SEED)
random.seed(SEED)

# ----------------------------------------------------------------------------- reference data
FIRST_M = ["Aarav", "Vivaan", "Aditya", "Rohan", "Arjun", "Karthik", "Rahul", "Siddharth", "Vikram", "Manish",
           "Pranav", "Nikhil", "Sanjay", "Rajesh", "Amit", "Harish", "Imran", "Farhan", "Gurpreet", "Anil",
           "Suresh", "Venkatesh", "Deepak", "Abhishek", "Kunal", "Yash", "Tejas", "Joseph", "Naveen", "Ravi"]
FIRST_F = ["Ananya", "Priya", "Sneha", "Kavya", "Diya", "Isha", "Meera", "Pooja", "Neha", "Lakshmi",
           "Shruti", "Aditi", "Fatima", "Simran", "Divya", "Anjali", "Rekha", "Swati", "Nandini", "Harini",
           "Sana", "Ritu", "Pallavi", "Gayatri", "Tanvi", "Mary", "Bhavna", "Kiran", "Revathi", "Zoya"]
LAST = ["Sharma", "Verma", "Iyer", "Nair", "Reddy", "Patel", "Shah", "Mehta", "Gupta", "Singh", "Kulkarni",
        "Deshpande", "Joshi", "Rao", "Menon", "Pillai", "Banerjee", "Chatterjee", "Das", "Khan", "Qureshi",
        "Agarwal", "Bansal", "Chopra", "Malhotra", "Saxena", "Mishra", "Pandey", "Naidu", "Gill", "Fernandes",
        "D'Souza", "Bhat", "Hegde", "Shetty", "Sinha", "Thakur", "Jain", "Kapoor", "Mukherjee"]
CITIES = [  # city, state, tier, language
    ("Mumbai", "Maharashtra", 1, "Marathi"), ("Pune", "Maharashtra", 1, "Marathi"),
    ("Delhi", "Delhi", 1, "Hindi"), ("Bengaluru", "Karnataka", 1, "Kannada"),
    ("Chennai", "Tamil Nadu", 1, "Tamil"), ("Hyderabad", "Telangana", 1, "Telugu"),
    ("Kolkata", "West Bengal", 1, "Bengali"), ("Ahmedabad", "Gujarat", 1, "Gujarati"),
    ("Jaipur", "Rajasthan", 2, "Hindi"), ("Lucknow", "Uttar Pradesh", 2, "Hindi"),
    ("Kochi", "Kerala", 2, "Malayalam"), ("Indore", "Madhya Pradesh", 2, "Hindi"),
    ("Chandigarh", "Punjab", 2, "Punjabi"), ("Nagpur", "Maharashtra", 2, "Marathi"),
    ("Coimbatore", "Tamil Nadu", 2, "Tamil"), ("Nashik", "Maharashtra", 3, "Marathi"),
    ("Mysuru", "Karnataka", 3, "Kannada"), ("Vadodara", "Gujarat", 2, "Gujarati"),
]
CITY_W = np.array([14, 7, 13, 12, 9, 9, 7, 6, 4, 4, 3, 3, 3, 2, 2, 1, 1, 2], dtype=float)
CITY_W /= CITY_W.sum()

SEGMENTS = ["Mass", "Mass Affluent", "HNI", "SME Owner"]
SEG_W = [0.45, 0.32, 0.10, 0.13]
INCOME = {"Mass": "3-6 L", "Mass Affluent": "6-15 L", "HNI": "50 L+", "SME Owner": "15-50 L"}
CHANNELS_PREF = ["Phone", "WhatsApp", "Email", "Mobile App", "Branch"]

ARCHETYPES = ["loyal", "at_risk", "price_shopper", "growth"]
ARCH_W = [0.45, 0.25, 0.15, 0.15]

PRODUCTS = {
    "Motor":  {"plans": ["Motor Comprehensive", "Motor Third-Party Plus", "Two-Wheeler Secure"],
               "prem": (6_000, 38_000), "si": (300_000, 1_800_000)},
    "Health": {"plans": ["Health Shield Family Floater", "Health Shield Individual", "Senior Care Health",
                         "Super Top-Up"], "prem": (9_000, 62_000), "si": (500_000, 2_500_000)},
    "Life":   {"plans": ["Term Secure", "Term Secure Plus (ROP)", "Child Future Saver"],
               "prem": (11_000, 95_000), "si": (5_000_000, 20_000_000)},
    "Home":   {"plans": ["Home Protect Structure", "Home Protect Contents"],
               "prem": (2_500, 14_000), "si": (1_000_000, 8_000_000)},
}
CLAIM_TYPES = {
    "Motor": ["Accident damage", "Windshield replacement", "Theft", "Flood damage"],
    "Health": ["Hospitalisation - cashless", "Hospitalisation - reimbursement", "Day-care procedure",
               "Maternity"],
    "Life": ["Critical illness rider", "Accidental disability rider"],
    "Home": ["Water damage", "Fire damage", "Burglary"],
}
AGENTS = ["Rohit (CX-114)", "Fatima (CX-207)", "Suresh (CX-052)", "Neha (CX-318)", "Arvind (CX-091)",
          "Lakshmi (CX-276)", "Kabir (CX-133)", "Meenal (CX-402)"]
HOSPITALS = ["Apollo Hospital", "Fortis Hospital", "Manipal Hospital", "a network hospital",
             "Ruby Hall Clinic", "KIMS Hospital", "Max Hospital"]
GARAGES = ["the authorised Maruti workshop", "the network garage", "the Hyundai service centre",
           "the Tata Motors workshop"]


def rdate(start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=int(rng.integers(0, max(span, 1))))


def inr(x: float) -> str:
    """Indian digit grouping: 1234567 -> 12,34,567"""
    s = str(int(round(x)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


# ----------------------------------------------------------------------------- customers
def make_customers() -> pd.DataFrame:
    rows = []
    for i in range(1, N_CUSTOMERS + 1):
        gender = rng.choice(["M", "F"], p=[0.55, 0.45])
        first = random.choice(FIRST_M if gender == "M" else FIRST_F)
        last = random.choice(LAST)
        city, state, tier, lang = CITIES[rng.choice(len(CITIES), p=CITY_W)]
        seg = rng.choice(SEGMENTS, p=SEG_W)
        arch = rng.choice(ARCHETYPES, p=ARCH_W)
        age = int(np.clip(rng.normal(41, 11), 22, 74))
        tenure = int(np.clip(rng.gamma(2.2, 2.4), 0, 18))
        if arch == "loyal":
            tenure = max(tenure, int(rng.integers(3, 12)))
        if arch == "price_shopper":
            tenure = min(tenure, int(rng.integers(0, 4)))
        joined = AS_OF - timedelta(days=int(tenure * 365 + rng.integers(0, 360)))
        pref_lang = lang if rng.random() < 0.35 else ("Hindi" if rng.random() < 0.4 else "English")
        rows.append({
            "CUSTOMER_ID": f"C{i:04d}",
            "FULL_NAME": f"{first} {last}",
            "GENDER": gender,
            "AGE": age,
            "CITY": city,
            "STATE": state,
            "CITY_TIER": tier,
            "SEGMENT": seg,
            "ANNUAL_INCOME_BAND": INCOME[seg],
            "CUSTOMER_SINCE": joined,
            "TENURE_YEARS": round((AS_OF - joined).days / 365.25, 1),
            "PREFERRED_CHANNEL": rng.choice(CHANNELS_PREF, p=[0.30, 0.32, 0.13, 0.17, 0.08]),
            "PREFERRED_LANGUAGE": pref_lang,
            "EMAIL": f"{first.lower()}.{last.lower().replace(chr(39), '')}{i}@example.in",
            "MOBILE_MASKED": f"+91-9XXXXX{rng.integers(1000, 9999)}",
            "KYC_STATUS": rng.choice(["Verified", "Verified", "Verified", "Pending re-KYC"]),
            "ARCH": arch,
        })
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- policies
def make_policies(cust: pd.DataFrame) -> pd.DataFrame:
    rows, pid = [], 1
    for c in cust.itertuples():
        arch = c.ARCH
        n = rng.choice([1, 2, 3], p=[0.45, 0.38, 0.17])
        if arch == "growth":
            n = 1 if rng.random() < 0.6 else 2   # room to cross-sell
        prods = list(rng.choice(list(PRODUCTS), size=n, replace=False,
                                p=[0.36, 0.34, 0.18, 0.12]))
        for k, prod in enumerate(prods):
            spec = PRODUCTS[prod]
            seg_mult = {"Mass": 0.7, "Mass Affluent": 1.0, "HNI": 1.9, "SME Owner": 1.35}[c.SEGMENT]
            prem = float(np.clip(rng.uniform(*spec["prem"]) * seg_mult, spec["prem"][0] * 0.6, spec["prem"][1] * 2))
            prem = round(prem / 50) * 50
            si = round(rng.uniform(*spec["si"]) * seg_mult / 50_000) * 50_000
            start = rdate(max(c.CUSTOMER_SINCE, AS_OF - timedelta(days=3650)), AS_OF - timedelta(days=30))
            # renewal date: at-risk customers are concentrated in the next 60 days
            if arch == "at_risk" and k == 0:
                ren = AS_OF + timedelta(days=int(rng.integers(3, 60)))
            elif arch == "price_shopper" and k == 0:
                ren = AS_OF + timedelta(days=int(rng.integers(10, 90)))
            else:
                ren = AS_OF + timedelta(days=int(rng.integers(-20, 365)))
            status = "Active"
            if ren < AS_OF:
                status = "Grace Period" if (AS_OF - ren).days <= 15 else "Lapsed"
            if arch == "at_risk" and rng.random() < 0.06:
                status = "Cancellation Requested"
            mode = rng.choice(["Annual", "Monthly", "Quarterly"], p=[0.42, 0.38, 0.20])
            if prod == "Motor":
                mode = "Annual"
            rows.append({
                "POLICY_ID": f"KVH-{prod[:2].upper()}-{pid:05d}",
                "CUSTOMER_ID": c.CUSTOMER_ID,
                "PRODUCT_LINE": prod,
                "PLAN_NAME": random.choice(spec["plans"]),
                "SUM_INSURED": int(si),
                "ANNUAL_PREMIUM": int(prem),
                "PAYMENT_FREQUENCY": mode,
                "START_DATE": start,
                "RENEWAL_DATE": ren,
                "STATUS": status,
                "SALES_CHANNEL": rng.choice(["Agent", "Online", "Bancassurance", "Broker"], p=[0.4, 0.3, 0.2, 0.1]),
                "NCB_PCT": int(rng.choice([0, 20, 25, 35, 45, 50])) if prod == "Motor" else None,
            })
            pid += 1
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- claims
def make_claims(cust: pd.DataFrame, pol: pd.DataFrame) -> pd.DataFrame:
    arch = cust.set_index("CUSTOMER_ID")["ARCH"]
    rows, cid = [], 1
    for p in pol.itertuples():
        a = arch[p.CUSTOMER_ID]
        lam = {"at_risk": 1.1, "price_shopper": 0.35, "growth": 0.3, "loyal": 0.4}[a]
        lam *= {"Health": 1.2, "Motor": 1.0, "Home": 0.5, "Life": 0.15}[p.PRODUCT_LINE]
        for _ in range(int(rng.poisson(lam))):
            cdate = rdate(AS_OF - timedelta(days=540), AS_OF - timedelta(days=5))
            amt = float(min(p.SUM_INSURED * rng.uniform(0.02, 0.25), 900_000))
            amt = round(amt / 100) * 100
            if a == "at_risk":
                status = rng.choice(["Settled", "Pending", "Under Review", "Rejected"], p=[0.35, 0.3, 0.2, 0.15])
                dts = int(rng.integers(32, 95))
            else:
                status = rng.choice(["Settled", "Pending", "Rejected"], p=[0.88, 0.07, 0.05])
                dts = int(rng.integers(4, 24))
            settled_date = None
            if status == "Settled":
                settled_date = cdate + timedelta(days=dts)
                if settled_date > AS_OF:
                    status, settled_date = "Under Review", None
            days_open = (settled_date or AS_OF) - cdate
            approved = None
            if status == "Settled":
                approved = round(amt * rng.uniform(0.6 if a == "at_risk" else 0.85, 1.0) / 100) * 100
            rows.append({
                "CLAIM_ID": f"CLM-{cid:05d}",
                "POLICY_ID": p.POLICY_ID,
                "CUSTOMER_ID": p.CUSTOMER_ID,
                "PRODUCT_LINE": p.PRODUCT_LINE,
                "CLAIM_TYPE": random.choice(CLAIM_TYPES[p.PRODUCT_LINE]),
                "CLAIM_DATE": cdate,
                "CLAIM_AMOUNT": int(amt),
                "APPROVED_AMOUNT": approved,
                "STATUS": status,
                "SETTLED_DATE": settled_date,
                "DAYS_TO_SETTLE": dts if status == "Settled" else None,
                "DAYS_OPEN": days_open.days,
            })
            cid += 1
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- payments
def make_payments(cust: pd.DataFrame, pol: pd.DataFrame) -> pd.DataFrame:
    arch = cust.set_index("CUSTOMER_ID")["ARCH"]
    rows, n = [], 1
    for p in pol.itertuples():
        a = arch[p.CUSTOMER_ID]
        step = {"Annual": 12, "Quarterly": 3, "Monthly": 1}[p.PAYMENT_FREQUENCY]
        per = p.ANNUAL_PREMIUM / (12 // step)
        p_late, p_miss = {"at_risk": (0.32, 0.12), "price_shopper": (0.18, 0.05),
                          "growth": (0.05, 0.0), "loyal": (0.03, 0.005)}[a]
        # due dates over the last 18 months, anchored on the renewal day-of-month
        for m in range(0, 18, step):
            due = date(AS_OF.year, AS_OF.month, 1) - timedelta(days=30 * m)
            due = due.replace(day=min(p.RENEWAL_DATE.day, 28))
            if due > AS_OF or due < p.START_DATE:
                continue
            recent = m < 6
            r = rng.random()
            pl, pm = (p_late * (1.4 if recent else 0.7), p_miss * (1.5 if recent else 0.6))
            if r < pm:
                status, paid, late = "Missed", None, None
            elif r < pm + pl:
                late = int(rng.integers(6, 40))
                status, paid = "Late", due + timedelta(days=late)
                if paid > AS_OF:
                    status, paid, late = "Missed", None, None
            else:
                status, paid, late = "On-time", due - timedelta(days=int(rng.integers(0, 5))), 0
            rows.append({
                "PAYMENT_ID": f"PAY-{n:06d}",
                "POLICY_ID": p.POLICY_ID,
                "CUSTOMER_ID": p.CUSTOMER_ID,
                "DUE_DATE": due,
                "PAID_DATE": paid,
                "AMOUNT_DUE": int(round(per)),
                "AMOUNT_PAID": int(round(per)) if paid else 0,
                "PAYMENT_STATUS": status,
                "DAYS_LATE": late,
                "PAYMENT_METHOD": rng.choice(["UPI", "NACH Auto-debit", "Credit Card", "Net Banking", "Cheque"],
                                             p=[0.38, 0.27, 0.17, 0.13, 0.05]),
            })
            n += 1
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- transcripts
OPENERS = [
    "Agent: Namaste, thank you for calling Kavach Insurance, this is {agent}. How may I help you today?",
    "Agent: Good {tod}, Kavach Insurance customer care, {agent} speaking. Am I speaking with {cname}?",
    "Agent: Hello {cname} ji, this is {agent} from Kavach Insurance calling regarding your {product} policy {pid}.",
]


def _lines(intent: str, ctx: dict) -> list[str]:
    """Return 4-9 dialogue lines (after the opener) for a given intent."""
    c = ctx
    pools = {
        "claim_issue": [
            [f"Customer: I filed a claim {c['claim']} almost {c['days']} days back and it is still showing '{c['cstatus']}'.",
             "Agent: I'm sorry for the delay. Let me check the status for you.",
             f"Customer: Every time I call I'm told the documents are under verification. I already submitted the discharge summary from {c['hosp']} twice.",
             f"Agent: I can see the file is with the claims team awaiting a query response from the {c['tpa']}.",
             f"Customer: This is really frustrating. I paid ₹{c['amt']} from my own pocket and nobody is taking ownership.",
             "Agent: I completely understand. I will raise an escalation with priority.",
             "Customer: Escalation was promised last time also. If this is not settled this week I will complain to the IRDAI grievance cell.",
             "Agent: Noted, I'm raising it to the claims manager and you will get an SMS with the reference number."],
            [f"Customer: My car was damaged in an accident and it has been at {c['garage']} for {c['days']} days.",
             "Agent: I'm sorry to hear that. Has the surveyor visited?",
             "Customer: Surveyor came once, after that nothing. The garage says approval from your side is pending.",
             f"Customer: They have now approved only ₹{c['amt']} which doesn't even cover the parts. This is not what I was promised.",
             "Agent: I understand. Deductions are as per depreciation on parts, but I'll ask for a re-assessment.",
             "Customer: I have been with you for years and this is how claims are handled? Very disappointing.",
             "Agent: I apologise for the experience. I'll flag this for a senior claims officer to call you back."],
        ],
        "cancellation_intent": [
            [f"Customer: I want to know the process to cancel my {c['product']} policy {c['pid']}.",
             "Agent: May I ask the reason you are considering cancellation?",
             "Customer: Honestly the service has been poor. My claim took forever and the renewal premium has gone up again.",
             f"Customer: I have already got a quote from another insurer which is ₹{c['diff']} cheaper with better cover.",
             "Agent: I understand. Before you decide, can I check if there is a retention benefit available?",
             "Customer: I'm not very hopeful. Please just send me the cancellation form and the refund details.",
             "Agent: I'll email the form, and a senior advisor will also call you within 24 hours.",
             "Customer: Fine, but I have mostly made up my mind to port."],
            [f"Customer: I received the renewal notice for {c['pid']}. I don't think I will renew this time.",
             "Agent: I'm sorry to hear that. Could you tell me what is not working for you?",
             "Customer: Your app keeps failing during payment, my last claim was a nightmare, and nobody calls back.",
             "Customer: I want to port my policy to another company. What documents do I need?",
             "Agent: You can request portability 45 days before renewal. I'll share the checklist.",
             "Customer: Please also stop the auto-debit from my account immediately.",
             "Agent: I've noted the request to stop the NACH mandate. You'll receive a confirmation."],
        ],
        "price_concern": [
            [f"Customer: My renewal premium for {c['pid']} has increased by almost {c['pct']} percent. Why such a big jump?",
             "Agent: The increase is due to the change in age band and medical inflation adjustment.",
             f"Customer: But I didn't make any claim last year. An online aggregator is showing me a similar plan for ₹{c['diff']} less.",
             "Agent: I understand. Let me check whether a loyalty discount or a higher deductible option is available.",
             "Customer: Please do. I'm happy with the service but I can't justify paying this much more.",
             "Agent: I'll send you a revised quote by WhatsApp today.",
             "Customer: Okay, I will compare and decide before the due date."],
            [f"Customer: I'm comparing quotes for my {c['product']} renewal. Your price is higher than others.",
             "Agent: Our plan includes add-ons like zero depreciation and roadside assistance which others may not include.",
             "Customer: I understand, but I'm on a tight budget this year. Is there any discount you can offer?",
             "Agent: I can check eligibility for the no-claim bonus protector and an online payment discount.",
             "Customer: Theek hai, send me the details. If it is not competitive I may have to switch.",
             "Agent: Sure, you'll receive it in the next hour."],
        ],
        "upsell_interest": [
            [f"Customer: I recently had a baby and I want to add her to my {c['product']} policy.",
             "Agent: Congratulations! You can add a newborn at renewal or mid-term with a small additional premium.",
             "Customer: Also, is the current sum insured enough? Hospital costs in the city are very high.",
             "Agent: Many families opt for a super top-up which increases cover cost-effectively.",
             "Customer: That sounds good. Can you share the options and premium?",
             "Agent: Definitely. I'll email a comparison and a relationship manager can walk you through it.",
             "Customer: Great, thank you. The service has been good so far."],
            ["Customer: I just bought a new house and I wanted to know if you offer home insurance.",
             "Agent: Yes, we have Home Protect which covers structure and contents against fire, flood and burglary.",
             "Customer: Nice. I already have my car and health policy with you, will I get any multi-policy discount?",
             "Agent: Yes, existing customers get a bundle discount of up to 10 percent.",
             "Customer: Perfect, please send me a quote. I'm also thinking of a term plan for my family.",
             "Agent: I'll arrange a call with our advisor for both. Thank you for staying with Kavach."],
        ],
        "service_praise": [
            [f"Customer: I just wanted to say thanks. My claim {c['claim']} was settled within a week.",
             "Agent: That's wonderful to hear, thank you for the feedback!",
             f"Customer: The cashless process at {c['hosp']} was very smooth, the help desk guided us properly.",
             "Agent: We're glad it worked well. Is there anything else I can help with?",
             "Customer: No, everything is fine. I have already recommended you to my brother.",
             "Agent: Thank you so much, we really appreciate it."],
            ["Customer: I renewed my policy on the app in two minutes, it was very easy.",
             "Agent: Great to hear! Did you receive the policy document?",
             "Customer: Yes, got it on WhatsApp and email immediately. Very convenient.",
             "Agent: Wonderful. Is there anything else you need today?",
             "Customer: No, all good. Keep it up."],
        ],
        "general_service": [
            ["Customer: I need to update my address in my policy records. I've moved recently.",
             "Agent: Sure, you can upload the address proof on the app or email it to us.",
             "Customer: Okay, and will the policy document be reissued?",
             "Agent: Yes, an endorsement will be issued within 3 working days.",
             "Customer: Fine, thank you."],
            [f"Customer: I need a premium paid certificate for {c['pid']} for my tax filing.",
             "Agent: I can email that to your registered email right now.",
             "Customer: Also please confirm my nominee details are updated.",
             "Agent: Yes, your spouse is listed as the nominee. Anything else?",
             "Customer: No, that's all, thanks."],
            ["Customer: I haven't received my renewal reminder, can you tell me when my policy is due?",
             f"Agent: Your policy {c['pid']} is due for renewal on {c['ren']}.",
             "Customer: Okay. Can I set up auto-debit so I don't miss it?",
             "Agent: Yes, I'll send you the e-NACH registration link on SMS.",
             "Customer: Thank you."],
        ],
    }
    lines = list(random.choice(pools[intent]))
    # light variation: occasionally drop one middle line to vary length (keeps 6-12 lines total)
    if len(lines) > 6 and random.random() < 0.4:
        lines.pop(random.randrange(1, len(lines) - 1))
    return lines


CLOSERS = {
    "claim_issue": ["Agent: Is there anything else I can help you with?", "Customer: No. Just get this resolved."],
    "cancellation_intent": ["Agent: Thank you for your time, someone will call you shortly.", "Customer: Okay."],
    "price_concern": ["Agent: Thank you for calling Kavach Insurance."],
    "upsell_interest": ["Agent: Thank you, have a great day!"],
    "service_praise": ["Agent: Thank you for choosing Kavach Insurance. Have a lovely day!"],
    "general_service": ["Agent: Thank you for calling, have a good day."],
}
INTENT_MIX = {
    "at_risk":       (["claim_issue", "cancellation_intent", "price_concern", "general_service"], [0.40, 0.35, 0.15, 0.10], (3, 5)),
    "price_shopper": (["price_concern", "cancellation_intent", "general_service", "claim_issue", "upsell_interest"], [0.55, 0.15, 0.15, 0.10, 0.05], (2, 4)),
    "growth":        (["upsell_interest", "service_praise", "general_service"], [0.50, 0.25, 0.25], (2, 3)),
    "loyal":         (["service_praise", "general_service", "upsell_interest", "claim_issue"], [0.35, 0.40, 0.15, 0.10], (1, 3)),
}


def make_transcripts(cust, pol, clm) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, labels, tid = [], [], 1
    pol_by_c = pol.groupby("CUSTOMER_ID")
    clm_by_c = {k: v for k, v in clm.groupby("CUSTOMER_ID")}
    for c in cust.itertuples():
        intents, w, (lo, hi) = INTENT_MIX[c.ARCH]
        n = int(rng.integers(lo, hi + 1))
        dates = sorted(rdate(AS_OF - timedelta(days=180), AS_OF - timedelta(days=1)) for _ in range(n))
        chosen = list(rng.choice(intents, size=n, p=w))
        if c.ARCH == "at_risk":
            # deteriorating journey: routine first, escalation later
            order = {"general_service": 0, "price_concern": 1, "claim_issue": 2, "cancellation_intent": 3}
            chosen.sort(key=lambda x: order.get(x, 1))
        cpols = pol_by_c.get_group(c.CUSTOMER_ID)
        for d, intent in zip(dates, chosen):
            p = cpols.sample(1, random_state=int(rng.integers(0, 1e6))).iloc[0]
            cc = clm_by_c.get(c.CUSTOMER_ID)
            claim_id = cc.iloc[0]["CLAIM_ID"] if cc is not None and len(cc) else f"CLM-{rng.integers(90000, 99999)}"
            agent = random.choice(AGENTS)
            ctx = {
                "agent": agent.split(" ")[0], "cname": c.FULL_NAME.split()[0],
                "tod": random.choice(["morning", "afternoon", "evening"]),
                "product": p.PRODUCT_LINE.lower(), "pid": p.POLICY_ID, "claim": claim_id,
                "days": int(rng.integers(25, 80)), "cstatus": random.choice(["Under Review", "Pending documents", "Query raised"]),
                "hosp": random.choice(HOSPITALS), "garage": random.choice(GARAGES),
                "tpa": random.choice(["TPA", "hospital", "surveyor"]),
                "amt": inr(rng.integers(18, 260) * 1000), "diff": inr(rng.integers(2, 15) * 500),
                "pct": int(rng.integers(14, 38)), "ren": p.RENEWAL_DATE.strftime("%d %b %Y"),
            }
            opener = random.choice(OPENERS).format(**ctx)
            body = _lines(intent, ctx)
            text = "\n".join([opener] + body + CLOSERS[intent])
            rows.append({
                "TRANSCRIPT_ID": f"T{tid:05d}",
                "CUSTOMER_ID": c.CUSTOMER_ID,
                "POLICY_ID": p.POLICY_ID,
                "CALL_TS": pd.Timestamp(d) + pd.Timedelta(minutes=int(rng.integers(9 * 60, 20 * 60))),
                "DIRECTION": "Outbound" if opener.startswith("Agent: Hello") else "Inbound",
                "CHANNEL": "Voice" if rng.random() < 0.85 else "Video KYC/Call",
                "AGENT_ID": agent,
                "DURATION_SEC": int(len(text) / 4 + rng.integers(60, 420)),
                "LANGUAGE": "English" if rng.random() < 0.7 else "Hinglish",
                "TRANSCRIPT_TEXT": text,
            })
            labels.append({"TRANSCRIPT_ID": f"T{tid:05d}", "TRUE_INTENT": intent})
            tid += 1
    return pd.DataFrame(rows), pd.DataFrame(labels)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cust = make_customers()
    pol = make_policies(cust)
    clm = make_claims(cust, pol)
    pay = make_payments(cust, pol)
    trn, lab = make_transcripts(cust, pol, clm)

    for df, cols in [(pol, ["NCB_PCT"]), (clm, ["APPROVED_AMOUNT", "DAYS_TO_SETTLE"]), (pay, ["DAYS_LATE"])]:
        for col in cols:
            df[col] = df[col].astype("Int64")   # nullable int -> "20" not "20.0" in CSV
    cust.drop(columns=["ARCH"]).to_csv(OUT / "customers.csv", index=False)
    pol.to_csv(OUT / "policies.csv", index=False)
    clm.to_csv(OUT / "claims.csv", index=False)
    pay.to_csv(OUT / "payments.csv", index=False)
    trn.to_csv(OUT / "call_transcripts.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
    lab.to_csv(OUT / "eval_transcript_labels.csv", index=False)
    # hidden archetype kept only for offline evaluation of the risk score (not loaded into RAW tables)
    cust[["CUSTOMER_ID", "ARCH"]].rename(columns={"ARCH": "ARCHETYPE"}).to_csv(OUT / "eval_customer_archetype.csv", index=False)

    for name, df in [("customers", cust), ("policies", pol), ("claims", clm), ("payments", pay),
                     ("call_transcripts", trn)]:
        print(f"{name:18s} {len(df):6d} rows")
    print(f"total annual premium ₹{inr(pol['ANNUAL_PREMIUM'].sum())}")


if __name__ == "__main__":
    main()
