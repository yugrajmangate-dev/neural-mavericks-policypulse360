# PolicyPulse 360 — CoCo CLI demo script

Exact prompts to type into **Cortex Code CLI** on camera. Hero customer: **C0004 · Arjun Shah** (Pune, Mass segment,
Health + Life + Motor, ₹84,850/yr, Health renewal in 22 days, scored High risk).

## Pre-flight (off camera, ~5 min)
```bash
cd neural-mavericks-policypulse360
python data/generate_data.py            # synthetic data -> data/raw/*.csv
python scripts/load_to_snowflake.py     # DB, schemas, XS warehouse, RAW tables loaded
cortex                                  # start CoCo CLI from the repo root -> loads .cortex/skills/*
```
In CoCo, type `$` and confirm the four skills autocomplete: `c360-unify`, `interaction-intel`, `next-best-action`,
`ask-policypulse` (or run `cortex skill list` in a shell).

After the base pipeline has run, deploy the upgrades once (semantic view, Cortex Search, Cortex Agent, action log):
```bash
python scripts/run_upgrades.py --smoke   # ~1–2 min; prints each statement and one sample agent answer
```

> Tip: before recording, warm up once with `python scripts/run_pipeline.py` so Cortex results are cached in tables.
> Skill 2 is incremental, so the on-camera re-run only enriches new transcripts. To show it enriching live, run
> `TRUNCATE TABLE POLICYPULSE.CURATED.INTERACTION_INSIGHTS;` first (~800 calls take 1–3 min on XS).

---

## Scene 1 — INPUT: unify structured data (Skill 1)
```
$c360-unify Build the PolicyPulse customer 360 in Snowflake and show me the coverage summary.
```
*Expected:* CoCo executes `c360_unify.sql`, creates `CURATED.CUSTOMER_360`, and reports 300 customers, coverage per source and total ₹ premium.

```
Show me the full 360 profile for Arjun Shah.
```

## Scene 2 — PROCESSING: unstructured → insight (Skill 2)
```
$interaction-intel Analyse all call-centre transcripts with Cortex AI — sentiment on the customer's words, primary intent and a one-line summary. Report intent accuracy against the eval labels and the intent distribution.
```
*Expected:* `INTERACTION_INSIGHTS` is populated, then CoCo reports accuracy % and a table of intents with average sentiment.

```
Why is customer C0004 unhappy? Show their calls in time order with sentiment and summary.
```
*Optional (if time):*
```
Create the Cortex Search service on transcripts and find customers complaining that hospital documents were submitted twice.
```

## Scene 3 — OUTPUT: risk + next best action (Skill 3)
```
$next-best-action Score churn risk for every customer and generate next best actions. How much annual premium is at risk, and who are the top 5 customers I should call today?
```
*Expected:* customers per risk band, ₹ premium at risk, and the top 5 with action and reason.

```
What should I do for customer C0004 right now? Explain the risk drivers, cite the call evidence, and give me a WhatsApp message I can send.
```
*Expected:* CoCo runs `SET CID='C0004'` and `nba_for_customer.sql`, then returns the action, reason, evidence transcript IDs and the message in a code block.

```
Which health policyholders renewing next month are at high churn risk and why?
```

## Scene 4 — the full chain in one prompt
```
Run the full PolicyPulse chain end to end: $c360-unify, then $interaction-intel, then $next-best-action. Then refresh the app's demo data with: python scripts/export_demo_data.py
```

## Scene 4b — ASK: the Cortex Agent answers with citations (Skill 4)
```
$ask-policypulse Which health policyholders renewing in the next 30 days are at high churn risk, and why?
```
*Expected:* CoCo sets `Q`, runs `ask.sql`, and **PolicyPulse Copilot** (Cortex Agent) answers. Cortex Analyst on
`APP.CUSTOMER_360_SV` finds the customers, Cortex Search on `CURATED.TRANSCRIPT_SEARCH` pulls their calls, and the answer
cites `[T0xxxx]` transcript IDs and ends with **Recommended action:**. CoCo then shows the cited calls' summaries.

```
$ask-policypulse Why is customer C0004 unhappy and what should I do today?
```
*Say on camera:* "Same data, new interface. A semantic view gives the business vocabulary, so 'churn rate', 'premium at risk'
and 'renewals due' mean the same thing to the agent as to the retention team. Every claim is backed by a call ID."

```
Log that I accepted this action for C0004.
```
*Expected:* CoCo inserts an `Accepted` row into `APP.ACTION_LOG` (the skill asks before writing).

## Scene 5 — the experience (Streamlit)
Switch to the deployed app:
1. **Customer 360**: search "Arjun", then walk through the risk gauge, drivers, policies/claims/payments, sentiment trend and transcript timeline.
2. **Next Best Action** panel: action, reason, evidence chips, then hit **copy** on the message.
   **Close the loop:** type a note ("customer asked for a callback Friday") and click **✅ Accepted**. In LIVE mode this
   writes to `APP.ACTION_LOG`. Click **🏁 Done** on a second customer and **✖️ Rejected** on a third.
   *Say:* "Recommendations aren't fire-and-forget. Agents' decisions flow back into Snowflake, so we can measure which plays they trust." 
3. **Portfolio**: ₹ premium at risk, top at-risk list, intent mix, and the new **Action uptake** KPI
   (share of reviewed actions Accepted or Done, from `APP.ACTION_UPTAKE`). It moves with the clicks from step 2.
4. **Ask PolicyPulse**: type *"Which health policyholders renewing next month are at high churn risk and why?"*

**React Command Center** (optional cut-away): the same **Accepted / Rejected / Done** buttons sit on the NBA card, and the
Portfolio **Action uptake** tile updates. The static site has no Snowflake connection, so it's labelled
*Demo · saved in this browser*.

## Backup prompts (if something fails live)
- Model not available: `Use the fallback SQL for interaction-intel and swap openai-gpt-4.1 for llama3.1-70b in next-best-action.`
- Missing objects: `Check which POLICYPULSE objects exist and run whichever skills are missing, in chain order.`
- Agent unavailable (orchestration model not in region): `Use the ask-policypulse fallback: query APP.CUSTOMER_360_SV with SEMANTIC_VIEW() and pull evidence with SEARCH_PREVIEW.`
- After recording: `python scripts/run_upgrades.py --teardown` drops the agent and the search service (stops serving cost).
