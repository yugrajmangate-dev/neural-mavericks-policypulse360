---
name: interaction-intel
description: Run Snowflake Cortex AI SQL over insurance call-centre transcripts to extract customer sentiment, primary intent (claim_issue, price_concern, cancellation_intent, upsell_interest, service_praise, general_service) and a one-line summary into CURATED.INTERACTION_INSIGHTS, and optionally build a Cortex Search service. Use when the user asks to analyse calls, transcripts, sentiment, complaints or intents.
---

# interaction-intel — Unstructured → structured with Cortex AI

## When to Use
- "Analyse the call transcripts", "what are customers complaining about?", "sentiment by product"
- "Why is customer C0042 unhappy?" (show their enriched calls)
- Second step of the chain: `$c360-unify` → **`$interaction-intel`** → `$next-best-action`

## What This Skill Provides
`POLICYPULSE.CURATED.INTERACTION_INSIGHTS` holds one row per transcript:

| Column | How |
|---|---|
| SENTIMENT_SCORE (-1…1) and SENTIMENT_LABEL | `SNOWFLAKE.CORTEX.SENTIMENT` on the **customer's lines only**, because agent politeness skews sentiment |
| PRIMARY_INTENT | `AI_CLASSIFY` with 6 labels, each with a business description and a task description |
| SUMMARY | `AI_COMPLETE('llama3.1-70b', …)`: one sentence of ≤25 words for the agent |

The run is **incremental**: only transcripts not yet enriched go to Cortex, so re-runs are near-free.
At the end it scores AI_CLASSIFY against `RAW.EVAL_TRANSCRIPT_LABELS` (synthetic ground truth) and reports accuracy.

## Instructions
1. Make sure `$c360-unify` has run (it's fine if it hasn't: this skill creates its own output table).
2. Execute `.cortex/skills/interaction-intel/interaction_intel.sql` on warehouse `POLICYPULSE_WH`.
   - If you get an "unknown function AI_CLASSIFY / AI_COMPLETE" error or a model-unavailable error, run
     `interaction_intel_fallback.sql` instead (it uses SNOWFLAKE.CORTEX.CLASSIFY_TEXT and SUMMARIZE), and tell the user.
   - If a model isn't available in the region, either suggest `ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';`
     (requires ACCOUNTADMIN) or swap `llama3.1-70b` for `mistral-7b`.
3. Report three things: rows enriched, intent accuracy %, and the intent distribution with average sentiment.
4. Optional, if the user wants semantic search: run `transcript_search.sql` to create the Cortex Search service
   `CURATED.TRANSCRIPT_SEARCH` and show the example query results. Remind them to drop it after the demo.
5. For a specific customer, show:
   ```sql
   SELECT TRANSCRIPT_ID, CALL_TS::DATE AS DAY, PRIMARY_INTENT, SENTIMENT_LABEL, ROUND(SENTIMENT_SCORE,2) AS SCORE, SUMMARY
   FROM POLICYPULSE.CURATED.INTERACTION_INSIGHTS WHERE CUSTOMER_ID = '<id>' ORDER BY CALL_TS;
   ```
6. Suggest the next step: `$next-best-action`.

## Guardrails
- Never send the whole RAW table to Cortex again. Rely on the incremental `NOT EXISTS` filter.
- Never use `EVAL_TRANSCRIPT_LABELS` as model input. It exists only for scoring.
