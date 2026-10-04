-- =====================================================================
-- Skill 2 · optional — Cortex Search service over enriched transcripts
-- Lets agents (and the app's chat box in LIVE mode) semantically search what customers said.
-- Cost note: a search service has a small always-on serving cost. Drop it after the demo:
--   DROP CORTEX SEARCH SERVICE POLICYPULSE.CURATED.TRANSCRIPT_SEARCH;
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.CURATED;

CREATE OR REPLACE CORTEX SEARCH SERVICE CURATED.TRANSCRIPT_SEARCH
  ON TRANSCRIPT_TEXT
  ATTRIBUTES CUSTOMER_ID, PRIMARY_INTENT, SENTIMENT_LABEL
  WAREHOUSE = POLICYPULSE_WH
  TARGET_LAG = '1 day'
  COMMENT = 'Semantic search over call-centre transcripts'
AS (
  SELECT TRANSCRIPT_ID, CUSTOMER_ID, CALL_TS::VARCHAR AS CALL_TS, PRIMARY_INTENT, SENTIMENT_LABEL,
         SUMMARY, TRANSCRIPT_TEXT
  FROM CURATED.INTERACTION_INSIGHTS
);

-- Example: find customers complaining about cashless hospital claims stuck on documents
SELECT PARSE_JSON(
  SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'POLICYPULSE.CURATED.TRANSCRIPT_SEARCH',
    '{"query": "hospital discharge summary submitted twice claim still pending",
      "columns": ["TRANSCRIPT_ID", "CUSTOMER_ID", "PRIMARY_INTENT", "SUMMARY"],
      "filter": {"@eq": {"SENTIMENT_LABEL": "negative"}},
      "limit": 5}'
  )
):results AS RESULTS;
