-- =====================================================================
-- PolicyPulse 360 — load RAW tables from the internal stage.
-- Pure-SQL path (works from `snow sql -f` or CoCo CLI). Run from the repo root.
-- Alternative: `python scripts/load_to_snowflake.py` does setup + upload + load in one go.
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.RAW;

PUT file://data/raw/customers.csv              @RAW_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file://data/raw/policies.csv               @RAW_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file://data/raw/claims.csv                 @RAW_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file://data/raw/payments.csv               @RAW_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file://data/raw/call_transcripts.csv       @RAW_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;
PUT file://data/raw/eval_transcript_labels.csv @RAW_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE;

COPY INTO CUSTOMERS              FROM @RAW_STAGE/customers.csv.gz              ON_ERROR = ABORT_STATEMENT;
COPY INTO POLICIES               FROM @RAW_STAGE/policies.csv.gz               ON_ERROR = ABORT_STATEMENT;
COPY INTO CLAIMS                 FROM @RAW_STAGE/claims.csv.gz                 ON_ERROR = ABORT_STATEMENT;
COPY INTO PAYMENTS               FROM @RAW_STAGE/payments.csv.gz               ON_ERROR = ABORT_STATEMENT;
COPY INTO CALL_TRANSCRIPTS       FROM @RAW_STAGE/call_transcripts.csv.gz       ON_ERROR = ABORT_STATEMENT;
COPY INTO EVAL_TRANSCRIPT_LABELS FROM @RAW_STAGE/eval_transcript_labels.csv.gz ON_ERROR = ABORT_STATEMENT;

SELECT 'CUSTOMERS' T, COUNT(*) N FROM CUSTOMERS UNION ALL
SELECT 'POLICIES', COUNT(*) FROM POLICIES UNION ALL
SELECT 'CLAIMS', COUNT(*) FROM CLAIMS UNION ALL
SELECT 'PAYMENTS', COUNT(*) FROM PAYMENTS UNION ALL
SELECT 'CALL_TRANSCRIPTS', COUNT(*) FROM CALL_TRANSCRIPTS;
