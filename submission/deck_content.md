# PolicyPulse 360 — deck content (6 slides)

> Numbers marked **[measured]** come from the pipeline run on the synthetic dataset (300 customers, 819 transcripts).
> Numbers marked **[projected]** are estimates. Their assumptions are stated on the slide.

---

## Slide 1 · Title / Team
**PolicyPulse 360**: Customer 360 and Next Best Action for insurance retention
- Team **Neural Mavericks** · Snowflake CoCo CLI Hackathon (GCC Edition)
- Challenge: Customer 360 and Next Best Action
- Built on: Snowflake AI Data Cloud · Cortex AI SQL · Cortex Code CLI skills · Streamlit
- Links: GitHub repo · live app · demo video

---

## Slide 2 · Problem brief
**An agent can't save a customer they can't see.**
- Indian insurers run policy admin, claims, billing and the call centre as separate systems. A retention agent opens 4+ screens and listens to call recordings before a renewal call, which takes **~20 minutes per customer [projected]**.
- The strongest churn signals are buried in **unstructured call transcripts**: "I'll port my policy", "claim pending 45 days", "an aggregator quoted ₹4,000 less".
- Result: churn is discovered at lapse, offers are generic, and upsell moments (a new baby, a new home) are missed.
- **Persona:** a relationship manager or retention agent at a multi-line insurer (Motor, Health, Life, Home).
- **Goal:** go from a customer question to a recommended, explainable action in one screen.

---

## Slide 3 · Architecture
*(insert `architecture.png`)*
- **Sources:** CUSTOMERS, POLICIES, CLAIMS, PAYMENTS (structured) plus CALL_TRANSCRIPTS (unstructured), loaded to `POLICYPULSE.RAW`.
- **Skill 1 `$c360-unify`:** SQL views produce `CURATED.CUSTOMER_360`, with 60+ signals per customer.
- **Skill 2 `$interaction-intel`:** `CORTEX.SENTIMENT` on customer turns, `AI_CLASSIFY` (6 intents), `AI_COMPLETE` summaries and an optional Cortex Search service produce `CURATED.INTERACTION_INSIGHTS`. It runs incrementally.
- **Skill 3 `$next-best-action`:** an explainable weighted risk score (8 drivers) plus a grounded `AI_COMPLETE` produce `APP.NEXT_BEST_ACTIONS` (action, reason, evidence transcript IDs, message).
- **How the skills connect:** they share Snowflake tables as their contract. Each one runs alone or chained (`$c360-unify → $interaction-intel → $next-best-action`). The 360 is a view, so AI signals flow in automatically once Skill 2 runs.
- **Experience:** a Streamlit app in LIVE mode (Snowflake connector, on-demand Cortex) or DEMO mode (Parquet export, so judges need no login).

---

## Slide 4 · Demo flow: Input → Processing → Output
1. **Input:** in CoCo CLI, `$c360-unify` builds the 360. Asking "Show me Arjun Shah" returns the unified profile.
2. **Processing:** `$interaction-intel` enriches 819 calls. "Why is C0004 unhappy?" returns a timeline: a 26% price hike, then a motor claim stuck 59 days, then a request to port the health policy.
3. **Output:** `$next-best-action` returns a risk score of 90/100 with drivers, the NBA "Senior retention call within 24h", evidence transcript IDs and a ready WhatsApp message.
4. **Experience:** the app shows the 360 card, the NBA with a copy button, the portfolio view with ₹ at risk, and an answer to "Which health policyholders renewing next month are at high churn risk and why?"

---

## Slide 5 · Impact (measurable outcomes)
| Metric | Value |
|---|---|
| Agent prep time per customer | **~20 min → < 30 s** [projected: 4 systems + recordings vs one card] |
| Customers flagged High risk | **78 of 300 (26%)** [measured] |
| Recall of truly at-risk customers (hidden synthetic label) | **87% (65/75)**, with **83% precision** in the High band [measured] |
| Annual premium in the High-risk band | **₹37.0 L of ₹1.45 Cr (25%)** [measured] |
| High-risk renewals due in ≤ 30 days | **43** customers to call this month [measured] |
| Premium retained if 20% of High-risk premium is saved | **₹7.4 L per 300 customers**, about **₹247 Cr per 1M customers** [projected] |
| Every recommendation | explainable: score drivers plus cited call IDs, so it's audit-friendly (IRDAI grievance context) |

---

## Slide 6 · Scalability and next steps
**Scales with Snowflake:**
- Views and incremental Cortex enrichment mean only new calls are processed. The LLM is capped to high-value customers, so cost grows with *new interactions*, not with book size.
- XS warehouse with auto-suspend 60s is enough for 300 → 100k customers. Warehouse size is a one-line change for millions.
- Skills are portable: drop `.cortex/skills/` into any account, point it at real RAW tables, and swap `AS_OF_DATE()` for `CURRENT_DATE()`.

**Next steps:**
- Speech-to-text ingestion (AI_TRANSCRIBE) for raw call audio, plus Hindi and regional-language calls
- Dynamic tables for near-real-time scoring after every call
- Calibrate risk weights against actual lapse outcomes, and add uplift measurement (A/B by action)
- Push NBAs into CRM and WhatsApp Business, and close the loop with an outcome-capture table
- Cortex Analyst semantic model for governed natural-language Q&A
