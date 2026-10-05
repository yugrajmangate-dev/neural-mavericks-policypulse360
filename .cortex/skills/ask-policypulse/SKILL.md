---
name: ask-policypulse
description: Ask the PolicyPulse Copilot (a Snowflake Cortex Agent combining Cortex Analyst on the Customer 360 semantic view and Cortex Search on call transcripts) a plain-English retention question, and return a cited answer (transcript IDs) plus a recommended action. Use when the user asks an open retention question such as who to call, why a customer is unhappy, premium at risk by segment, or which customers complained about something.
---

# ask-policypulse — Cited answers from the PolicyPulse Copilot

## When to Use
- "Which health policyholders renewing in the next 30 days are at high churn risk, and why?"
- "Why is C0004 unhappy, and what should I do today?"
- "Which customers complained about claims stuck on hospital documents?"
- "How much premium is at risk by segment, and which play should we run first?"
- Fourth step, after the chain: `$c360-unify` → `$interaction-intel` → `$next-best-action` → **`$ask-policypulse`**

## What This Skill Provides
| Object | Created by | Role |
|---|---|---|
| `APP.CUSTOMER_360_SV` | `sql/semantic_view_customer360.sql` | Semantic view: business dimensions, metrics (churn rate, premium at risk, avg sentiment, claim settlement days, renewals due 30d) and synonyms |
| `CURATED.TRANSCRIPT_SEARCH` | `sql/cortex_search_transcripts.sql` | Cortex Search over transcripts, filterable by `CUSTOMER_ID`, `PRIMARY_INTENT`, `SENTIMENT_LABEL` |
| `APP.POLICYPULSE_COPILOT` | `sql/cortex_agent_policypulse.sql` | Cortex Agent: orchestrates both tools, cites `[T00042]`-style evidence and ends with `Recommended action:` |

## Instructions
1. **Check the objects exist** (`SHOW AGENTS IN SCHEMA POLICYPULSE.APP;`). If `POLICYPULSE_COPILOT` is missing, run
   `python scripts/run_upgrades.py` from the repo root. It needs the base chain outputs, so if it reports missing
   tables, run `$c360-unify`, `$interaction-intel` and `$next-best-action` first and tell the user you're chaining them.
2. **Ask the agent.** Set the question, then execute `.cortex/skills/ask-policypulse/ask.sql` on `POLICYPULSE_WH`:
   ```sql
   SET Q = 'Which health policyholders renewing in the next 30 days are at high churn risk, and why?';
   ```
   The file returns `ANSWER` (the agent's text), `TOOLS_USED`, `EVIDENCE_IDS` (transcript IDs in the answer) and `SQL_USED`
   (the Cortex Analyst query, if any).
3. **Present the result** in this order:
   - The answer, kept short, with transcript IDs in brackets left exactly as returned.
   - **Evidence**: for up to 5 IDs in `EVIDENCE_IDS`, show date, intent, sentiment and summary:
     ```sql
     SELECT TRANSCRIPT_ID, CALL_TS::DATE AS CALL_DATE, PRIMARY_INTENT, ROUND(SENTIMENT_SCORE, 2) AS SENTIMENT, SUMMARY
     FROM POLICYPULSE.CURATED.INTERACTION_INSIGHTS
     WHERE ARRAY_CONTAINS(TRANSCRIPT_ID::VARIANT, PARSE_JSON('<EVIDENCE_IDS json>'))
     ORDER BY CALL_TS DESC;
     ```
   - **Recommended action**: copy the agent's `Recommended action:` line. If one customer is named, also show their stored
     next best action and message from `APP.NEXT_BEST_ACTIONS` in a code block.
   - Offer to log the decision: `INSERT INTO POLICYPULSE.APP.ACTION_LOG (CUSTOMER_ID, ACTION_CATEGORY, ACTION, STATUS, AGENT, NOTE)
     SELECT '<id>', '<category>', '<action>', 'Accepted', CURRENT_USER(), 'via $ask-policypulse';`
4. **Follow-ups**: re-run step 2 with the new question. The agent is stateless here, so put the needed context
   (customer ID, segment) in the question.
5. **Fallback if the agent errors** (for example, the orchestration model isn't available in the region):
   - Numbers: query the semantic view directly, for example
     ```sql
     SELECT * FROM SEMANTIC_VIEW(POLICYPULSE.APP.CUSTOMER_360_SV
       DIMENSIONS c360.customer_segment
       METRICS nba.at_risk_premium, nba.churn_rate, c360.renewals_due_30d)
     ORDER BY at_risk_premium DESC;
     ```
   - Evidence: `SNOWFLAKE.CORTEX.SEARCH_PREVIEW('POLICYPULSE.CURATED.TRANSCRIPT_SEARCH', ...)` with a
     `{"@eq": {"CUSTOMER_ID": "<id>"}}` filter (see `sql/cortex_search_transcripts.sql`).
   - Then write the answer yourself in the same format: cited IDs, then `Recommended action:`.

## Guardrails
- Cite only transcript IDs returned by the tools. Never invent IDs, figures or discounts above 10%.
- "Churn" means **predicted** churn risk (High band, score ≥ 55), not realised lapses. Say so if the user asks about actual churn.
- Read-only, except for an `ACTION_LOG` insert the user explicitly confirms.
- Each agent call costs tokens, so don't loop it over many customers. Use the semantic view for lists.
