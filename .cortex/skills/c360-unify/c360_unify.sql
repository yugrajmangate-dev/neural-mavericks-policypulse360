-- =====================================================================
-- Skill 1 · c360-unify
-- Builds CURATED.CUSTOMER_360: one row per customer that unifies
--   policy admin (POLICIES) + claims (CLAIMS) + billing (PAYMENTS)
--   + call-centre interactions (CALL_TRANSCRIPTS, and AI insights when available).
-- Idempotent. Views only (zero storage, always fresh) — cheap on an XS warehouse.
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.CURATED;

-- Single source of truth for "today". Synthetic data is anchored to 2026-10-04.
-- For production data, change the body to CURRENT_DATE().
CREATE OR REPLACE FUNCTION CURATED.AS_OF_DATE()
  RETURNS DATE
  AS $$ DATE '2026-10-04' $$;

-- Skill 2 (interaction-intel) fills this table. Created empty here so the 360 view
-- works standalone; once Skill 2 runs, the view picks up AI sentiment/intent automatically.
CREATE TABLE IF NOT EXISTS CURATED.INTERACTION_INSIGHTS (
  TRANSCRIPT_ID     VARCHAR,
  CUSTOMER_ID       VARCHAR,
  POLICY_ID         VARCHAR,
  CALL_TS           TIMESTAMP_NTZ,
  AGENT_ID          VARCHAR,
  CUSTOMER_TEXT     VARCHAR,
  SENTIMENT_SCORE   FLOAT,
  SENTIMENT_LABEL   VARCHAR,
  PRIMARY_INTENT    VARCHAR,
  SUMMARY           VARCHAR,
  TRANSCRIPT_TEXT   VARCHAR,
  ENRICHED_BY       VARCHAR,
  ENRICHED_AT       TIMESTAMP_NTZ
);

CREATE OR REPLACE VIEW CURATED.CUSTOMER_360
  COMMENT = 'PolicyPulse 360: unified customer view (structured + unstructured aggregates)'
AS
WITH ref_dt AS (SELECT CURATED.AS_OF_DATE() AS D),

pol AS (
  SELECT
    p.CUSTOMER_ID,
    COUNT_IF(p.STATUS IN ('Active','Grace Period','Cancellation Requested'))              AS N_ACTIVE_POLICIES,
    LISTAGG(DISTINCT p.PRODUCT_LINE, ', ') WITHIN GROUP (ORDER BY p.PRODUCT_LINE)         AS PRODUCT_LINES,
    SUM(IFF(p.STATUS <> 'Lapsed', p.ANNUAL_PREMIUM, 0))                                    AS TOTAL_ANNUAL_PREMIUM,
    SUM(p.SUM_INSURED)                                                                     AS TOTAL_SUM_INSURED,
    MAX(IFF(p.PRODUCT_LINE = 'Health', 1, 0))                                              AS HAS_HEALTH,
    MAX(IFF(p.PRODUCT_LINE = 'Life',   1, 0))                                              AS HAS_LIFE,
    MAX(IFF(p.PRODUCT_LINE = 'Motor',  1, 0))                                              AS HAS_MOTOR,
    MAX(IFF(p.PRODUCT_LINE = 'Home',   1, 0))                                              AS HAS_HOME,
    COUNT_IF(p.STATUS = 'Cancellation Requested')                                          AS N_CANCEL_REQUESTS,
    COUNT_IF(p.STATUS = 'Grace Period')                                                    AS N_IN_GRACE
  FROM RAW.POLICIES p
  GROUP BY p.CUSTOMER_ID
),

next_ren AS (   -- the soonest upcoming (or in-grace) renewal
  SELECT p.CUSTOMER_ID, p.POLICY_ID AS NEXT_RENEWAL_POLICY_ID, p.PRODUCT_LINE AS NEXT_RENEWAL_PRODUCT,
         p.PLAN_NAME AS NEXT_RENEWAL_PLAN, p.ANNUAL_PREMIUM AS NEXT_RENEWAL_PREMIUM,
         p.RENEWAL_DATE AS NEXT_RENEWAL_DATE, DATEDIFF('day', a.D, p.RENEWAL_DATE) AS DAYS_TO_RENEWAL
  FROM RAW.POLICIES p, ref_dt a
  WHERE p.STATUS <> 'Lapsed'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY p.CUSTOMER_ID ORDER BY p.RENEWAL_DATE) = 1
),

clm AS (
  SELECT
    c.CUSTOMER_ID,
    COUNT(*)                                                                          AS N_CLAIMS,
    COUNT_IF(c.STATUS IN ('Pending','Under Review'))                                  AS N_OPEN_CLAIMS,
    COUNT_IF(c.STATUS = 'Rejected')                                                   AS N_REJECTED_CLAIMS,
    COUNT_IF((c.STATUS = 'Settled' AND c.DAYS_TO_SETTLE > 30)
          OR (c.STATUS IN ('Pending','Under Review') AND c.DAYS_OPEN > 30))           AS N_SLOW_CLAIMS,
    SUM(c.CLAIM_AMOUNT)                                                               AS TOTAL_CLAIMED,
    SUM(COALESCE(c.APPROVED_AMOUNT, 0))                                               AS TOTAL_APPROVED,
    ROUND(AVG(c.DAYS_TO_SETTLE), 1)                                                   AS AVG_DAYS_TO_SETTLE,
    MAX(IFF(c.STATUS IN ('Pending','Under Review'), c.DAYS_OPEN, NULL))               AS MAX_OPEN_CLAIM_DAYS
  FROM RAW.CLAIMS c, ref_dt a
  WHERE c.CLAIM_DATE >= DATEADD('month', -18, a.D)
  GROUP BY c.CUSTOMER_ID
),

pay AS (
  SELECT
    y.CUSTOMER_ID,
    COUNT(*)                                       AS N_PAYMENTS_DUE_12M,
    COUNT_IF(y.PAYMENT_STATUS = 'Late')            AS N_LATE_12M,
    COUNT_IF(y.PAYMENT_STATUS = 'Missed')          AS N_MISSED_12M,
    ROUND(COUNT_IF(y.PAYMENT_STATUS = 'On-time') / NULLIF(COUNT(*), 0), 3) AS ON_TIME_RATE_12M,
    ROUND(AVG(IFF(y.PAYMENT_STATUS = 'Late', y.DAYS_LATE, NULL)), 1)        AS AVG_DAYS_LATE
  FROM RAW.PAYMENTS y, ref_dt a
  WHERE y.DUE_DATE >= DATEADD('month', -12, a.D)
  GROUP BY y.CUSTOMER_ID
),

calls AS (      -- raw interaction volume (works even before Skill 2 runs)
  SELECT t.CUSTOMER_ID,
         COUNT(*)                                                         AS N_CALLS_180D,
         MAX(t.CALL_TS)                                                   AS LAST_CALL_TS,
         SUM(t.DURATION_SEC) / 60                                         AS CALL_MINUTES_180D
  FROM RAW.CALL_TRANSCRIPTS t, ref_dt a
  WHERE t.CALL_TS >= DATEADD('day', -180, a.D)
  GROUP BY t.CUSTOMER_ID
),

ai AS (         -- AI-derived interaction signals (from Skill 2)
  SELECT i.CUSTOMER_ID,
    ROUND(AVG(IFF(i.CALL_TS >= DATEADD('day', -90, a.D), i.SENTIMENT_SCORE, NULL)), 3)        AS AVG_SENTIMENT_90D,
    ROUND(AVG(i.SENTIMENT_SCORE), 3)                                                            AS AVG_SENTIMENT_180D,
    MAX_BY(i.SENTIMENT_SCORE, i.CALL_TS)                                                        AS LAST_SENTIMENT,
    MAX_BY(i.PRIMARY_INTENT, i.CALL_TS)                                                         AS LAST_INTENT,
    COUNT_IF(i.PRIMARY_INTENT = 'cancellation_intent' AND i.CALL_TS >= DATEADD('day', -90, a.D)) AS N_CANCEL_INTENT_90D,
    COUNT_IF(i.PRIMARY_INTENT = 'cancellation_intent')                                          AS N_CANCEL_INTENT_180D,
    COUNT_IF(i.PRIMARY_INTENT = 'price_concern' AND i.CALL_TS >= DATEADD('day', -90, a.D))       AS N_PRICE_CONCERN_90D,
    COUNT_IF(i.PRIMARY_INTENT = 'claim_issue' AND i.CALL_TS >= DATEADD('day', -90, a.D))         AS N_CLAIM_ISSUE_90D,
    COUNT_IF(i.PRIMARY_INTENT = 'upsell_interest')                                              AS N_UPSELL_INTEREST_180D,
    COUNT_IF(i.PRIMARY_INTENT = 'service_praise')                                               AS N_SERVICE_PRAISE_180D
  FROM CURATED.INTERACTION_INSIGHTS i, ref_dt a
  WHERE i.CALL_TS >= DATEADD('day', -180, a.D)
  GROUP BY i.CUSTOMER_ID
)

SELECT
  c.CUSTOMER_ID, c.FULL_NAME, c.GENDER, c.AGE, c.CITY, c.STATE, c.CITY_TIER, c.SEGMENT,
  c.ANNUAL_INCOME_BAND, c.CUSTOMER_SINCE, c.TENURE_YEARS, c.PREFERRED_CHANNEL, c.PREFERRED_LANGUAGE,
  c.KYC_STATUS,
  -- policies
  COALESCE(pol.N_ACTIVE_POLICIES, 0) AS N_ACTIVE_POLICIES, pol.PRODUCT_LINES,
  COALESCE(pol.TOTAL_ANNUAL_PREMIUM, 0) AS TOTAL_ANNUAL_PREMIUM, pol.TOTAL_SUM_INSURED,
  pol.HAS_HEALTH, pol.HAS_LIFE, pol.HAS_MOTOR, pol.HAS_HOME, pol.N_CANCEL_REQUESTS, pol.N_IN_GRACE,
  nr.NEXT_RENEWAL_POLICY_ID, nr.NEXT_RENEWAL_PRODUCT, nr.NEXT_RENEWAL_PLAN, nr.NEXT_RENEWAL_PREMIUM,
  nr.NEXT_RENEWAL_DATE, nr.DAYS_TO_RENEWAL,
  -- claims
  COALESCE(clm.N_CLAIMS, 0) AS N_CLAIMS, COALESCE(clm.N_OPEN_CLAIMS, 0) AS N_OPEN_CLAIMS,
  COALESCE(clm.N_REJECTED_CLAIMS, 0) AS N_REJECTED_CLAIMS, COALESCE(clm.N_SLOW_CLAIMS, 0) AS N_SLOW_CLAIMS,
  COALESCE(clm.TOTAL_CLAIMED, 0) AS TOTAL_CLAIMED, COALESCE(clm.TOTAL_APPROVED, 0) AS TOTAL_APPROVED,
  clm.AVG_DAYS_TO_SETTLE, clm.MAX_OPEN_CLAIM_DAYS,
  -- payments
  COALESCE(pay.N_PAYMENTS_DUE_12M, 0) AS N_PAYMENTS_DUE_12M, COALESCE(pay.N_LATE_12M, 0) AS N_LATE_12M,
  COALESCE(pay.N_MISSED_12M, 0) AS N_MISSED_12M, pay.ON_TIME_RATE_12M, pay.AVG_DAYS_LATE,
  -- interactions (structured + AI)
  COALESCE(calls.N_CALLS_180D, 0) AS N_CALLS_180D, calls.LAST_CALL_TS, calls.CALL_MINUTES_180D,
  ai.AVG_SENTIMENT_90D, ai.AVG_SENTIMENT_180D, ai.LAST_SENTIMENT, ai.LAST_INTENT,
  COALESCE(ai.N_CANCEL_INTENT_90D, 0)    AS N_CANCEL_INTENT_90D,
  COALESCE(ai.N_CANCEL_INTENT_180D, 0)   AS N_CANCEL_INTENT_180D,
  COALESCE(ai.N_PRICE_CONCERN_90D, 0)    AS N_PRICE_CONCERN_90D,
  COALESCE(ai.N_CLAIM_ISSUE_90D, 0)      AS N_CLAIM_ISSUE_90D,
  COALESCE(ai.N_UPSELL_INTEREST_180D, 0) AS N_UPSELL_INTEREST_180D,
  COALESCE(ai.N_SERVICE_PRAISE_180D, 0)  AS N_SERVICE_PRAISE_180D,
  (ai.CUSTOMER_ID IS NOT NULL)           AS HAS_AI_INSIGHTS
FROM RAW.CUSTOMERS c
LEFT JOIN pol      ON pol.CUSTOMER_ID   = c.CUSTOMER_ID
LEFT JOIN next_ren nr ON nr.CUSTOMER_ID = c.CUSTOMER_ID
LEFT JOIN clm      ON clm.CUSTOMER_ID   = c.CUSTOMER_ID
LEFT JOIN pay      ON pay.CUSTOMER_ID   = c.CUSTOMER_ID
LEFT JOIN calls    ON calls.CUSTOMER_ID = c.CUSTOMER_ID
LEFT JOIN ai       ON ai.CUSTOMER_ID    = c.CUSTOMER_ID;

-- Validation: 1 row per customer, coverage of each source
SELECT COUNT(*)                                   AS CUSTOMERS,
       COUNT_IF(N_ACTIVE_POLICIES > 0)            AS WITH_ACTIVE_POLICY,
       COUNT_IF(N_CLAIMS > 0)                     AS WITH_CLAIMS,
       COUNT_IF(N_CALLS_180D > 0)                 AS WITH_CALLS_180D,
       COUNT_IF(HAS_AI_INSIGHTS)                  AS WITH_AI_INSIGHTS,
       TO_VARCHAR(SUM(TOTAL_ANNUAL_PREMIUM), '999,999,999') AS TOTAL_PREMIUM_INR
FROM CURATED.CUSTOMER_360;
