-- =====================================================================
-- Skill 2 · interaction-intel
-- Turns unstructured call transcripts into structured signals with Cortex AI SQL:
--   SENTIMENT  -> SNOWFLAKE.CORTEX.SENTIMENT on the CUSTOMER's utterances only
--                 (agent politeness would otherwise bias every call positive)
--   INTENT     -> AI_CLASSIFY into 6 business intents
--   SUMMARY    -> AI_COMPLETE one-line agent-facing summary
-- Output: CURATED.INTERACTION_INSIGHTS (one row per transcript).
-- Cost control: incremental — only transcripts not yet enriched are sent to Cortex.
--   Full rebuild: TRUNCATE TABLE CURATED.INTERACTION_INSIGHTS; then re-run.
-- If AI_CLASSIFY / AI_COMPLETE are unavailable in your region, run
--   interaction_intel_fallback.sql (legacy SNOWFLAKE.CORTEX.* functions) instead.
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.CURATED;

CREATE TABLE IF NOT EXISTS CURATED.INTERACTION_INSIGHTS (
  TRANSCRIPT_ID VARCHAR, CUSTOMER_ID VARCHAR, POLICY_ID VARCHAR, CALL_TS TIMESTAMP_NTZ, AGENT_ID VARCHAR,
  CUSTOMER_TEXT VARCHAR, SENTIMENT_SCORE FLOAT, SENTIMENT_LABEL VARCHAR, PRIMARY_INTENT VARCHAR,
  SUMMARY VARCHAR, TRANSCRIPT_TEXT VARCHAR, ENRICHED_BY VARCHAR, ENRICHED_AT TIMESTAMP_NTZ
);

INSERT INTO CURATED.INTERACTION_INSIGHTS
WITH todo AS (
  SELECT t.*
  FROM RAW.CALL_TRANSCRIPTS t
  WHERE NOT EXISTS (SELECT 1 FROM CURATED.INTERACTION_INSIGHTS i WHERE i.TRANSCRIPT_ID = t.TRANSCRIPT_ID)
),
cust_text AS (   -- keep only the customer's side of the dialogue
  SELECT t.TRANSCRIPT_ID,
         LISTAGG(TRIM(SUBSTR(TRIM(s.VALUE), 10)), ' ') WITHIN GROUP (ORDER BY s.INDEX) AS CUSTOMER_TEXT
  FROM todo t, LATERAL SPLIT_TO_TABLE(t.TRANSCRIPT_TEXT, '\n') s
  WHERE STARTSWITH(TRIM(s.VALUE), 'Customer:')
  GROUP BY t.TRANSCRIPT_ID
),
enriched AS (
  SELECT
    t.TRANSCRIPT_ID, t.CUSTOMER_ID, t.POLICY_ID, t.CALL_TS, t.AGENT_ID, ct.CUSTOMER_TEXT, t.TRANSCRIPT_TEXT,
    SNOWFLAKE.CORTEX.SENTIMENT(ct.CUSTOMER_TEXT) AS SENTIMENT_SCORE,
    AI_CLASSIFY(
      t.TRANSCRIPT_TEXT,
      [
        {'label': 'claim_issue',         'description': 'customer complains about a delayed, rejected, under-paid or stuck insurance claim'},
        {'label': 'price_concern',       'description': 'customer questions a premium increase, asks for a discount or compares quotes from other insurers'},
        {'label': 'cancellation_intent', 'description': 'customer wants to cancel, not renew, port the policy to another insurer or stop auto-debit'},
        {'label': 'upsell_interest',     'description': 'customer asks about adding cover, members, a top-up, a new product or a bundle'},
        {'label': 'service_praise',      'description': 'customer thanks the insurer or praises a fast claim, easy renewal or good service'},
        {'label': 'general_service',     'description': 'routine request: address change, certificates, nominee, renewal date, auto-debit setup'}
      ],
      {'task_description': 'Identify the PRIMARY reason the customer is calling an Indian insurance company call centre. If the customer threatens to cancel or port, choose cancellation_intent.'}
    ):labels[0]::VARCHAR AS PRIMARY_INTENT,
    TRIM(AI_COMPLETE(
      'llama3.1-70b',
      'You are summarising an insurance call-centre transcript for a retention agent. '
      || 'Write ONE sentence (max 25 words) stating what the customer wanted, how they felt, and any open commitment. '
      || 'Mention policy/claim IDs and rupee amounts if present. No preamble.\n\nTranscript:\n' || t.TRANSCRIPT_TEXT
    )) AS SUMMARY
  FROM todo t
  LEFT JOIN cust_text ct ON ct.TRANSCRIPT_ID = t.TRANSCRIPT_ID
)
SELECT
  TRANSCRIPT_ID, CUSTOMER_ID, POLICY_ID, CALL_TS, AGENT_ID, CUSTOMER_TEXT,
  ROUND(SENTIMENT_SCORE, 3),
  CASE WHEN SENTIMENT_SCORE <= -0.25 THEN 'negative'
       WHEN SENTIMENT_SCORE >=  0.25 THEN 'positive'
       ELSE 'neutral' END,
  PRIMARY_INTENT, SUMMARY, TRANSCRIPT_TEXT,
  'CORTEX.SENTIMENT + AI_CLASSIFY + AI_COMPLETE(llama3.1-70b)',
  CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
FROM enriched;

-- ---------------------------------------------------------------------
-- Quality check: AI_CLASSIFY accuracy vs ground-truth labels (synthetic eval set)
-- ---------------------------------------------------------------------
SELECT COUNT(*)                                                 AS TRANSCRIPTS_ENRICHED,
       ROUND(AVG(IFF(i.PRIMARY_INTENT = l.TRUE_INTENT, 1, 0)) * 100, 1) AS INTENT_ACCURACY_PCT,
       ROUND(AVG(i.SENTIMENT_SCORE), 3)                         AS AVG_SENTIMENT,
       COUNT_IF(i.SENTIMENT_LABEL = 'negative')                 AS NEGATIVE_CALLS
FROM CURATED.INTERACTION_INSIGHTS i
LEFT JOIN RAW.EVAL_TRANSCRIPT_LABELS l USING (TRANSCRIPT_ID);

SELECT PRIMARY_INTENT, COUNT(*) AS CALLS, ROUND(AVG(SENTIMENT_SCORE), 2) AS AVG_SENTIMENT
FROM CURATED.INTERACTION_INSIGHTS GROUP BY 1 ORDER BY 2 DESC;
