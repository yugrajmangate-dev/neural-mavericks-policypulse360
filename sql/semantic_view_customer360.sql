-- =====================================================================
-- PolicyPulse 360 — Semantic view for Cortex Analyst / the PolicyPulse Copilot agent
--   APP.CUSTOMER_360_SV over three logical tables:
--     c360 : one row per customer           (CURATED.CUSTOMER_360_SNAPSHOT)
--     nba  : risk + next best action        (APP.NEXT_BEST_ACTIONS, 1:1 with c360)
--     ins  : AI-enriched call transcripts   (CURATED.INTERACTION_INSIGHTS, many:1 with c360)
--   Business-friendly dimensions, facts, metrics and synonyms so plain-English retention questions
--   ("churn rate", "premium at risk", "renewals due this month") map to the right columns.
-- Requires: Skill 1 (c360-unify), Skill 2 (interaction-intel), Skill 3 (next-best-action) outputs.
-- Re-run this file after the pipeline refreshes, so the 360 snapshot is current.
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.APP;

-- CURATED.CUSTOMER_360 is a view (its AI columns fill in after Skill 2 runs). Logical tables in a semantic
-- view need a primary key on a base-table column, so we materialise a snapshot table for the 360.
CREATE OR REPLACE TABLE POLICYPULSE.CURATED.CUSTOMER_360_SNAPSHOT
  COMMENT = 'Materialised CURATED.CUSTOMER_360 for the semantic view; rebuilt by sql/semantic_view_customer360.sql'
AS SELECT * FROM POLICYPULSE.CURATED.CUSTOMER_360;

CREATE OR REPLACE SEMANTIC VIEW POLICYPULSE.APP.CUSTOMER_360_SV

  TABLES (
    c360 AS POLICYPULSE.CURATED.CUSTOMER_360_SNAPSHOT
      PRIMARY KEY (CUSTOMER_ID)
      WITH SYNONYMS = ('customers', 'policyholders', 'customer 360', 'insured')
      COMMENT = 'One row per insurance customer: profile, policies, claims, payments and call signals',
    nba AS POLICYPULSE.APP.NEXT_BEST_ACTIONS
      PRIMARY KEY (CUSTOMER_ID)
      WITH SYNONYMS = ('churn risk', 'next best action', 'retention recommendations', 'NBA')
      COMMENT = 'Explainable churn risk score (0-100) and the recommended next best action per customer',
    ins AS POLICYPULSE.CURATED.INTERACTION_INSIGHTS
      PRIMARY KEY (TRANSCRIPT_ID)
      WITH SYNONYMS = ('calls', 'call transcripts', 'interactions', 'conversations', 'call centre')
      COMMENT = 'Call-centre transcripts enriched by Cortex: sentiment, primary intent and a one-line summary'
  )

  RELATIONSHIPS (
    nba_to_customer AS nba (CUSTOMER_ID) REFERENCES c360 (CUSTOMER_ID),
    call_to_customer AS ins (CUSTOMER_ID) REFERENCES c360 (CUSTOMER_ID)
  )

  FACTS (
    c360.annual_premium_inr AS c360.TOTAL_ANNUAL_PREMIUM
      WITH SYNONYMS = ('premium', 'annual premium', 'GWP')
      COMMENT = 'Total annual premium across active policies, in INR',
    c360.sum_insured_inr AS c360.TOTAL_SUM_INSURED
      COMMENT = 'Total sum insured across active policies, in INR',
    c360.renewal_premium_inr AS c360.NEXT_RENEWAL_PREMIUM
      COMMENT = 'Premium of the next policy due for renewal, in INR',
    c360.settlement_days AS c360.AVG_DAYS_TO_SETTLE
      COMMENT = 'Average days taken to settle this customer''s claims (last 18 months)',
    c360.claims_count AS c360.N_CLAIMS
      COMMENT = 'Claims filed in the last 18 months',
    c360.open_claims_count AS c360.N_OPEN_CLAIMS
      COMMENT = 'Claims still pending or under review',
    c360.late_payments_12m AS c360.N_LATE_12M
      COMMENT = 'Late premium instalments in the last 12 months',
    c360.missed_payments_12m AS c360.N_MISSED_12M
      COMMENT = 'Missed premium instalments in the last 12 months',
    nba.risk_points AS nba.RISK_SCORE
      COMMENT = 'Churn risk score, 0 to 100 (High >= 55, Medium 30-54, Low < 30)',
    nba.premium_at_risk_inr AS nba.PREMIUM_AT_RISK
      COMMENT = 'Annual premium of customers whose risk band is High, in INR',
    nba.expected_loss_inr AS nba.EXPECTED_PREMIUM_LOSS
      COMMENT = 'Annual premium x risk score / 100, in INR',
    ins.sentiment AS ins.SENTIMENT_SCORE
      COMMENT = 'Cortex SENTIMENT on the customer''s words, -1 (negative) to +1 (positive)'
  )

  DIMENSIONS (
    c360.cust_id AS c360.CUSTOMER_ID
      WITH SYNONYMS = ('customer id', 'customer number', 'client id')
      COMMENT = 'Customer identifier, e.g. C0004',
    c360.customer_name AS c360.FULL_NAME
      WITH SYNONYMS = ('name', 'policyholder name', 'client name')
      COMMENT = 'Customer full name',
    c360.customer_city AS c360.CITY
      WITH SYNONYMS = ('city', 'location')
      COMMENT = 'City of residence',
    c360.customer_state AS c360.STATE
      WITH SYNONYMS = ('state', 'region')
      COMMENT = 'Indian state of residence',
    c360.customer_city_tier AS c360.CITY_TIER
      COMMENT = 'City tier 1, 2 or 3',
    c360.customer_segment AS c360.SEGMENT
      WITH SYNONYMS = ('segment', 'customer type')
      COMMENT = 'Customer segment: Mass, Mass Affluent, HNI, SME Owner',
    c360.income_band AS c360.ANNUAL_INCOME_BAND
      COMMENT = 'Annual income band',
    c360.customer_age AS c360.AGE
      COMMENT = 'Customer age in years',
    c360.customer_tenure_years AS c360.TENURE_YEARS
      WITH SYNONYMS = ('tenure', 'years with us', 'vintage')
      COMMENT = 'Years since the customer first bought a policy',
    c360.contact_channel AS c360.PREFERRED_CHANNEL
      WITH SYNONYMS = ('contact channel', 'channel preference')
      COMMENT = 'Preferred contact channel: WhatsApp, Phone, Email, SMS, Branch',
    c360.contact_language AS c360.PREFERRED_LANGUAGE
      COMMENT = 'Preferred language for communication',
    c360.product_mix AS c360.PRODUCT_LINES
      WITH SYNONYMS = ('products', 'product mix', 'lines of business')
      COMMENT = 'Comma-separated active product lines: Health, Life, Motor, Home',
    c360.has_health_policy AS c360.HAS_HEALTH = 1
      WITH SYNONYMS = ('health policyholder', 'health customer')
      COMMENT = 'TRUE if the customer holds an active Health policy',
    c360.has_life_policy AS c360.HAS_LIFE = 1
      COMMENT = 'TRUE if the customer holds an active Life policy',
    c360.has_motor_policy AS c360.HAS_MOTOR = 1
      COMMENT = 'TRUE if the customer holds an active Motor policy',
    c360.has_home_policy AS c360.HAS_HOME = 1
      COMMENT = 'TRUE if the customer holds an active Home policy',
    c360.renewal_product AS c360.NEXT_RENEWAL_PRODUCT
      WITH SYNONYMS = ('renewing product', 'next renewal product')
      COMMENT = 'Product line of the next policy due for renewal',
    c360.renewal_policy_id AS c360.NEXT_RENEWAL_POLICY_ID
      COMMENT = 'Policy ID of the next policy due for renewal',
    c360.renewal_date AS c360.NEXT_RENEWAL_DATE
      WITH SYNONYMS = ('renewal date', 'due date', 'expiry date')
      COMMENT = 'Date of the next policy renewal',
    c360.days_until_renewal AS c360.DAYS_TO_RENEWAL
      WITH SYNONYMS = ('days left', 'days until renewal')
      COMMENT = 'Days from the as-of date (CURATED.AS_OF_DATE()) to the next renewal',
    c360.last_call_intent AS c360.LAST_INTENT
      COMMENT = 'Primary intent of the customer''s most recent call',
    nba.churn_risk_band AS nba.RISK_BAND
      WITH SYNONYMS = ('churn risk band', 'risk level', 'risk category')
      COMMENT = 'Churn risk band: High, Medium or Low',
    nba.nba_category AS nba.ACTION_CATEGORY
      WITH SYNONYMS = ('play', 'action type', 'NBA category')
      COMMENT = 'RETENTION_CALL, CLAIM_ESCALATION, PRICE_MATCH, PAYMENT_FLEX, RENEWAL_NUDGE, CROSS_SELL, ADVOCACY, NURTURE',
    nba.recommended_action AS nba.ACTION
      WITH SYNONYMS = ('next best action', 'recommendation', 'what to do')
      COMMENT = 'Recommended next best action for the customer',
    nba.action_reason AS nba.REASON
      WITH SYNONYMS = ('why', 'reason', 'rationale')
      COMMENT = 'Why this action was recommended (top risk drivers)',
    nba.evidence_transcripts AS ARRAY_TO_STRING(nba.EVIDENCE::ARRAY, ', ')
      WITH SYNONYMS = ('evidence', 'source calls', 'citations')
      COMMENT = 'Comma-separated transcript IDs that support the recommendation (cite these)',
    nba.suggested_message AS nba.CUSTOMER_MESSAGE
      COMMENT = 'Ready-to-send message for the customer',
    nba.outreach_channel AS nba.CHANNEL
      COMMENT = 'Channel to use for the outreach',
    nba.action_source AS nba.GENERATED_BY
      COMMENT = 'Whether the action came from Cortex AI_COMPLETE or the rule engine',
    ins.call_transcript_id AS ins.TRANSCRIPT_ID
      WITH SYNONYMS = ('call id', 'transcript', 'evidence id')
      COMMENT = 'Call transcript identifier, e.g. T00042; cite these as evidence',
    ins.call_date AS ins.CALL_TS::DATE
      WITH SYNONYMS = ('call date', 'date of call')
      COMMENT = 'Date of the call',
    ins.call_policy_id AS ins.POLICY_ID
      COMMENT = 'Policy discussed on the call, if any',
    ins.call_intent AS ins.PRIMARY_INTENT
      WITH SYNONYMS = ('intent', 'reason for call', 'call reason', 'topic')
      COMMENT = 'Cortex AI_CLASSIFY intent: cancellation_intent, claim_issue, price_concern, upsell_interest, service_praise, general_service',
    ins.call_sentiment AS ins.SENTIMENT_LABEL
      WITH SYNONYMS = ('sentiment', 'mood', 'tone')
      COMMENT = 'negative, neutral or positive',
    ins.call_summary AS ins.SUMMARY
      WITH SYNONYMS = ('summary', 'call notes')
      COMMENT = 'One-line Cortex AI_COMPLETE summary of the call'
  )

  METRICS (
    c360.customer_count AS COUNT(c360.CUSTOMER_ID)
      WITH SYNONYMS = ('number of customers', 'customers', 'headcount')
      COMMENT = 'Number of customers',
    c360.book_premium AS SUM(c360.TOTAL_ANNUAL_PREMIUM)
      WITH SYNONYMS = ('total premium', 'book size', 'GWP')
      COMMENT = 'Total annual premium in INR',
    c360.avg_claim_settlement_days AS AVG(c360.AVG_DAYS_TO_SETTLE)
      WITH SYNONYMS = ('claim settlement days', 'time to settle', 'TAT', 'claim turnaround')
      COMMENT = 'Average days to settle a claim, averaged over customers with settled claims',
    c360.open_claims AS SUM(c360.N_OPEN_CLAIMS)
      COMMENT = 'Open (pending or under review) claims',
    c360.renewals_due_30d AS COUNT_IF(c360.DAYS_TO_RENEWAL BETWEEN 0 AND 30)
      WITH SYNONYMS = ('renewals due this month', 'upcoming renewals', 'renewals in 30 days')
      COMMENT = 'Customers with a policy renewal due in the next 30 days',
    c360.renewal_premium_due_30d AS SUM(IFF(c360.DAYS_TO_RENEWAL BETWEEN 0 AND 30, c360.NEXT_RENEWAL_PREMIUM, 0))
      COMMENT = 'Premium (INR) of policies renewing in the next 30 days',
    nba.churn_rate AS COUNT_IF(nba.RISK_BAND = 'High') / NULLIF(COUNT(nba.CUSTOMER_ID), 0)
      WITH SYNONYMS = ('churn risk rate', 'high risk share', 'percent at risk', 'attrition risk')
      COMMENT = 'Share of customers in the High churn-risk band (0-1); predicted, not realised churn',
    nba.high_risk_customers AS COUNT_IF(nba.RISK_BAND = 'High')
      WITH SYNONYMS = ('at-risk customers', 'customers at risk')
      COMMENT = 'Customers in the High churn-risk band',
    nba.avg_risk_score AS AVG(nba.RISK_SCORE)
      COMMENT = 'Average churn risk score (0-100)',
    nba.at_risk_premium AS SUM(nba.PREMIUM_AT_RISK)
      WITH SYNONYMS = ('revenue at risk', 'premium at stake', 'at-risk premium')
      COMMENT = 'Annual premium (INR) held by High-risk customers',
    nba.expected_loss AS SUM(nba.EXPECTED_PREMIUM_LOSS)
      WITH SYNONYMS = ('expected loss', 'risk-weighted premium')
      COMMENT = 'Sum of premium x risk score / 100, in INR',
    ins.call_count AS COUNT(ins.TRANSCRIPT_ID)
      WITH SYNONYMS = ('number of calls', 'call volume', 'interactions')
      COMMENT = 'Number of call transcripts',
    ins.avg_sentiment AS AVG(ins.SENTIMENT_SCORE)
      WITH SYNONYMS = ('average sentiment', 'sentiment score', 'customer mood')
      COMMENT = 'Average Cortex sentiment of customer turns (-1 to +1)',
    ins.negative_call_share AS COUNT_IF(ins.SENTIMENT_LABEL = 'negative') / NULLIF(COUNT(ins.TRANSCRIPT_ID), 0)
      COMMENT = 'Share of calls with negative customer sentiment (0-1)',
    ins.cancellation_calls AS COUNT_IF(ins.PRIMARY_INTENT = 'cancellation_intent')
      WITH SYNONYMS = ('porting calls', 'cancel requests')
      COMMENT = 'Calls where the customer asked to cancel or port a policy'
  )

  COMMENT = 'PolicyPulse 360: insurance Customer 360, churn risk and next best action (Kavach Insurance, synthetic data)'
  AI_SQL_GENERATION 'Money is in Indian rupees (INR); format large values in lakh or crore. "Churn" means predicted churn risk: High risk is churn_risk_band = High (score 55 or more). Renewal windows are relative to days_until_renewal, which is already computed against the as-of date, so use it instead of CURRENT_DATE. When listing customers, include cust_id, customer_name, churn_risk_band, recommended_action and evidence_transcripts. Order at-risk lists by at_risk_premium or risk_points descending.';

-- Smoke tests -------------------------------------------------------------------------
SHOW SEMANTIC VIEWS IN SCHEMA POLICYPULSE.APP;

SELECT * FROM SEMANTIC_VIEW(
  POLICYPULSE.APP.CUSTOMER_360_SV
  DIMENSIONS nba.churn_risk_band
  METRICS c360.customer_count, nba.at_risk_premium, c360.renewals_due_30d
) ORDER BY churn_risk_band;
