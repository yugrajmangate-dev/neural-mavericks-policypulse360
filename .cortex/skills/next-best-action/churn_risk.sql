-- =====================================================================
-- Skill 3 · next-best-action — step 1: explainable churn-risk score
-- Transparent weighted rules (no black box). Every point is attributable to a driver.
--
--   Driver               Max pts  Rule
--   NEGATIVE_SENTIMENT     25     25 × clamp((0.25 − avg customer sentiment 90d) / 1.0, 0, 1)   (falls back to 180d)
--   CANCELLATION_INTENT    20     20 if a cancellation/port call in last 90d, 8 if only in 91–180d
--   PRICE_SENSITIVITY      10     10 if a price-concern call in last 90d
--   PAYMENT_STRESS         15     15 × min(1, (late_12m + 2 × missed_12m) / 4)
--   CLAIM_FRICTION         15     15 × min(1, (slow_or_open>30d + rejected claims, 18m) / 2)
--   RENEWAL_PROXIMITY      15     15 if renewal ≤30d (or in grace), 10 if ≤60d, 5 if ≤90d
--   LOYALTY (protective)   −5     tenure ≥ 8 years
--   ADVOCACY (protective)  −5     service-praise call in last 180d
--   Score = clamp(sum, 0, 100).  Bands: High ≥ 55 · Medium 30–54 · Low < 30
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.APP;

CREATE OR REPLACE VIEW APP.CHURN_RISK
  COMMENT = 'Explainable churn-risk score per customer (weighted rules over CURATED.CUSTOMER_360)'
AS
WITH s AS (
  SELECT c.*,
    ROUND(25 * LEAST(1, GREATEST(0, (0.25 - COALESCE(c.AVG_SENTIMENT_90D, c.AVG_SENTIMENT_180D, 0.25)) / 1.0)), 1) AS P_SENTIMENT,
    CASE WHEN c.N_CANCEL_INTENT_90D > 0 THEN 20 WHEN c.N_CANCEL_INTENT_180D > 0 THEN 8 ELSE 0 END             AS P_CANCEL,
    IFF(c.N_PRICE_CONCERN_90D > 0, 10, 0)                                                                    AS P_PRICE,
    ROUND(15 * LEAST(1, (c.N_LATE_12M + 2 * c.N_MISSED_12M) / 4), 1)                                         AS P_PAYMENT,
    ROUND(15 * LEAST(1, (c.N_SLOW_CLAIMS + c.N_REJECTED_CLAIMS) / 2), 1)                                     AS P_CLAIMS,
    CASE WHEN c.DAYS_TO_RENEWAL <= 30 THEN 15 WHEN c.DAYS_TO_RENEWAL <= 60 THEN 10
         WHEN c.DAYS_TO_RENEWAL <= 90 THEN 5 ELSE 0 END                                                      AS P_RENEWAL,
    IFF(c.TENURE_YEARS >= 8, -5, 0)                                                                          AS P_LOYALTY,
    IFF(c.N_SERVICE_PRAISE_180D > 0, -5, 0)                                                                  AS P_ADVOCACY
  FROM CURATED.CUSTOMER_360 c
),
scored AS (
  SELECT s.*,
    LEAST(100, GREATEST(0, P_SENTIMENT + P_CANCEL + P_PRICE + P_PAYMENT + P_CLAIMS + P_RENEWAL + P_LOYALTY + P_ADVOCACY)) AS RISK_SCORE
  FROM s
)
SELECT
  CUSTOMER_ID, FULL_NAME, SEGMENT, CITY, TENURE_YEARS, PRODUCT_LINES, TOTAL_ANNUAL_PREMIUM,
  NEXT_RENEWAL_POLICY_ID, NEXT_RENEWAL_PRODUCT, NEXT_RENEWAL_DATE, DAYS_TO_RENEWAL,
  ROUND(RISK_SCORE, 1) AS RISK_SCORE,
  CASE WHEN RISK_SCORE >= 55 THEN 'High' WHEN RISK_SCORE >= 30 THEN 'Medium' ELSE 'Low' END AS RISK_BAND,
  ROUND(TOTAL_ANNUAL_PREMIUM * RISK_SCORE / 100, 0)                                         AS EXPECTED_PREMIUM_LOSS,
  P_SENTIMENT, P_CANCEL, P_PRICE, P_PAYMENT, P_CLAIMS, P_RENEWAL, P_LOYALTY, P_ADVOCACY,
  -- human-readable drivers, strongest first
  ARRAY_COMPACT(ARRAY_CONSTRUCT(
    IFF(P_SENTIMENT > 0, OBJECT_CONSTRUCT('factor','Negative sentiment','points',P_SENTIMENT,
        'detail','Avg customer sentiment ' || TO_VARCHAR(ROUND(COALESCE(AVG_SENTIMENT_90D, AVG_SENTIMENT_180D), 2)) || ' (90d)'), NULL),
    IFF(P_CANCEL > 0, OBJECT_CONSTRUCT('factor','Cancellation / porting intent','points',P_CANCEL,
        'detail', TO_VARCHAR(N_CANCEL_INTENT_180D) || ' call(s) mentioning cancel/port'), NULL),
    IFF(P_PRICE > 0, OBJECT_CONSTRUCT('factor','Price sensitivity','points',P_PRICE,
        'detail', TO_VARCHAR(N_PRICE_CONCERN_90D) || ' price-concern call(s) in 90d'), NULL),
    IFF(P_PAYMENT > 0, OBJECT_CONSTRUCT('factor','Payment stress','points',P_PAYMENT,
        'detail', TO_VARCHAR(N_LATE_12M) || ' late, ' || TO_VARCHAR(N_MISSED_12M) || ' missed payments (12m)'), NULL),
    IFF(P_CLAIMS > 0, OBJECT_CONSTRUCT('factor','Claim friction','points',P_CLAIMS,
        'detail', TO_VARCHAR(N_SLOW_CLAIMS) || ' slow/open >30d, ' || TO_VARCHAR(N_REJECTED_CLAIMS) || ' rejected'), NULL),
    IFF(P_RENEWAL > 0, OBJECT_CONSTRUCT('factor','Renewal due soon','points',P_RENEWAL,
        'detail', NEXT_RENEWAL_PRODUCT || ' renewal in ' || TO_VARCHAR(DAYS_TO_RENEWAL) || ' days'), NULL),
    IFF(P_LOYALTY < 0, OBJECT_CONSTRUCT('factor','Long tenure (protective)','points',P_LOYALTY,
        'detail', TO_VARCHAR(TENURE_YEARS) || ' years with Kavach'), NULL),
    IFF(P_ADVOCACY < 0, OBJECT_CONSTRUCT('factor','Recent praise (protective)','points',P_ADVOCACY,
        'detail','Service-praise call in last 180d'), NULL)
  )) AS RISK_DRIVERS
FROM scored;

SELECT RISK_BAND, COUNT(*) AS CUSTOMERS, ROUND(AVG(RISK_SCORE),1) AS AVG_SCORE,
       TO_VARCHAR(SUM(TOTAL_ANNUAL_PREMIUM), '999,999,999') AS PREMIUM_INR
FROM APP.CHURN_RISK GROUP BY 1 ORDER BY 3 DESC;
