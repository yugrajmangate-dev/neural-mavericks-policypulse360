-- =====================================================================
-- PolicyPulse 360 — environment setup (idempotent)
-- Creates: XS warehouse (auto-suspend 60s), DB POLICYPULSE, schemas RAW / CURATED / APP,
--          RAW tables, CSV file format + internal stage.
-- Run as a role that can create warehouses/databases (e.g. SYSADMIN), or ACCOUNTADMIN on a trial.
-- =====================================================================

CREATE WAREHOUSE IF NOT EXISTS POLICYPULSE_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  COMMENT = 'PolicyPulse 360 hackathon — XS, auto-suspend 60s';

USE WAREHOUSE POLICYPULSE_WH;

CREATE DATABASE IF NOT EXISTS POLICYPULSE COMMENT = 'PolicyPulse 360 — Insurance Customer 360 + Next Best Action';
CREATE SCHEMA IF NOT EXISTS POLICYPULSE.RAW     COMMENT = 'Landing zone: source-system extracts (policy admin, claims, billing, call centre)';
CREATE SCHEMA IF NOT EXISTS POLICYPULSE.CURATED COMMENT = 'Unified 360 + AI-enriched interactions';
CREATE SCHEMA IF NOT EXISTS POLICYPULSE.APP     COMMENT = 'Serving layer for the Streamlit app (risk + next best action)';

-- Optional (ACCOUNTADMIN): allow Cortex models not hosted in your region (e.g. AWS ap-south-1 Mumbai)
-- ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION';

USE SCHEMA POLICYPULSE.RAW;

CREATE OR REPLACE TABLE CUSTOMERS (
  CUSTOMER_ID         VARCHAR PRIMARY KEY,
  FULL_NAME           VARCHAR,
  GENDER              VARCHAR(1),
  AGE                 NUMBER(3),
  CITY                VARCHAR,
  STATE               VARCHAR,
  CITY_TIER           NUMBER(1),
  SEGMENT             VARCHAR,
  ANNUAL_INCOME_BAND  VARCHAR,
  CUSTOMER_SINCE      DATE,
  TENURE_YEARS        NUMBER(4,1),
  PREFERRED_CHANNEL   VARCHAR,
  PREFERRED_LANGUAGE  VARCHAR,
  EMAIL               VARCHAR,
  MOBILE_MASKED       VARCHAR,
  KYC_STATUS          VARCHAR
);

CREATE OR REPLACE TABLE POLICIES (
  POLICY_ID           VARCHAR PRIMARY KEY,
  CUSTOMER_ID         VARCHAR,
  PRODUCT_LINE        VARCHAR,      -- Motor / Health / Life / Home
  PLAN_NAME           VARCHAR,
  SUM_INSURED         NUMBER(14,0), -- INR
  ANNUAL_PREMIUM      NUMBER(12,0), -- INR
  PAYMENT_FREQUENCY   VARCHAR,
  START_DATE          DATE,
  RENEWAL_DATE        DATE,
  STATUS              VARCHAR,
  SALES_CHANNEL       VARCHAR,
  NCB_PCT             NUMBER(3)
);

CREATE OR REPLACE TABLE CLAIMS (
  CLAIM_ID            VARCHAR PRIMARY KEY,
  POLICY_ID           VARCHAR,
  CUSTOMER_ID         VARCHAR,
  PRODUCT_LINE        VARCHAR,
  CLAIM_TYPE          VARCHAR,
  CLAIM_DATE          DATE,
  CLAIM_AMOUNT        NUMBER(12,0),
  APPROVED_AMOUNT     NUMBER(12,0),
  STATUS              VARCHAR,      -- Settled / Pending / Under Review / Rejected
  SETTLED_DATE        DATE,
  DAYS_TO_SETTLE      NUMBER(5),
  DAYS_OPEN           NUMBER(5)
);

CREATE OR REPLACE TABLE PAYMENTS (
  PAYMENT_ID          VARCHAR PRIMARY KEY,
  POLICY_ID           VARCHAR,
  CUSTOMER_ID         VARCHAR,
  DUE_DATE            DATE,
  PAID_DATE           DATE,
  AMOUNT_DUE          NUMBER(12,0),
  AMOUNT_PAID         NUMBER(12,0),
  PAYMENT_STATUS      VARCHAR,      -- On-time / Late / Missed
  DAYS_LATE           NUMBER(5),
  PAYMENT_METHOD      VARCHAR
);

CREATE OR REPLACE TABLE CALL_TRANSCRIPTS (
  TRANSCRIPT_ID       VARCHAR PRIMARY KEY,
  CUSTOMER_ID         VARCHAR,
  POLICY_ID           VARCHAR,
  CALL_TS             TIMESTAMP_NTZ,
  DIRECTION           VARCHAR,
  CHANNEL             VARCHAR,
  AGENT_ID            VARCHAR,
  DURATION_SEC        NUMBER(6),
  LANGUAGE            VARCHAR,
  TRANSCRIPT_TEXT     VARCHAR       -- unstructured: full agent/customer dialogue
);

-- Ground-truth intent labels — used ONLY to score AI_CLASSIFY accuracy, never as model input
CREATE OR REPLACE TABLE EVAL_TRANSCRIPT_LABELS (
  TRANSCRIPT_ID       VARCHAR,
  TRUE_INTENT         VARCHAR
);

CREATE FILE FORMAT IF NOT EXISTS CSV_FMT
  TYPE = CSV
  SKIP_HEADER = 1
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  NULL_IF = ('', 'NULL')
  EMPTY_FIELD_AS_NULL = TRUE
  ENCODING = 'UTF8';

CREATE STAGE IF NOT EXISTS RAW_STAGE FILE_FORMAT = CSV_FMT
  COMMENT = 'Upload data/raw/*.csv here';
