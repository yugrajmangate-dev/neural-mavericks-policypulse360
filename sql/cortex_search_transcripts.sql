-- =====================================================================
-- PolicyPulse 360 — Cortex Search service over call-centre transcripts
--   CURATED.TRANSCRIPT_SEARCH: hybrid (vector + keyword) search over what customers said, with
--   CUSTOMER_ID, PRIMARY_INTENT and SENTIMENT_LABEL as filterable attributes.
--   Used by the PolicyPulse Copilot agent (sql/cortex_agent_policypulse.sql) to cite evidence.
-- Requires: Skill 2 (interaction-intel) output CURATED.INTERACTION_INSIGHTS.
-- Cost: a search service has a small always-on serving cost. DROP it after the demo (bottom of file,
--       or `python scripts/run_upgrades.py --teardown`).
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.CURATED;

CREATE OR REPLACE CORTEX SEARCH SERVICE POLICYPULSE.CURATED.TRANSCRIPT_SEARCH
  ON SEARCH_TEXT
  ATTRIBUTES CUSTOMER_ID, PRIMARY_INTENT, SENTIMENT_LABEL, POLICY_ID
  WAREHOUSE = POLICYPULSE_WH
  TARGET_LAG = '1 day'
  COMMENT = 'PolicyPulse: semantic search over call transcripts (filter by customer, intent, sentiment)'
AS (
  SELECT
    TRANSCRIPT_ID,
    CUSTOMER_ID,
    COALESCE(POLICY_ID, '')                      AS POLICY_ID,
    TO_VARCHAR(CALL_TS, 'YYYY-MM-DD')            AS CALL_DATE,
    PRIMARY_INTENT,
    SENTIMENT_LABEL,
    ROUND(SENTIMENT_SCORE, 2)::VARCHAR           AS SENTIMENT_SCORE,
    SUMMARY,
    TRANSCRIPT_TEXT,
    -- summary first so short queries match the AI gist as well as the raw dialogue
    COALESCE(SUMMARY, '') || '\n' || COALESCE(TRANSCRIPT_TEXT, '') AS SEARCH_TEXT
  FROM POLICYPULSE.CURATED.INTERACTION_INSIGHTS
);

-- Smoke test: negative-sentiment calls about stuck cashless hospital claims
SELECT PARSE_JSON(
  SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'POLICYPULSE.CURATED.TRANSCRIPT_SEARCH',
    '{"query": "hospital discharge summary submitted twice, claim still pending",
      "columns": ["TRANSCRIPT_ID", "CUSTOMER_ID", "CALL_DATE", "PRIMARY_INTENT", "SENTIMENT_LABEL", "SUMMARY"],
      "filter": {"@and": [{"@eq": {"SENTIMENT_LABEL": "negative"}}, {"@eq": {"PRIMARY_INTENT": "claim_issue"}}]},
      "limit": 5}'
  )
):results AS RESULTS;

-- Per-customer evidence lookup (what the agent does when asked about one customer):
-- SELECT PARSE_JSON(SNOWFLAKE.CORTEX.SEARCH_PREVIEW('POLICYPULSE.CURATED.TRANSCRIPT_SEARCH',
--   '{"query": "cancel or port my policy", "columns": ["TRANSCRIPT_ID","CALL_DATE","SUMMARY"],
--     "filter": {"@eq": {"CUSTOMER_ID": "C0004"}}, "limit": 3}')):results;

-- ---------------------------------------------------------------------------------------------
-- AFTER THE DEMO: drop the service to stop serving costs (the agent's search tool stops working).
-- DROP CORTEX SEARCH SERVICE IF EXISTS POLICYPULSE.CURATED.TRANSCRIPT_SEARCH;
