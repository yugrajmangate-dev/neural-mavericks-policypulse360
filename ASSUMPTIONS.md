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

## Skills & Cortex (Phase 2)
| # | Assumption / fallback |
|---|---|
| S1 | **Sentiment** uses `SNOWFLAKE.CORTEX.SENTIMENT` (numeric −1…1) on the *customer's* lines only, because agent scripts are uniformly polite. Labels: ≤ −0.25 negative, ≥ 0.25 positive. |
| S2 | **Intent** uses `AI_CLASSIFY` with label descriptions and a task description. `interaction_intel_fallback.sql` swaps to `CLASSIFY_TEXT` + `SUMMARIZE` for regions without AI_* functions. |
| S3 | **Models**: `llama3.1-70b` for summaries (cheap, widely available) and `mistral-large2` for NBA. If either is unavailable in the region, enable cross-region inference or swap models (documented in each SKILL.md). |
| S4 | **NBA cost cap**: the LLM runs only for High/Medium-risk or upsell-signal customers, max 150. Everyone else gets the deterministic rule-engine action. That baseline is also the fallback when the LLM JSON doesn't parse. |
| S5 | Risk weights are **hand-set, transparent rules** (documented in `churn_risk.sql` and the skill), as the brief asked: explainable, not black-box. They are not trained on real lapse outcomes. Calibrating them is a listed next step. |
| S6 | Cortex Search is **optional** (`transcript_search.sql`) because it has an always-on serving cost. Drop it after the demo. |
| S7 | `CURATED.AS_OF_DATE()` pins "today" to 2026-10-04 so the synthetic data doesn't age. Use `CURRENT_DATE()` for real data. |
| S8 | **Not executed against Snowflake during the build** (no connection, A1). The SQL follows current Snowflake docs but may need minor fixes on first run. `scripts/run_pipeline.py` prints every statement so failures are easy to locate. |

## App (Phase 3)
| # | Assumption |
|---|---|
| P1 | `demo_data/*.parquet` currently comes from `scripts/simulate_pipeline_local.py`, an **offline simulation** that mirrors the SQL logic but replaces Cortex with lexicon/keyword/template stand-ins. Every row is tagged `local-sim` and the app shows a yellow "offline simulation" badge. After the Snowflake run, `python scripts/export_demo_data.py` overwrites these files with real Cortex outputs and the badge turns blue ("Cortex outputs exported"). |
| P2 | In DEMO mode, "Ask PolicyPulse" uses a transparent rule-based interpreter and shows the filters it applied. In LIVE mode it uses Cortex `AI_COMPLETE` text-to-SQL, restricted to a single SELECT over allow-listed POLICYPULSE schemas. |
| P3 | Deployed on Streamlit Community Cloud from `streamlit_app.py`. Package versions are pinned to the ones tested locally. |

## Submission (Phase 4)
| # | Assumption |
|---|---|
| M1 | Impact numbers are split into **measured** (on the synthetic data: 26% flagged High, 87% recall / 83% precision vs the hidden archetype, ₹37.0 L premium at risk) and **projected** (20 min → 30 s prep time; 20% save rate). Projections are labelled as such. |
| M2 | The architecture PNG and PDF deck are rendered locally with matplotlib (`scripts/render_architecture.py`, `scripts/build_deck.py`). `architecture.mmd` holds the same diagram in Mermaid. |
