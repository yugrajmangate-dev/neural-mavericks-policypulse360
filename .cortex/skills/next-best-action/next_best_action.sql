-- =====================================================================
-- Skill 3 · next-best-action — step 2: recommend the next best action
--   (a) deterministic rule engine gives every customer a safe baseline action
--   (b) AI_COMPLETE, grounded ONLY on the customer's 360 row + risk drivers + recent call
--       summaries, writes the action / reason / evidence / customer message for the
--       customers that matter (High + Medium risk, plus upsell signals) — capped for cost
--   (c) APP.NEXT_BEST_ACTIONS = LLM output where valid, rule baseline otherwise
-- Requires: churn_risk.sql (APP.CHURN_RISK), Skill 1 + Skill 2 outputs.
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.APP;

-- (a) context + rule engine ------------------------------------------------------------
CREATE OR REPLACE TABLE APP.NBA_CONTEXT AS
WITH recent AS (
  SELECT CUSTOMER_ID,
    ARRAY_AGG(OBJECT_CONSTRUCT(
      'transcript_id', TRANSCRIPT_ID, 'date', TO_VARCHAR(CALL_TS::DATE), 'intent', PRIMARY_INTENT,
      'sentiment', ROUND(SENTIMENT_SCORE, 2), 'summary', SUMMARY))
      WITHIN GROUP (ORDER BY CALL_TS DESC) AS RECENT_CALLS
  FROM (SELECT * FROM CURATED.INTERACTION_INSIGHTS
        QUALIFY ROW_NUMBER() OVER (PARTITION BY CUSTOMER_ID ORDER BY CALL_TS DESC) <= 4)
  GROUP BY CUSTOMER_ID
),
ev AS (   -- evidence transcript IDs per signal, newest first
  SELECT CUSTOMER_ID,
    ARRAY_AGG(IFF(PRIMARY_INTENT = 'cancellation_intent', TRANSCRIPT_ID, NULL)) WITHIN GROUP (ORDER BY CALL_TS DESC) AS EV_CANCEL,
    ARRAY_AGG(IFF(PRIMARY_INTENT = 'claim_issue',         TRANSCRIPT_ID, NULL)) WITHIN GROUP (ORDER BY CALL_TS DESC) AS EV_CLAIM,
    ARRAY_AGG(IFF(PRIMARY_INTENT = 'price_concern',       TRANSCRIPT_ID, NULL)) WITHIN GROUP (ORDER BY CALL_TS DESC) AS EV_PRICE,
    ARRAY_AGG(IFF(PRIMARY_INTENT = 'upsell_interest',     TRANSCRIPT_ID, NULL)) WITHIN GROUP (ORDER BY CALL_TS DESC) AS EV_UPSELL,
    ARRAY_AGG(IFF(PRIMARY_INTENT = 'service_praise',      TRANSCRIPT_ID, NULL)) WITHIN GROUP (ORDER BY CALL_TS DESC) AS EV_PRAISE,
    ARRAY_AGG(TRANSCRIPT_ID) WITHIN GROUP (ORDER BY CALL_TS DESC)                                                       AS EV_ANY
  FROM CURATED.INTERACTION_INSIGHTS
  WHERE CALL_TS >= DATEADD('day', -180, CURATED.AS_OF_DATE())
  GROUP BY CUSTOMER_ID
),
base AS (
  SELECT r.*, SPLIT_PART(c.FULL_NAME, ' ', 1) AS FIRST_NAME, c.PREFERRED_CHANNEL,
         c.PREFERRED_LANGUAGE, c.N_OPEN_CLAIMS, c.MAX_OPEN_CLAIM_DAYS, c.N_LATE_12M, c.N_MISSED_12M,
         c.N_UPSELL_INTEREST_180D, c.N_SERVICE_PRAISE_180D, c.N_ACTIVE_POLICIES, c.NEXT_RENEWAL_PREMIUM,
         c.HAS_HEALTH, c.HAS_LIFE, c.HAS_HOME, c.AVG_SENTIMENT_90D, c.AGE,
         COALESCE(rc.RECENT_CALLS, ARRAY_CONSTRUCT()) AS RECENT_CALLS,
         ev.EV_CANCEL, ev.EV_CLAIM, ev.EV_PRICE, ev.EV_UPSELL, ev.EV_PRAISE, ev.EV_ANY,
         CASE WHEN c.HAS_HEALTH = 0 THEN 'Health Shield Family Floater'
              WHEN c.HAS_LIFE   = 0 THEN 'Term Secure life cover'
              WHEN c.HAS_HOME   = 0 THEN 'Home Protect'
              ELSE 'Super Top-Up health cover' END AS CROSS_SELL_PRODUCT,
         OBJECT_CONSTRUCT_KEEP_NULL(
           'customer_id', c.CUSTOMER_ID, 'name', c.FULL_NAME, 'age', c.AGE, 'city', c.CITY, 'segment', c.SEGMENT,
           'tenure_years', c.TENURE_YEARS, 'preferred_channel', c.PREFERRED_CHANNEL,
           'preferred_language', c.PREFERRED_LANGUAGE, 'products', c.PRODUCT_LINES,
           'active_policies', c.N_ACTIVE_POLICIES, 'total_annual_premium_inr', c.TOTAL_ANNUAL_PREMIUM,
           'next_renewal', OBJECT_CONSTRUCT('policy_id', c.NEXT_RENEWAL_POLICY_ID, 'plan', c.NEXT_RENEWAL_PLAN,
                                            'date', TO_VARCHAR(c.NEXT_RENEWAL_DATE), 'days_left', c.DAYS_TO_RENEWAL,
                                            'premium_inr', c.NEXT_RENEWAL_PREMIUM),
           'claims_18m', OBJECT_CONSTRUCT('total', c.N_CLAIMS, 'open', c.N_OPEN_CLAIMS, 'slow', c.N_SLOW_CLAIMS,
                                          'rejected', c.N_REJECTED_CLAIMS, 'max_open_days', c.MAX_OPEN_CLAIM_DAYS),
           'payments_12m', OBJECT_CONSTRUCT('due', c.N_PAYMENTS_DUE_12M, 'late', c.N_LATE_12M,
                                            'missed', c.N_MISSED_12M, 'on_time_rate', c.ON_TIME_RATE_12M),
           'interactions_180d', OBJECT_CONSTRUCT('calls', c.N_CALLS_180D, 'avg_sentiment_90d', c.AVG_SENTIMENT_90D,
                                                 'upsell_interest_calls', c.N_UPSELL_INTEREST_180D,
                                                 'praise_calls', c.N_SERVICE_PRAISE_180D)
         ) AS PROFILE
  FROM APP.CHURN_RISK r
  JOIN CURATED.CUSTOMER_360 c ON c.CUSTOMER_ID = r.CUSTOMER_ID
  LEFT JOIN recent rc ON rc.CUSTOMER_ID = r.CUSTOMER_ID
  LEFT JOIN ev        ON ev.CUSTOMER_ID = r.CUSTOMER_ID
),
rules AS (
  SELECT b.*,
    CASE
      WHEN P_CANCEL >= 20 OR (RISK_BAND = 'High' AND P_CANCEL > 0)            THEN 'RETENTION_CALL'
      WHEN P_CLAIMS >= 7.5 AND N_OPEN_CLAIMS > 0                              THEN 'CLAIM_ESCALATION'
      WHEN P_PRICE > 0                                                        THEN 'PRICE_MATCH'
      WHEN P_PAYMENT >= 7.5                                                   THEN 'PAYMENT_FLEX'
      WHEN P_CLAIMS >= 7.5                                                    THEN 'CLAIM_ESCALATION'
      WHEN DAYS_TO_RENEWAL <= 30                                              THEN 'RENEWAL_NUDGE'
      WHEN RISK_BAND = 'Low' AND (N_UPSELL_INTEREST_180D > 0 OR N_ACTIVE_POLICIES <= 2) THEN 'CROSS_SELL'
      WHEN RISK_BAND = 'Low' AND N_SERVICE_PRAISE_180D > 0                    THEN 'ADVOCACY'
      WHEN DAYS_TO_RENEWAL <= 60                                              THEN 'RENEWAL_NUDGE'
      ELSE 'NURTURE' END AS RULE_CATEGORY
  FROM base b
)
SELECT r.*,
  CASE RULE_CATEGORY
    WHEN 'RETENTION_CALL'   THEN 'Senior retention call within 24h with a personalised renewal offer'
    WHEN 'CLAIM_ESCALATION' THEN 'Escalate open claim to claims manager and give a proactive status callback'
    WHEN 'PRICE_MATCH'      THEN 'Send personalised renewal quote: loyalty discount or higher-deductible option'
    WHEN 'PAYMENT_FLEX'     THEN 'Offer instalment switch to monthly e-NACH and a grace-period reminder'
    WHEN 'RENEWAL_NUDGE'    THEN 'Early-bird renewal reminder with one-click payment link'
    WHEN 'CROSS_SELL'       THEN 'Cross-sell ' || CROSS_SELL_PRODUCT || ' with multi-policy discount'
    WHEN 'ADVOCACY'         THEN 'Invite to refer-a-friend programme and request a review'
    ELSE 'No outreach needed — keep in nurture journey' END AS RULE_ACTION,
  CASE RULE_CATEGORY
    WHEN 'RETENTION_CALL'   THEN IFF(ARRAY_SIZE(EV_CANCEL) > 0, EV_CANCEL, EV_ANY)
    WHEN 'CLAIM_ESCALATION' THEN IFF(ARRAY_SIZE(EV_CLAIM) > 0, EV_CLAIM, EV_ANY)
    WHEN 'PRICE_MATCH'      THEN IFF(ARRAY_SIZE(EV_PRICE) > 0, EV_PRICE, EV_ANY)
    WHEN 'CROSS_SELL'       THEN IFF(ARRAY_SIZE(EV_UPSELL) > 0, EV_UPSELL, EV_ANY)
    WHEN 'ADVOCACY'         THEN IFF(ARRAY_SIZE(EV_PRAISE) > 0, EV_PRAISE, EV_ANY)
    ELSE EV_ANY END AS RULE_EVIDENCE,
  CASE RULE_CATEGORY
    WHEN 'RETENTION_CALL'   THEN 'Hi ' || FIRST_NAME || ', we are sorry your recent experience with Kavach fell short. A senior advisor will call you within 24 hours with a personalised offer on policy ' || NEXT_RENEWAL_POLICY_ID || ' before it renews. Reply CALL to pick a time.'
    WHEN 'CLAIM_ESCALATION' THEN 'Hi ' || FIRST_NAME || ', your claim has been escalated to our claims manager today. You will get a status update within 48 hours and a direct contact for any documents needed. We apologise for the delay.'
    WHEN 'PRICE_MATCH'      THEN 'Hi ' || FIRST_NAME || ', thank you for being with Kavach. We have prepared a personalised renewal quote for ' || NEXT_RENEWAL_POLICY_ID || ' with a loyalty discount and a lower-premium deductible option. Tap here to compare before ' || TO_VARCHAR(NEXT_RENEWAL_DATE, 'DD Mon') || '.'
    WHEN 'PAYMENT_FLEX'     THEN 'Hi ' || FIRST_NAME || ', to make premiums easier we can split your payment into monthly e-NACH instalments at no extra cost. Reply YES and we will set it up so your cover stays uninterrupted.'
    WHEN 'RENEWAL_NUDGE'    THEN 'Hi ' || FIRST_NAME || ', your ' || NEXT_RENEWAL_PRODUCT || ' policy ' || NEXT_RENEWAL_POLICY_ID || ' renews on ' || TO_VARCHAR(NEXT_RENEWAL_DATE, 'DD Mon') || '. Renew in one click and keep your benefits: [link]'
    WHEN 'CROSS_SELL'       THEN 'Hi ' || FIRST_NAME || ', as a valued Kavach customer you are eligible for up to 10% multi-policy discount on ' || CROSS_SELL_PRODUCT || '. Shall our advisor share a quick quote?'
    WHEN 'ADVOCACY'         THEN 'Hi ' || FIRST_NAME || ', thank you for your kind words about Kavach! Refer a friend and you both get a ₹500 voucher on renewal.'
    ELSE NULL END AS RULE_MESSAGE,
  (RISK_BAND IN ('High', 'Medium') OR N_UPSELL_INTEREST_180D > 0) AS LLM_ELIGIBLE,
  'You are PolicyPulse, a next-best-action copilot for retention agents at Kavach Insurance, an Indian multi-line insurer. '
  || 'Using ONLY the facts below, recommend ONE next best action for this customer.\n'
  || 'Allowed action_category values: RETENTION_CALL, CLAIM_ESCALATION, PRICE_MATCH, PAYMENT_FLEX, RENEWAL_NUDGE, CROSS_SELL, ADVOCACY, NURTURE.\n'
  || 'Rules: cite 1-3 transcript_id values from RECENT_CALLS as evidence; do not promise discounts above 10%; use Indian rupees (₹); '
  || 'customer_message must be at most 60 words, warm and specific, address the customer by first name, and suit their preferred channel.\n'
  || 'Return ONLY a JSON object with keys: action_category, action (imperative, max 15 words), reason (max 40 words, reference the risk drivers), '
  || 'evidence (array of transcript_id strings), customer_message, channel.\n\n'
  || 'CUSTOMER_360: ' || TO_JSON(PROFILE) || '\n'
  || 'CHURN_RISK: {"score": ' || TO_VARCHAR(RISK_SCORE) || ', "band": "' || RISK_BAND || '", "drivers": ' || TO_JSON(RISK_DRIVERS) || '}\n'
  || 'RECENT_CALLS: ' || TO_JSON(RECENT_CALLS) || '\n'
  || 'RULE_ENGINE_SUGGESTION: ' || RULE_CATEGORY || ' (override only if the evidence clearly supports a better action)'
  AS PROMPT
FROM rules r;

-- (b) grounded LLM recommendations (cost-capped, incremental) -----------------------------
-- Each run adds the next 50 highest-risk eligible customers that have no LLM output yet
-- (~3.5 s per call with openai-gpt-4.1). Re-run to extend coverage;
-- everyone else keeps the rule-engine action. Full refresh: TRUNCATE TABLE APP.NBA_LLM;
CREATE TABLE IF NOT EXISTS APP.NBA_LLM (
  CUSTOMER_ID VARCHAR, RAW_RESPONSE VARCHAR, MODEL VARCHAR, GENERATED_AT TIMESTAMP_NTZ
);
INSERT INTO APP.NBA_LLM
SELECT x.CUSTOMER_ID,
       AI_COMPLETE('openai-gpt-4.1', x.PROMPT),
       'AI_COMPLETE(openai-gpt-4.1)',
       CURRENT_TIMESTAMP()::TIMESTAMP_NTZ
FROM APP.NBA_CONTEXT x
WHERE x.LLM_ELIGIBLE
  AND NOT EXISTS (SELECT 1 FROM APP.NBA_LLM l WHERE l.CUSTOMER_ID = x.CUSTOMER_ID)
QUALIFY ROW_NUMBER() OVER (ORDER BY x.RISK_SCORE DESC) <= 50;

-- (c) final serving table ----------------------------------------------------------------
CREATE OR REPLACE TABLE APP.NEXT_BEST_ACTIONS AS
WITH llm AS (
  SELECT CUSTOMER_ID, MODEL, GENERATED_AT,
         TRY_PARSE_JSON(REGEXP_SUBSTR(RAW_RESPONSE, '\\{.*\\}', 1, 1, 's')) AS J
  FROM APP.NBA_LLM
),
drv AS (  -- driver names, strongest first
  SELECT x.CUSTOMER_ID,
         ARRAY_AGG(d.VALUE:factor::VARCHAR) WITHIN GROUP (ORDER BY d.VALUE:points::FLOAT DESC) AS F
  FROM APP.NBA_CONTEXT x, LATERAL FLATTEN(INPUT => x.RISK_DRIVERS) d
  WHERE d.VALUE:points::FLOAT > 0
  GROUP BY x.CUSTOMER_ID
)
SELECT
  x.CUSTOMER_ID, x.FULL_NAME, x.SEGMENT, x.CITY, x.PRODUCT_LINES, x.TOTAL_ANNUAL_PREMIUM,
  x.NEXT_RENEWAL_POLICY_ID, x.NEXT_RENEWAL_PRODUCT, x.NEXT_RENEWAL_DATE, x.DAYS_TO_RENEWAL,
  x.RISK_SCORE, x.RISK_BAND, x.RISK_DRIVERS, x.EXPECTED_PREMIUM_LOSS,
  IFF(x.RISK_BAND = 'High', x.TOTAL_ANNUAL_PREMIUM, 0)                        AS PREMIUM_AT_RISK,
  COALESCE(l.J:action_category::VARCHAR, x.RULE_CATEGORY)                     AS ACTION_CATEGORY,
  COALESCE(l.J:action::VARCHAR,          x.RULE_ACTION)                       AS ACTION,
  COALESCE(l.J:reason::VARCHAR,
           'Rule engine: ' || x.RULE_CATEGORY || ' — top drivers: ' ||
           COALESCE(ARRAY_TO_STRING(ARRAY_SLICE(drv.F, 0, 2), '; '), 'none'))     AS REASON,
  COALESCE(l.J:evidence,                 ARRAY_SLICE(x.RULE_EVIDENCE, 0, 3))  AS EVIDENCE,
  COALESCE(l.J:customer_message::VARCHAR, x.RULE_MESSAGE)                     AS CUSTOMER_MESSAGE,
  COALESCE(l.J:channel::VARCHAR,          x.PREFERRED_CHANNEL)                AS CHANNEL,
  x.RULE_CATEGORY,
  IFF(l.J IS NOT NULL, l.MODEL, 'rule-engine')                                AS GENERATED_BY,
  COALESCE(l.GENERATED_AT, CURRENT_TIMESTAMP()::TIMESTAMP_NTZ)                AS GENERATED_AT
FROM APP.NBA_CONTEXT x
LEFT JOIN llm l ON l.CUSTOMER_ID = x.CUSTOMER_ID
LEFT JOIN drv   ON drv.CUSTOMER_ID = x.CUSTOMER_ID;

-- Summary
SELECT RISK_BAND, ACTION_CATEGORY, GENERATED_BY, COUNT(*) AS CUSTOMERS,
       TO_VARCHAR(SUM(TOTAL_ANNUAL_PREMIUM), '999,999,999') AS PREMIUM_INR
FROM APP.NEXT_BEST_ACTIONS GROUP BY 1, 2, 3 ORDER BY 1, 4 DESC;
