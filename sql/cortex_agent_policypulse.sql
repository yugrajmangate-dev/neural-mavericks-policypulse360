-- =====================================================================
-- PolicyPulse 360 — Cortex Agent "PolicyPulse Copilot"
--   Orchestrates two tools:
--     retention_analyst  : Cortex Analyst text-to-SQL over APP.CUSTOMER_360_SV (numbers, lists, KPIs)
--     transcript_search  : Cortex Search over CURATED.TRANSCRIPT_SEARCH (what customers actually said)
--   Every answer cites transcript IDs as evidence and ends with a recommended action.
-- Requires: sql/semantic_view_customer360.sql and sql/cortex_search_transcripts.sql.
-- Privileges: CREATE AGENT on schema APP; USAGE on the search service, semantic view, tables and warehouse;
--             a role that can use Cortex Agents (SNOWFLAKE.CORTEX_USER database role).
-- Also visible in Snowsight > AI & ML > Agents. To list it in Snowflake Intelligence, create it in
-- SNOWFLAKE_INTELLIGENCE.AGENTS instead (same spec).
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.APP;

CREATE OR REPLACE AGENT POLICYPULSE.APP.POLICYPULSE_COPILOT
  COMMENT = 'PolicyPulse Copilot: retention Q&A over the insurance Customer 360 with cited call evidence'
  PROFILE = '{"display_name": "PolicyPulse Copilot", "color": "blue"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto

  orchestration:
    budget:
      seconds: 60
      tokens: 16000

  instructions:
    orchestration: >
      You help retention agents at Kavach Insurance, an Indian insurer, decide who to call and what to do.
      Use retention_analyst for anything numeric or list-shaped, such as churn rate, premium at risk,
      renewals due, risk bands, segments, products, claim settlement days or top-N customers.
      Use transcript_search to find what customers actually said, and to fetch evidence for a named customer
      by filtering on CUSTOMER_ID. When a question is about specific customers, call retention_analyst first to
      identify them, then transcript_search to pull their supporting calls.
      Treat churn as predicted churn risk: High means churn_risk_band = High (score 55 or more).
    response: >
      Be concise and business-friendly. Format money in Indian rupees using lakh and crore.
      Always cite evidence as transcript IDs in square brackets, for example [T00042], taken only from tool results.
      Never invent transcript IDs, customer IDs, figures or discounts above 10 percent.
      End every answer with a line that starts with "Recommended action:" naming the action, the customer or
      segment it applies to, and the channel. If the data does not support an answer, say so plainly.
    sample_questions:
      - question: "Which health policyholders renewing in the next 30 days are at high churn risk, and why?"
      - question: "How much annual premium is at risk, by customer segment?"
      - question: "Why is customer C0004 unhappy, and what should I do today?"
      - question: "Which customers complained about claims stuck on hospital documents?"

  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "retention_analyst"
        description: >
          Text-to-SQL over the PolicyPulse semantic view: one row per customer with profile, products,
          annual premium, next renewal and days until renewal, claims and payment behaviour, churn risk score
          and band, premium at risk, the recommended next best action, its reason and evidence transcript IDs,
          plus per-call sentiment and intent.
    - tool_spec:
        type: "cortex_search"
        name: "transcript_search"
        description: >
          Semantic search over call-centre transcripts with AI summaries. Filterable by CUSTOMER_ID,
          PRIMARY_INTENT (cancellation_intent, claim_issue, price_concern, upsell_interest, service_praise,
          general_service), SENTIMENT_LABEL (negative, neutral, positive) and POLICY_ID. Returns TRANSCRIPT_ID
          to cite as evidence.

  tool_resources:
    retention_analyst:
      semantic_view: "POLICYPULSE.APP.CUSTOMER_360_SV"
      execution_environment:
        type: "warehouse"
        warehouse: "POLICYPULSE_WH"
    transcript_search:
      search_service: "POLICYPULSE.CURATED.TRANSCRIPT_SEARCH"
      max_results: "5"
      id_column: "TRANSCRIPT_ID"
      title_column: "SUMMARY"
  $$;

SHOW AGENTS IN SCHEMA POLICYPULSE.APP;

-- Smoke test (one agent run; returns JSON with content[] items of type text / tool_use / tool_result).
-- Kept commented so re-running this file does not spend tokens; scripts/run_upgrades.py --smoke runs it.
-- SELECT c.value:text::STRING AS ANSWER
-- FROM (SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
--         'POLICYPULSE.APP.POLICYPULSE_COPILOT',
--         $${"messages": [{"role": "user", "content": [{"type": "text",
--            "text": "Why is customer C0004 at risk and what should I do today? Cite transcripts."}]}]}$$)) AS J) r,
--      LATERAL FLATTEN(INPUT => r.J:content) c
-- WHERE c.value:type::STRING = 'text';
