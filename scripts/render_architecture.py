"""Render submission/architecture.png (same content as submission/architecture.mmd), locally with matplotlib."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "submission" / "architecture.png"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
SKILL, SKILL_EDGE = "#1c5cab", "#104281"
TABLE_EDGE, SF_BG, SRC_BG, UNSTRUCT = "#2a78d6", "#eef6fd", "#f0efec", "#eb6834"

fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")
fig.patch.set_facecolor("white")


def box(cx, cy, w, h, title, sub="", fc="white", ec=INK2, tc=INK, lw=1.4, r=0.12, fs=11, ls="-"):
    ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
                                fc=fc, ec=ec, lw=lw, ls=ls, zorder=2))
    if sub:
        ty = cy + h / 2 - 0.27
        ax.text(cx, ty, title, ha="center", va="center", fontsize=fs, fontweight="bold", color=tc, zorder=3)
        ax.text(cx, ty - 0.2, sub, ha="center", va="top", fontsize=fs - 2.5,
                color=tc if tc == "white" else INK2, zorder=3, linespacing=1.4)
    else:
        ax.text(cx, cy, title, ha="center", va="center", fontsize=fs, fontweight="bold", color=tc, zorder=3)
    return (cx, cy, w, h)


def arrow(p, q, color=INK2, ls="-", lw=1.6, rad=0.0, label=None, lpos=0.5, loff=(0, 0.16)):
    ax.annotate("", xy=q, xytext=p, zorder=4,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls, shrinkA=2, shrinkB=2,
                                connectionstyle=f"arc3,rad={rad}", mutation_scale=14))
    if label:
        x = p[0] + (q[0] - p[0]) * lpos + loff[0]
        y = p[1] + (q[1] - p[1]) * lpos + loff[1]
        ax.text(x, y, label, ha="center", va="center", fontsize=8.5, color=INK2, zorder=5,
                bbox=dict(fc="white", ec="none", pad=1.2))


R = lambda b: (b[0] + b[2] / 2, b[1])  # noqa: E731
L = lambda b: (b[0] - b[2] / 2, b[1])  # noqa: E731
T = lambda b: (b[0], b[1] + b[3] / 2)  # noqa: E731
B = lambda b: (b[0], b[1] - b[3] / 2)  # noqa: E731

# title
ax.text(0.25, 8.62, "PolicyPulse 360 — architecture", fontsize=19, fontweight="bold", color=INK, va="center")
ax.text(0.25, 8.22, "Structured + unstructured touchpoints → unified 360 → explainable churn risk → next best action, "
        "orchestrated by 3 modular Cortex Code CLI skills", fontsize=11, color=INK2, va="center")

# sources
ax.text(1.4, 7.72, "SOURCE SYSTEMS", ha="center", fontsize=9, color=MUTED, fontweight="bold")
srcs = [("CRM / KYC", "CUSTOMERS · 300"), ("Policy admin", "POLICIES · 509"), ("Claims", "CLAIMS · 239"),
        ("Billing", "PAYMENTS · 2,232"), ("Call centre", "CALL_TRANSCRIPTS · 819\nunstructured dialogue")]
src_boxes = []
for i, (t, s) in enumerate(srcs):
    y = 7.0 - i * 1.28
    un = i == 4
    src_boxes.append(box(1.4, y, 2.3, 1.0 if not un else 1.1, t, s, fc=SRC_BG if not un else "#fdf0ea",
                         ec=MUTED if not un else UNSTRUCT, lw=1.2 if not un else 2.0, fs=10.5))

# snowflake container
ax.add_patch(FancyBboxPatch((2.95, 0.55), 10.25, 7.35, boxstyle="round,pad=0,rounding_size=0.25",
                            fc=SF_BG, ec="#29b5e8", lw=2, zorder=1))
ax.text(3.15, 7.62, "SNOWFLAKE AI DATA CLOUD  ·  database POLICYPULSE", fontsize=10.5, fontweight="bold", color="#0f6e99")
ax.text(3.15, 0.8, "XS warehouse · auto-suspend 60s · incremental Cortex enrichment · LLM capped to high-value customers · "
        "no credentials in repo", fontsize=8.8, color=INK2)

raw = box(4.15, 4.45, 1.55, 2.0, "RAW", "stage +\nCOPY INTO\n6 tables", ec=TABLE_EDGE, lw=1.6, fs=12)
k1 = box(6.5, 6.45, 2.55, 1.05, "$c360-unify", "SQL views · AS_OF_DATE()", fc=SKILL, ec=SKILL_EDGE, tc="white")
k2 = box(6.5, 4.0, 2.55, 1.85, "$interaction-intel",
         "SENTIMENT on customer turns\nAI_CLASSIFY · 6 intents\nAI_COMPLETE 1-line summary\nCortex Search (optional)",
         fc=SKILL, ec=SKILL_EDGE, tc="white")
c360 = box(9.35, 6.45, 2.5, 0.95, "CURATED.CUSTOMER_360", "1 row / customer · 60+ signals", ec=TABLE_EDGE, fs=9.5)
ins = box(9.35, 4.0, 2.5, 0.95, "CURATED.INTERACTION_INSIGHTS", "sentiment · intent · summary", ec=TABLE_EDGE, fs=8.1)
k3 = box(11.85, 5.25, 2.4, 1.55, "$next-best-action",
         "explainable weighted risk\n(8 drivers, 0–100)\ngrounded AI_COMPLETE NBA",
         fc=SKILL, ec=SKILL_EDGE, tc="white")
nba = box(11.85, 2.55, 2.5, 1.15, "APP.NEXT_BEST_ACTIONS", "action · reason · evidence IDs\nmessage · ₹ premium at risk",
          ec=TABLE_EDGE, fs=9.5)
risk = box(9.35, 2.55, 2.3, 0.85, "APP.CHURN_RISK", "score + driver breakdown", ec=TABLE_EDGE, fs=10)
box(5.45, 1.75, 4.3, 0.9, "Run alone or chained in CoCo CLI",
    "$c360-unify → $interaction-intel → $next-best-action", fc="white", ec=SKILL, ls="--", fs=10)

for b in src_boxes:
    arrow(R(b), (L(raw)[0], raw[1] + (b[1] - 4.45) * 0.25))
arrow((raw[0] + 0.4, T(raw)[1]), L(k1), rad=-0.2)
arrow(R(raw), L(k2))
arrow(R(k1), L(c360))
arrow(R(k2), L(ins))
arrow(T(ins), B(c360), color=TABLE_EDGE, ls="--", label="AI signals", loff=(0.48, 0))
arrow(R(c360), (k3[0] - 0.4, T(k3)[1]), rad=-0.25)
arrow(R(ins), (L(k3)[0], k3[1] - 0.35))
arrow(B(k3), T(nba))
arrow((L(k3)[0] + 0.3, B(k3)[1]), (risk[0] + 0.6, T(risk)[1]), rad=0.2)

# experience
ax.text(14.6, 7.72, "EXPERIENCE", ha="center", fontsize=9, color=MUTED, fontweight="bold")
app = box(14.6, 3.85, 2.35, 2.3, "Streamlit app",
          "360 card · risk gauge\nNBA + copy message\nportfolio · ₹ at risk\nAsk PolicyPulse (NL)", ec=INK, lw=1.8)
agent = box(14.6, 6.55, 2.35, 1.05, "Retention agent / RM", "question → action", fc=SRC_BG, ec=MUTED, fs=10)
arrow(R(nba), (L(app)[0], app[1] - 0.9))
ax.text(14.6, 2.42, "fed by APP tables\nLIVE: Snowflake connector\nDEMO: Parquet export", ha="center", va="top",
        fontsize=8.5, color=INK2)
arrow((agent[0] - 0.35, B(agent)[1]), (app[0] - 0.35, T(app)[1]), color=SKILL)
arrow((app[0] + 0.35, T(app)[1]), (agent[0] + 0.35, B(agent)[1]))

# legend
lx, ly = 8.3, 1.75
ax.add_patch(FancyBboxPatch((lx, ly), 0.3, 0.22, boxstyle="round,pad=0,rounding_size=0.04", fc=SKILL, ec=SKILL_EDGE))
ax.text(lx + 0.4, ly + 0.11, "CoCo CLI skill (SKILL.md + SQL)", fontsize=8.5, va="center", color=INK2)
ax.add_patch(FancyBboxPatch((lx, ly - 0.38), 0.3, 0.22, boxstyle="round,pad=0,rounding_size=0.04", fc="white", ec=TABLE_EDGE))
ax.text(lx + 0.4, ly - 0.27, "Snowflake table / view", fontsize=8.5, va="center", color=INK2)
ax.add_patch(FancyBboxPatch((lx, ly - 0.76), 0.3, 0.22, boxstyle="round,pad=0,rounding_size=0.04", fc="#fdf0ea", ec=UNSTRUCT, lw=1.5))
ax.text(lx + 0.4, ly - 0.65, "unstructured source", fontsize=8.5, va="center", color=INK2)

fig.savefig(OUT, dpi=150, bbox_inches="tight", facecolor="white")
print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
