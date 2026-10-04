# Assumptions & decisions log

Built under a ~3-hour hackathon deadline. Every non-obvious call is logged here.

## Environment (Phase 0)
| # | Finding / assumption | Impact |
|---|---|---|
| A1 | `cortex` (CoCo CLI) and `snow` (Snowflake CLI) were **not installed** on the build machine, and no `~/.snowflake/connections.toml` existed. | All SQL and skills were written against Snowflake docs and could not be executed live during the build. The team must run them once (see README → Setup) before recording the demo. |
| A2 | CoCo CLI skills are discovered from `.cortex/skills/<skill-name>/SKILL.md` (project scope) and invoked with `$skill-name` ([docs](https://docs.snowflake.com/user-guide/cortex-code/extensibility)). | Skills live in this repo under `.cortex/skills/`, so they auto-load when `cortex` is started from the repo root. |
| A3 | The CoCo CLI and the Python loader share one connection file: `~/.snowflake/connections.toml`. | No credentials in the repo; the Streamlit app uses `st.secrets` instead. |

## Data (Phase 1)
| # | Assumption |
|---|---|
| D1 | The insurer is the fictional **"Kavach Insurance"**, a multi-line (Motor/Health/Life/Home) Indian insurer. All people, policies, phone numbers and e-mails (`@example.in`) are synthetic. |
| D2 | `AS_OF` date is fixed at **2026-10-04**, so the dataset is reproducible (seed 42). Renewal windows and "last 90 days" logic are relative to it. |
| D3 | Churn signal is baked in using a hidden archetype (loyal 45% / at-risk 25% / price-shopper 15% / growth 15%). The archetype is **not** loaded into Snowflake. It's kept in `data/raw/eval_customer_archetype.csv` only to evaluate the risk score offline. |
| D4 | Ground-truth intent per transcript (`eval_transcript_labels.csv`) is loaded to `RAW.EVAL_TRANSCRIPT_LABELS` **only to score AI_CLASSIFY accuracy**. No skill uses it as model input. |
| D5 | A 6th intent, `general_service` (address change, certificates, due-date queries), was added to the 5 required ones so routine calls aren't forced into a complaint/upsell bucket. |
| D6 | Transcripts are English, with a few Hinglish phrases ("ji", "theek hai") to reflect Indian call centres. Competitors are never named ("another insurer", "an online aggregator"). |
| D7 | ~819 transcripts (target ~800); counts vary slightly by archetype mix. |
