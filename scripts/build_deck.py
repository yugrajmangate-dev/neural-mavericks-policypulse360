"""Build submission/PolicyPulse360_NeuralMavericks.pdf (16:9, 6 slides) from the deck content.
Numbers are recomputed from demo_data so the deck never drifts from the data.

    python scripts/build_deck.py
"""
import json
import os
from pathlib import Path

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submission"
OUT = SUB / "PolicyPulse360_NeuralMavericks.pdf"
INK, INK2, MUTED, ACC, ACC2, BG = "#0b0b0b", "#52514e", "#898781", "#1c5cab", "#29b5e8", "#f9f9f7"
HIGH = "#d03b3b"

nba = pd.read_parquet(ROOT / "demo_data" / "next_best_actions.parquet")
arch = pd.read_csv(ROOT / "data" / "raw" / "eval_customer_archetype.csv")
m = nba.merge(arch, on="CUSTOMER_ID")
n_hi = int((nba.RISK_BAND == "High").sum())
tp = int(((m.RISK_BAND == "High") & (m.ARCHETYPE == "at_risk")).sum())
n_risk = int((m.ARCHETYPE == "at_risk").sum())
prec = tp / n_hi
p_hi = nba.loc[nba.RISK_BAND == "High", "TOTAL_ANNUAL_PREMIUM"].sum()
p_all = nba.TOTAL_ANNUAL_PREMIUM.sum()
ren30 = int(((nba.RISK_BAND == "High") & (nba.DAYS_TO_RENEWAL <= 30)).sum())
source = json.loads((ROOT / "demo_data" / "meta.json").read_text()).get("source")


def L(x):
    return f"₹{x / 1e5:.1f} L" if x < 1e7 else f"₹{x / 1e7:.2f} Cr"


def slide(pdf, title, kicker=None):
    fig = plt.figure(figsize=(13.333, 7.5), dpi=100)
    fig.patch.set_facecolor("white")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13.333)
    ax.set_ylim(0, 7.5)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 7.32), 13.333, 0.18, boxstyle="square,pad=0", fc=ACC, ec="none"))
    if kicker:
        ax.text(0.6, 6.85, kicker.upper(), fontsize=11, color=ACC, fontweight="bold")
    ax.text(0.6, 6.35, title, fontsize=28, color=INK, fontweight="bold", va="center")
    ax.text(12.75, 0.3, "PolicyPulse 360 · Neural Mavericks", fontsize=9, color=MUTED, ha="right")
    return fig, ax


def bullets(ax, items, x=0.65, y=5.6, fs=15, gap=0.62, width=None):
    for it in items:
        sub = it.startswith("  ")
        ax.text(x + (0.4 if sub else 0), y, ("–  " if sub else "•  ") + it.strip(), fontsize=fs - (2 if sub else 0),
                color=INK2 if sub else INK, va="top", wrap=True)
        y -= gap * (0.85 if sub else 1)
    return y


def tile(ax, x, y, w, h, value, label, color=ACC):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.12", fc=BG, ec="#e1e0d9", lw=1.2))
    ax.text(x + 0.25, y + h - 0.35, value, fontsize=26, fontweight="bold", color=color, va="top")
    ax.text(x + 0.25, y + 0.3, label, fontsize=11, color=INK2, va="bottom", wrap=True)


PREVIEW = os.environ.get("DECK_PREVIEW_DIR")  # optional: also dump PNG previews of each slide
_n = [0]
_save = PdfPages.savefig


def _savefig(self, fig, **kw):
    _n[0] += 1
    if PREVIEW:
        fig.savefig(Path(PREVIEW) / f"slide_{_n[0]}.png", dpi=60)
    return _save(self, fig, **kw)


PdfPages.savefig = _savefig

with PdfPages(OUT) as pdf:
    # 1 title
    fig, ax = slide(pdf, "")
    ax.text(0.6, 4.6, "PolicyPulse 360", fontsize=54, fontweight="bold", color=INK)
    ax.text(0.62, 3.85, "Customer 360 + Next Best Action for insurance retention teams", fontsize=20, color=INK2)
    ax.text(0.62, 2.9, "Team Neural Mavericks  ·  Snowflake CoCo CLI Hackathon (GCC Edition)", fontsize=15, color=ACC,
            fontweight="bold")
    ax.text(0.62, 2.35, "Challenge: Customer 360 and Next Best Action", fontsize=14, color=INK2)
    ax.text(0.62, 1.5, "Snowflake AI Data Cloud  ·  Cortex AI SQL (SENTIMENT · AI_CLASSIFY · AI_COMPLETE · Search)  ·  "
            "3 Cortex Code CLI skills  ·  Streamlit", fontsize=12, color=MUTED)
    pdf.savefig(fig)
    plt.close(fig)

    # 2 problem
    fig, ax = slide(pdf, "An agent can't save a customer they can't see", "Problem brief")
    bullets(ax, [
        "Indian insurers run policy admin, claims, billing and the call centre as separate systems.",
        "  A retention agent opens 4+ screens and replays call recordings, taking ~20 min per customer (est.)",
        "The strongest churn signals are buried in unstructured call transcripts:",
        "  \"I want to port my policy\" · \"claim pending 45 days\" · \"an aggregator quoted ₹4,000 less\"",
        "Result: churn is discovered at lapse, offers are generic, and upsell moments are missed.",
        "  (new baby → health top-up, new home → Home Protect)",
        "Persona: relationship manager or retention agent at a multi-line insurer (Motor · Health · Life · Home).",
        "Goal: go from a customer question to an explainable, ready-to-send action in one screen.",
    ], fs=16, gap=0.64)
    pdf.savefig(fig)
    plt.close(fig)

    # 3 architecture
    fig, ax = slide(pdf, "Architecture: 3 modular CoCo CLI skills on Snowflake", "Architecture")
    img = mpimg.imread(SUB / "architecture.png")
    iax = fig.add_axes([0.05, 0.07, 0.9, 0.74])
    iax.imshow(img)
    iax.axis("off")
    pdf.savefig(fig)
    plt.close(fig)

    # 4 how skills connect / demo flow
    fig, ax = slide(pdf, "Input → Processing → Output, all driven from CoCo CLI", "How the skills connect")
    cols = [
        ("$c360-unify", "INPUT", ["Joins CUSTOMERS, POLICIES, CLAIMS,", "PAYMENTS + call volume", "→ CURATED.CUSTOMER_360 (view)",
                                  "60+ signals, 1 row per customer", "Zero Cortex cost"]),
        ("$interaction-intel", "PROCESSING", ["CORTEX.SENTIMENT on customer turns", "AI_CLASSIFY → 6 intents",
                                               "AI_COMPLETE → 1-line summary", "→ CURATED.INTERACTION_INSIGHTS",
                                               "Incremental · accuracy vs labels"]),
        ("$next-best-action", "OUTPUT", ["Explainable risk: 8 weighted drivers", "Rule baseline for every customer",
                                          "Grounded AI_COMPLETE: action, reason,", "evidence call IDs, message",
                                          "→ APP.NEXT_BEST_ACTIONS"]),
    ]
    for i, (name, stage, lines) in enumerate(cols):
        x = 0.6 + i * 4.15
        ax.add_patch(FancyBboxPatch((x, 1.55), 3.85, 4.2, boxstyle="round,pad=0,rounding_size=0.15", fc=BG, ec="#e1e0d9"))
        ax.text(x + 0.25, 5.4, stage, fontsize=11, color=MUTED, fontweight="bold")
        ax.text(x + 0.25, 4.9, name, fontsize=19, color=ACC, fontweight="bold", family="monospace")
        for j, ln in enumerate(lines):
            ax.text(x + 0.25, 4.3 - j * 0.5, ln, fontsize=12.5, color=INK2 if not ln.startswith("→") else INK,
                    fontweight="bold" if ln.startswith("→") else "normal")
        if i < 2:
            ax.annotate("", xy=(x + 4.12, 3.65), xytext=(x + 3.88, 3.65),
                        arrowprops=dict(arrowstyle="-|>", color=ACC, lw=2, mutation_scale=18))
    ax.text(0.6, 1.0, "Skills share Snowflake tables as their contract, so each runs alone or chained. "
            "The 360 is a view, so AI signals flow in as soon as Skill 2 runs.\n"
            "Demo: \"What should I do for C0004?\" → risk 90/100 → senior retention call + WhatsApp message.",
            fontsize=11.5, color=INK2, wrap=True)
    pdf.savefig(fig)
    plt.close(fig)

    # 5 impact
    fig, ax = slide(pdf, "Impact: measurable outcomes", "Impact statement")
    tile(ax, 0.6, 3.7, 2.9, 2.1, "20m → 30s", "agent prep per customer\n(projected: 4 systems → 1 card)")
    tile(ax, 3.7, 3.7, 2.9, 2.1, f"{n_hi} / {len(nba)}", f"customers flagged High risk\n({n_hi / len(nba):.0%} of book, measured)", HIGH)
    tile(ax, 6.8, 3.7, 2.9, 2.1, f"{tp / n_risk:.0%}", f"recall of truly at-risk customers\n({tp}/{n_risk}; {prec:.0%} precision)")
    tile(ax, 9.9, 3.7, 2.85, 2.1, L(p_hi), f"premium in High-risk band\n({p_hi / p_all:.0%} of {L(p_all)}, measured)", HIGH)
    bullets(ax, [
        f"{ren30} High-risk customers renew within 30 days: a ranked call list for this week.",
        f"Saving 20% of High-risk premium = {L(p_hi * 0.2)} per {len(nba)} customers, about ₹{p_hi / len(nba) * 1e6 * 0.2 / 1e7:,.0f} Cr per 1M customers (projected).",
        "Every recommendation is explainable: score drivers + cited transcript IDs, so it's audit-friendly.",
        "Upsell signals (new baby, new home) are routed to cross-sell, not missed.",
    ], y=3.2, fs=14, gap=0.58)
    ax.text(0.6, 0.65, f"Measured on the synthetic dataset (seed 42, 300 customers, 819 transcripts). Data source for this deck: {source}.",
            fontsize=9.5, color=MUTED)
    pdf.savefig(fig)
    plt.close(fig)

    # 6 scalability
    fig, ax = slide(pdf, "Scalability and next steps", "Scale")
    y = bullets(ax, [
        "Cost grows with new interactions, not book size:",
        "  incremental Cortex enrichment; LLM capped to High/Medium-risk + upsell customers",
        "XS warehouse + auto-suspend 60s handles this demo. Warehouse size is a one-line change for millions.",
        "Portable skills: drop .cortex/skills into any account, point at real RAW tables, AS_OF_DATE() → CURRENT_DATE()",
        "DEMO mode (Parquet) lets anyone open the app; LIVE mode queries Snowflake and calls Cortex on demand.",
    ], fs=15, gap=0.56)
    ax.text(0.65, y - 0.1, "Next steps", fontsize=17, fontweight="bold", color=ACC, va="top")
    bullets(ax, [
        "AI_TRANSCRIBE for raw call audio; Hindi and regional-language calls",
        "Dynamic tables for near-real-time scoring after every call",
        "Calibrate weights on real lapse outcomes; A/B uplift by action; push NBAs to CRM / WhatsApp Business",
        "Cortex Analyst semantic model for governed natural-language Q&A",
    ], y=y - 0.65, fs=14, gap=0.47)
    pdf.savefig(fig)
    plt.close(fig)

print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
