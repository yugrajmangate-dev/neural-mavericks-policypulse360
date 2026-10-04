---
name: c360-unify
description: Build the PolicyPulse unified Customer 360 view in Snowflake by joining policy admin, claims, payments and call-centre interaction data into CURATED.CUSTOMER_360. Use when the user asks to unify customer data, build or refresh the customer 360, or look up a single customer's full profile.
---

# c360-unify — Unified Customer 360

## When to Use
- "Unify / build / refresh the customer 360"
- "Show me everything we know about customer C0042 / <name>"
- First step of the PolicyPulse chain: `$c360-unify` → `$interaction-intel` → `$next-best-action`

## What This Skill Provides
`POLICYPULSE.CURATED.CUSTOMER_360` is a **view** with one row per customer. It unifies:

| Source (RAW) | System | Signals in the 360 |
|---|---|---|
| CUSTOMERS | CRM / KYC | demographics, segment, tenure, city, preferred channel and language |
| POLICIES | Policy admin | active policies, product mix, total ₹ premium, **next renewal and days left** |
| CLAIMS | Claims | open, slow (>30 days) and rejected claims, average days to settle |
| PAYMENTS | Billing | late and missed payments over 12 months, on-time rate |
| CALL_TRANSCRIPTS | Call centre | call volume (180 days) |
| CURATED.INTERACTION_INSIGHTS | Skill 2 output | avg sentiment (90d), last intent, cancellation, price, upsell and praise counts |

It also creates `CURATED.AS_OF_DATE()` (pinned to 2026-10-04 for the synthetic data) and an empty
`CURATED.INTERACTION_INSIGHTS` table if it doesn't exist yet. That lets this skill run **standalone**: AI columns
are NULL until `$interaction-intel` runs, then fill in automatically because the 360 is a view.

## Instructions
1. Confirm the active connection can see `POLICYPULSE.RAW` (`SHOW TABLES IN SCHEMA POLICYPULSE.RAW;`).
   If the database is missing, run `python scripts/load_to_snowflake.py` from the repo root first
   (it runs `sql/00_setup.sql` and `sql/01_load_from_stage.sql`).
2. Execute every statement in `.cortex/skills/c360-unify/c360_unify.sql` in order, using warehouse `POLICYPULSE_WH`.
3. Show the user the final validation row (customers, coverage per source, total premium in ₹).
4. If the user named a customer, run:
   ```sql
   SELECT * FROM POLICYPULSE.CURATED.CUSTOMER_360
   WHERE CUSTOMER_ID = '<id>' OR FULL_NAME ILIKE '%<name>%';
   ```
   Then present it as a short profile: policies, claims, payments and interactions. Format money as ₹ with Indian grouping.
5. Suggest the next step: `$interaction-intel` to add AI sentiment and intent from call transcripts.

## Guardrails
- Use the XS warehouse `POLICYPULSE_WH` only. Never resize it.
- This skill creates only views and one function, so it costs no Cortex credits.
