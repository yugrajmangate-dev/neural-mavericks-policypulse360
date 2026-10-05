-- =====================================================================
-- Skill 4 · ask-policypulse — ask the PolicyPulse Copilot agent one question
-- Usage:  SET Q = '<plain-English retention question>';  then run this file.
-- Returns one row: ANSWER, TOOLS_USED, EVIDENCE_IDS (transcript IDs cited), SQL_USED.
-- Requires: sql/cortex_agent_policypulse.sql (python scripts/run_upgrades.py)
-- =====================================================================
USE WAREHOUSE POLICYPULSE_WH;
USE SCHEMA POLICYPULSE.APP;

WITH run AS (
  SELECT TRY_PARSE_JSON(SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
           'POLICYPULSE.APP.POLICYPULSE_COPILOT',
           TO_JSON(OBJECT_CONSTRUCT('messages', ARRAY_CONSTRUCT(
             OBJECT_CONSTRUCT('role', 'user', 'content', ARRAY_CONSTRUCT(
               OBJECT_CONSTRUCT('type', 'text', 'text', $Q)))))))) AS J
),
items AS (
  SELECT c.index AS I, c.value AS V FROM run, LATERAL FLATTEN(INPUT => run.J:content) c
),
answer AS (
  SELECT LISTAGG(V:text::STRING, '\n') WITHIN GROUP (ORDER BY I) AS ANSWER
  FROM items WHERE V:type::STRING = 'text'
)
SELECT
  a.ANSWER,
  (SELECT ARRAY_UNIQUE_AGG(V:tool_use:name::STRING) FROM items WHERE V:type::STRING = 'tool_use') AS TOOLS_USED,
  ARRAY_DISTINCT(REGEXP_SUBSTR_ALL(a.ANSWER, 'T[0-9]{5}'))                                          AS EVIDENCE_IDS,
  (SELECT ANY_VALUE(V:tool_result:content[0]:json:sql::STRING) FROM items
    WHERE V:type::STRING = 'tool_result' AND V:tool_result:content[0]:json:sql IS NOT NULL)         AS SQL_USED
FROM answer a;
