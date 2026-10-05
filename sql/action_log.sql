-- =====================================================================
-- PolicyPulse 360 — closed-loop write-back: APP.ACTION_LOG
--   Retention agents mark each next best action Accepted / Rejected / Done from the app.
--   Rows are append-only; the latest row per customer is the current status.
--   APP.ACTION_UPTAKE gives the portfolio-level uptake % shown on the Portfolio tab.
-- Idempotent: CREATE ... IF NOT EXISTS keeps logged history across re-runs.
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.APP;

CREATE TABLE IF NOT EXISTS POLICYPULSE.APP.ACTION_LOG (
  LOG_ID           NUMBER AUTOINCREMENT START 1 INCREMENT 1,
  CUSTOMER_ID      VARCHAR       NOT NULL,
  ACTION_CATEGORY  VARCHAR,
  ACTION           VARCHAR,
  STATUS           VARCHAR       NOT NULL,   -- 'Accepted' | 'Rejected' | 'Done' (validated by the app)
  AGENT            VARCHAR,                  -- Snowflake user (live) or app user label
  TS               TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  NOTE             VARCHAR
)
COMMENT = 'PolicyPulse: retention agent decisions on next best actions (append-only)';

-- Current status per customer (latest decision wins)
CREATE OR REPLACE VIEW POLICYPULSE.APP.ACTION_STATUS AS
SELECT CUSTOMER_ID, ACTION_CATEGORY, ACTION, STATUS, AGENT, TS, NOTE
FROM POLICYPULSE.APP.ACTION_LOG
WHERE STATUS IN ('Accepted', 'Rejected', 'Done')
QUALIFY ROW_NUMBER() OVER (PARTITION BY CUSTOMER_ID ORDER BY TS DESC, LOG_ID DESC) = 1;

-- Portfolio uptake: share of reviewed actions that were accepted or completed
CREATE OR REPLACE VIEW POLICYPULSE.APP.ACTION_UPTAKE AS
SELECT
  COUNT(*)                                               AS REVIEWED,
  COUNT_IF(STATUS = 'Accepted')                          AS ACCEPTED,
  COUNT_IF(STATUS = 'Done')                              AS DONE,
  COUNT_IF(STATUS = 'Rejected')                          AS REJECTED,
  (ACCEPTED + DONE) / NULLIF(REVIEWED, 0)                AS UPTAKE_RATE
FROM POLICYPULSE.APP.ACTION_STATUS;

-- Uptake by play, for "which actions do agents trust?"
CREATE OR REPLACE VIEW POLICYPULSE.APP.ACTION_UPTAKE_BY_CATEGORY AS
SELECT ACTION_CATEGORY,
       COUNT(*)                                          AS REVIEWED,
       COUNT_IF(STATUS IN ('Accepted', 'Done')) / COUNT(*) AS UPTAKE_RATE
FROM POLICYPULSE.APP.ACTION_STATUS
GROUP BY ACTION_CATEGORY;

-- What the Streamlit app runs on a button click (bind variables shown as %s):
-- INSERT INTO POLICYPULSE.APP.ACTION_LOG (CUSTOMER_ID, ACTION_CATEGORY, ACTION, STATUS, AGENT, NOTE)
-- SELECT %s, %s, %s, %s, CURRENT_USER(), %s;

SELECT * FROM POLICYPULSE.APP.ACTION_UPTAKE;
