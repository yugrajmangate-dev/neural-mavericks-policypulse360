-- =====================================================================
-- Skill 3 · next-best-action — single-customer, on-demand recommendation
-- "Customer question -> recommended action" in one call.
-- Usage: set the customer, then run the file (needs APP.NBA_CONTEXT from next_best_action.sql).
--   SET CID = 'C0042';
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.APP;

-- (requires: SET CID = '<customer_id>'; in the same session)

WITH gen AS (
  SELECT x.CUSTOMER_ID, x.FULL_NAME, x.RISK_SCORE, x.RISK_BAND, x.RISK_DRIVERS, x.RULE_CATEGORY,
         TRY_PARSE_JSON(REGEXP_SUBSTR(AI_COMPLETE('mistral-large2', x.PROMPT), '\\{.*\\}', 1, 1, 's')) AS J
  FROM APP.NBA_CONTEXT x
  WHERE x.CUSTOMER_ID = $CID
)
SELECT CUSTOMER_ID, FULL_NAME, RISK_SCORE, RISK_BAND,
       J:action_category::VARCHAR  AS ACTION_CATEGORY,
       J:action::VARCHAR           AS ACTION,
       J:reason::VARCHAR           AS REASON,
       J:evidence                  AS EVIDENCE_TRANSCRIPTS,
       J:customer_message::VARCHAR AS CUSTOMER_MESSAGE,
       J:channel::VARCHAR          AS CHANNEL,
       RISK_DRIVERS,
       RULE_CATEGORY               AS RULE_ENGINE_BASELINE
FROM gen;
