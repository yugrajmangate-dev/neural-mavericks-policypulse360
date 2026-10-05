---
name: next-best-action
description: Score explainable churn risk for every insurance customer from the Customer 360 and AI interaction insights, then generate a grounded next best action (action, reason, evidence transcript IDs, ready-to-send customer message) with Cortex AI_COMPLETE into APP.NEXT_BEST_ACTIONS. Use when the user asks who is at risk of churning, what to do for a customer, premium at risk, or retention/upsell recommendations.
---

# next-best-action — Explainable churn risk + grounded NBA

## When to Use
- "Who are my top at-risk customers and why?" or "How much premium is at risk?"
- "What should I do for customer C0042 / Priya Iyer?"
- "Which health policyholders renewing next month are at high churn risk?"
- Final step of the chain: `$c360-unify` → `$interaction-intel` → **`$next-best-action`**

## What This Skill Provides
1. **`APP.CHURN_RISK`** (view) is a transparent 0–100 score. Every point traces to a driver:

| Driver | Max pts | Rule |
|---|---|---|
| Negative sentiment | 25 | 25 × clamp((0.25 − avg customer sentiment over 90d) / 1.0, 0, 1) |
| Cancellation or porting intent | 20 | 20 if a call in the last 90d, 8 if only in days 91–180 |
| Price sensitivity | 10 | price-concern call in the last 90d |
| Payment stress | 15 | 15 × min(1, (late + 2 × missed over 12m) / 4) |
| Claim friction | 15 | 15 × min(1, (slow or open >30d + rejected claims) / 2) |
| Renewal proximity | 15 | ≤30d: 15 · ≤60d: 10 · ≤90d: 5 |
| Long tenure (protective) | −5 | ≥ 8 years |
| Recent praise (protective) | −5 | service-praise call in the last 180d |

   Bands: **High ≥ 55**, **Medium 30–54**, **Low < 30**.
2. **`APP.NBA_CONTEXT`** has a rule-engine baseline action for every customer, plus a grounded prompt
   (360 JSON + risk drivers + last 4 call summaries with transcript IDs).
3. **`APP.NBA_LLM`** runs `AI_COMPLETE('openai-gpt-4.1')` for High and Medium risk customers and anyone with upsell signals.
   Incremental: each run adds the next 50 highest-risk customers (re-run to extend coverage).
4. **`APP.NEXT_BEST_ACTIONS`** is the serving table: ACTION_CATEGORY, ACTION, REASON, EVIDENCE (transcript IDs),
   CUSTOMER_MESSAGE, CHANNEL, PREMIUM_AT_RISK and GENERATED_BY. It uses the LLM output when the JSON is valid and the rule baseline otherwise.

## Instructions
1. Check that `CURATED.CUSTOMER_360` and `CURATED.INTERACTION_INSIGHTS` exist and the latter has rows.
   If not, run `$c360-unify` and/or `$interaction-intel` first, and tell the user you're chaining them.
2. Execute `.cortex/skills/next-best-action/churn_risk.sql`, then `next_best_action.sql`, on `POLICYPULSE_WH`.
   - If `openai-gpt-4.1` is unavailable, replace it with `llama3.1-70b` in both files and re-run.
3. Report three things: customers per risk band, ₹ premium at risk (sum of TOTAL_ANNUAL_PREMIUM where RISK_BAND = 'High'),
   and the top 5 at-risk customers with their ACTION and REASON.
4. **Single customer** ("what should I do for C0042?"): run `SET CID = '<id>';`, then
   `.cortex/skills/next-best-action/nba_for_customer.sql`. Present:
   - Risk score and band, with the top drivers and their points
   - **Next best action**, reason, and the evidence transcript IDs (offer to show those transcripts' summaries)
   - The customer message, in a code block so it's easy to copy
5. **Portfolio question in plain English**: translate it into SQL over `APP.NEXT_BEST_ACTIONS` joined to
   `RAW.POLICIES` and `CURATED.CUSTOMER_360` as needed. For example, health renewals next month:
   ```sql
   SELECT n.CUSTOMER_ID, n.FULL_NAME, n.RISK_SCORE, n.ACTION, n.REASON, p.POLICY_ID, p.RENEWAL_DATE, p.ANNUAL_PREMIUM
   FROM POLICYPULSE.APP.NEXT_BEST_ACTIONS n
   JOIN POLICYPULSE.RAW.POLICIES p ON p.CUSTOMER_ID = n.CUSTOMER_ID
   WHERE p.PRODUCT_LINE = 'Health' AND n.RISK_BAND = 'High'
     AND p.RENEWAL_DATE BETWEEN DATEADD('month', 1, DATE_TRUNC('month', POLICYPULSE.CURATED.AS_OF_DATE()))
                            AND LAST_DAY(DATEADD('month', 1, POLICYPULSE.CURATED.AS_OF_DATE()))
   ORDER BY n.RISK_SCORE DESC;
   ```
6. Offer to refresh the Streamlit demo data with `python scripts/export_demo_data.py`.

## Guardrails
- Recommendations must cite only facts in the customer's 360 row and transcripts. Never invent claim IDs or discounts above 10%.
- Explain the score through its drivers. Never describe it as a black-box model.
