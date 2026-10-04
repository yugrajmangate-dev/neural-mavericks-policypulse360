"""PolicyPulse 360 — Insurance Customer 360 + Next Best Action copilot.
Team Neural Mavericks · Snowflake CoCo CLI Hackathon (GCC Edition)

    streamlit run streamlit_app.py
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app import chat
from app.data import AS_OF, cortex_complete, is_live, load, meta, regenerate_nba, sql

st.set_page_config(page_title="PolicyPulse 360", page_icon="🛡️", layout="wide")

# ----------------------------------------------------------------------------- design tokens
HIGH, MED, LOW = "#d03b3b", "#fab219", "#0ca30c"            # status: critical / warning / good
NEG, NEU, POS = "#e34948", "#b5b3ab", "#2a78d6"             # diverging sentiment: red / gray / blue
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BAND_COLOR = {"High": HIGH, "Medium": MED, "Low": LOW}
BAND_ICON = {"High": "▲", "Medium": "●", "Low": "▼"}
INTENT_LABEL = {"cancellation_intent": "Cancellation", "claim_issue": "Claim issue", "price_concern": "Price concern",
                "upsell_interest": "Upsell interest", "service_praise": "Service praise",
                "general_service": "General service"}
ACTION_ICON = {"RETENTION_CALL": "📞", "CLAIM_ESCALATION": "⚡", "PRICE_MATCH": "🏷️", "PAYMENT_FLEX": "💳",
               "RENEWAL_NUDGE": "🔔", "CROSS_SELL": "➕", "ADVOCACY": "⭐", "NURTURE": "🌱"}

st.markdown(f"""
<style>
  .block-container {{padding-top: 1.6rem; max-width: 1320px;}}
  h1, h2, h3 {{letter-spacing: -0.01em;}}
  .pp-brand {{display:flex; align-items:baseline; gap:.75rem; flex-wrap:wrap; margin-bottom:.25rem;}}
  .pp-brand .name {{font-size:1.9rem; font-weight:750; color:{INK};}}
  .pp-brand .name b {{color:#1c5cab;}}
  .pp-brand .tag {{color:{INK2}; font-size:.98rem;}}
  .pp-badge {{display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:650;
             border:1px solid rgba(11,11,11,.12);}}
  .pp-card {{background:#fff; border:1px solid rgba(11,11,11,.09); border-radius:14px; padding:1rem 1.15rem;
            box-shadow:0 1px 2px rgba(0,0,0,.04); height:100%;}}
  .pp-card h4 {{margin:0 0 .4rem 0; font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; color:{MUTED};}}
  .pp-profile {{display:flex; gap:1.4rem; flex-wrap:wrap; align-items:center;}}
  .pp-profile .who {{font-size:1.45rem; font-weight:720; color:{INK};}}
  .pp-profile .meta {{color:{INK2}; font-size:.92rem;}}
  .pp-chip {{display:inline-block; padding:2px 9px; margin:2px 4px 2px 0; border-radius:999px; font-size:.78rem;
            background:#f0efec; color:{INK}; border:1px solid rgba(11,11,11,.06);}}
  .pp-chip.ev {{background:#e8f1fc; color:#184f95; font-family:ui-monospace,Consolas,monospace;}}
  .pp-action {{font-size:1.18rem; font-weight:700; color:{INK}; margin:.2rem 0 .5rem 0; line-height:1.35;}}
  .pp-reason {{color:{INK2}; font-size:.95rem; line-height:1.5;}}
  .pp-small {{color:{MUTED}; font-size:.78rem;}}
  .pp-call {{border-left:3px solid {GRID}; padding:.35rem 0 .55rem .85rem; margin-left:.3rem;}}
  .pp-call .when {{color:{MUTED}; font-size:.8rem;}}
  .pp-call .sum {{color:{INK}; font-size:.95rem;}}
  div[data-testid="stMetricValue"] {{font-size:1.55rem;}}
</style>
""", unsafe_allow_html=True)


def rgba(hex_: str, a: float) -> str:
    h = hex_.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def inr(x) -> str:
    """₹ in lakh/crore notation."""
    x = float(x or 0)
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.1f} L"
    return f"₹{x:,.0f}"


def band_badge(band: str, score: float | None = None) -> str:
    c = BAND_COLOR[band]
    txt = f"{BAND_ICON[band]} {band} risk" + (f" · {score:.0f}" if score is not None else "")
    return f'<span class="pp-badge" style="background:{c}1f;color:{INK};border-color:{c}">{txt}</span>'


def style_fig(fig: go.Figure, h: int = 300) -> go.Figure:
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="system-ui, Segoe UI, sans-serif", color=INK2, size=12),
                      legend=dict(orientation="h", y=1.12, x=0, title=None), hoverlabel=dict(bgcolor="white"),
                      bargap=0.28)
    fig.update_xaxes(gridcolor=GRID, zerolinecolor="#c3c2b7", linecolor="#c3c2b7")
    fig.update_yaxes(gridcolor=GRID, zerolinecolor="#c3c2b7", linecolor="#c3c2b7")
    return fig


# ----------------------------------------------------------------------------- data
LIVE = is_live()
try:
    D = load(LIVE)
except Exception as e:  # live connection failed -> fall back to demo files
    st.warning(f"Live Snowflake connection failed ({type(e).__name__}); showing demo data.")
    LIVE = False
    D = load(False)
META = meta(LIVE)
nba, c360, ins, pol, clm, pay = D["nba"], D["c360"], D["ins"], D["pol"], D["clm"], D["pay"]

src = META.get("source", "")
if LIVE:
    mode_html = f'<span class="pp-badge" style="background:#e6f4e6;border-color:{LOW}">● LIVE · Snowflake + Cortex</span>'
elif src == "snowflake-cortex":
    mode_html = (f'<span class="pp-badge" style="background:#e8f1fc;border-color:{POS}">DEMO MODE · Cortex outputs exported '
                 f'{META.get("generated_at", "")[:10]}</span>')
else:
    mode_html = (f'<span class="pp-badge" style="background:#fff5dc;border-color:{MED}">DEMO MODE · offline simulation '
                 f'of the Cortex pipeline</span>')

st.markdown(f"""<div class="pp-brand"><span class="name">Policy<b>Pulse</b> 360</span>
<span class="tag">Customer 360 + Next Best Action for insurance retention teams</span>{mode_html}</div>""",
            unsafe_allow_html=True)
st.caption(f"Fictional insurer *Kavach Insurance* · {len(c360)} customers · {len(pol)} policies · "
           f"{len(ins)} AI-analysed call transcripts · as of {AS_OF:%d %b %Y}")

tab_c, tab_p, tab_a, tab_h = st.tabs(["🎯 Customer 360 + NBA", "📊 Portfolio", "💬 Ask PolicyPulse", "🧩 How it works"])


# ============================================================================= CUSTOMER 360
def customer_tab():
    order = nba.sort_values("RISK_SCORE", ascending=False)
    labels = {r.CUSTOMER_ID: f"{r.FULL_NAME} · {r.CUSTOMER_ID} · {r.CITY} · {r.RISK_BAND} {r.RISK_SCORE:.0f}"
              for r in order.itertuples()}
    ids = list(labels)
    default = st.session_state.get("focus_customer", "C0004")
    idx = ids.index(default) if default in ids else 0
    cid = st.selectbox("Search customer (name, ID or city)", ids, index=idx, format_func=labels.get,
                       help="Sorted by churn risk. Type to search.")
    n = nba[nba.CUSTOMER_ID == cid].iloc[0]
    c = c360[c360.CUSTOMER_ID == cid].iloc[0]
    cins = ins[ins.CUSTOMER_ID == cid].sort_values("CALL_TS")
    cpol, cclm, cpay = pol[pol.CUSTOMER_ID == cid], clm[clm.CUSTOMER_ID == cid], pay[pay.CUSTOMER_ID == cid]

    # profile strip
    st.markdown(f"""<div class="pp-card"><div class="pp-profile">
      <div><div class="who">{html.escape(c.FULL_NAME)}</div>
      <div class="meta">{c.CUSTOMER_ID} · {c.AGE} yrs · {c.CITY}, {c.STATE} · {c.SEGMENT} · customer {c.TENURE_YEARS:.1f} yrs</div>
      <div class="meta">Prefers <b>{c.PREFERRED_CHANNEL}</b> · {c.PREFERRED_LANGUAGE} · KYC {c.KYC_STATUS}</div></div>
      <div style="margin-left:auto">{band_badge(n.RISK_BAND, n.RISK_SCORE)}</div></div>
      <div style="margin-top:.5rem">{''.join(f'<span class="pp-chip">{p}</span>' for p in str(c.PRODUCT_LINES).split(', '))}</div>
    </div>""", unsafe_allow_html=True)

    k = st.columns(5)
    k[0].metric("Annual premium", inr(c.TOTAL_ANNUAL_PREMIUM))
    k[1].metric("Active policies", int(c.N_ACTIVE_POLICIES))
    dtr = c.DAYS_TO_RENEWAL
    k[2].metric("Next renewal", f"{int(dtr)} days" if pd.notna(dtr) else "—",
                help=f"{c.NEXT_RENEWAL_PRODUCT} · {c.NEXT_RENEWAL_POLICY_ID}")
    k[3].metric("Claims (18m)", f"{int(c.N_CLAIMS)} · {int(c.N_OPEN_CLAIMS)} open")
    s90 = c.AVG_SENTIMENT_90D if pd.notna(c.AVG_SENTIMENT_90D) else c.AVG_SENTIMENT_180D
    k[4].metric("Sentiment (90d)", f"{s90:+.2f}" if pd.notna(s90) else "—", help="Cortex SENTIMENT on customer's words, −1…+1")

    left, right = st.columns([5, 7], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Churn risk** — explainable score")
            g = go.Figure(go.Indicator(
                mode="gauge+number", value=float(n.RISK_SCORE), number=dict(suffix=" / 100", font=dict(size=30, color=INK)),
                gauge=dict(axis=dict(range=[0, 100], tickvals=[0, 30, 55, 100], tickcolor=MUTED),
                           bar=dict(color=INK, thickness=0.22),
                           steps=[dict(range=[0, 30], color=rgba(LOW, .25)), dict(range=[30, 55], color=rgba(MED, .33)),
                                  dict(range=[55, 100], color=rgba(HIGH, .27))],
                           borderwidth=0)))
            st.plotly_chart(style_fig(g, 190), width="stretch", config={"displayModeBar": False})
            drv = [d for d in n.RISK_DRIVERS if d["points"] != 0]
            if drv:
                dd = pd.DataFrame(drv)[::-1]
                fig = go.Figure(go.Bar(
                    x=dd.points, y=dd.factor, orientation="h", marker=dict(color=[HIGH if p > 0 else LOW for p in dd.points],
                                                                           cornerradius=4),
                    text=[f"{p:+.0f}" for p in dd.points], textposition="outside", textfont=dict(color=INK2),
                    customdata=dd.detail, hovertemplate="<b>%{y}</b><br>%{customdata}<br>%{x:+.1f} pts<extra></extra>"))
                fig.update_xaxes(range=[min(-7, dd.points.min() - 3), max(28, dd.points.max() + 5)], title=None)
                st.plotly_chart(style_fig(fig, 40 + 34 * len(dd)), width="stretch", config={"displayModeBar": False})
                st.markdown('<span class="pp-small">Red adds risk, green is protective. Weights are documented in the '
                            '<code>next-best-action</code> skill.</span>', unsafe_allow_html=True)
            else:
                st.success("No active risk drivers.")

    with right:
        with st.container(border=True):
            cat = n.ACTION_CATEGORY
            ai = not str(n.GENERATED_BY).startswith(("rule", "local"))
            st.markdown(f"**Next best action** &nbsp; <span class='pp-chip'>{ACTION_ICON.get(cat, '•')} "
                        f"{cat.replace('_', ' ').title()}</span>"
                        f"<span class='pp-chip'>{'🤖 ' + n.GENERATED_BY if ai else '⚙️ ' + n.GENERATED_BY}</span>",
                        unsafe_allow_html=True)
            regen = st.session_state.get(f"regen_{cid}")
            action, reason, ev, msg, ch = n.ACTION, n.REASON, list(n.EVIDENCE), n.CUSTOMER_MESSAGE, n.CHANNEL
            if regen:
                action, reason = regen.get("action", action), regen.get("reason", reason)
                ev, msg, ch = regen.get("evidence", ev), regen.get("customer_message", msg), regen.get("channel", ch)
            st.markdown(f"<div class='pp-action'>{html.escape(str(action))}</div>"
                        f"<div class='pp-reason'><b>Why:</b> {html.escape(str(reason))}</div>", unsafe_allow_html=True)
            st.markdown("<div style='margin-top:.55rem' class='pp-small'>EVIDENCE · source calls</div>"
                        + "".join(f"<span class='pp-chip ev'>{html.escape(str(e))}</span>" for e in ev),
                        unsafe_allow_html=True)
            evc = cins[cins.TRANSCRIPT_ID.isin(ev)]
            for r in evc.itertuples():
                st.markdown(f"<div class='pp-small' style='margin:.15rem 0'><b>{r.TRANSCRIPT_ID}</b> · {r.CALL_TS:%d %b} · "
                            f"{INTENT_LABEL.get(r.PRIMARY_INTENT, r.PRIMARY_INTENT)} · sentiment {r.SENTIMENT_SCORE:+.2f} — "
                            f"{html.escape(str(r.SUMMARY))}</div>", unsafe_allow_html=True)
            if msg and str(msg) != "None":
                st.markdown(f"<div style='margin-top:.6rem' class='pp-small'>SUGGESTED MESSAGE · via {ch} "
                            f"(copy icon, top-right)</div>", unsafe_allow_html=True)
                st.code(str(msg), language=None, wrap_lines=True)
            if LIVE:
                if st.button("🔄 Regenerate with Cortex AI_COMPLETE", key=f"btn_{cid}"):
                    with st.spinner("Asking Cortex…"):
                        out = regenerate_nba(cid)
                    if out:
                        st.session_state[f"regen_{cid}"] = out
                        st.rerun()
                    st.error("Cortex returned no valid JSON — keeping the stored action.")
            nxt = c.NEXT_RENEWAL_DATE
            st.markdown(f"<div class='pp-small'>Next renewal: {c.NEXT_RENEWAL_PLAN} ({c.NEXT_RENEWAL_POLICY_ID}) on "
                        f"{nxt:%d %b %Y} · {inr(c.NEXT_RENEWAL_PREMIUM)}</div>" if pd.notna(nxt) else "",
                        unsafe_allow_html=True)

    t1, t2, t3, t4, t5 = st.tabs([f"🗣️ Interactions ({len(cins)})", "📈 Sentiment trend", f"📄 Policies ({len(cpol)})",
                                  f"🩺 Claims ({len(cclm)})", f"💰 Payments ({len(cpay)})"])
    with t1:
        if cins.empty:
            st.info("No calls on record.")
        for r in cins.iloc[::-1].itertuples():
            col = NEG if r.SENTIMENT_SCORE <= -0.25 else POS if r.SENTIMENT_SCORE >= 0.25 else NEU
            st.markdown(f"""<div class="pp-call" style="border-left-color:{col}">
              <div class="when">{r.CALL_TS:%a %d %b %Y, %H:%M} · {r.TRANSCRIPT_ID} · {html.escape(str(r.AGENT_ID))} ·
              <span class="pp-chip">{INTENT_LABEL.get(r.PRIMARY_INTENT, r.PRIMARY_INTENT)}</span>
              <span class="pp-chip">sentiment {r.SENTIMENT_SCORE:+.2f} ({r.SENTIMENT_LABEL})</span></div>
              <div class="sum">{html.escape(str(r.SUMMARY))}</div></div>""", unsafe_allow_html=True)
            with st.expander(f"Full transcript {r.TRANSCRIPT_ID}"):
                st.text(r.TRANSCRIPT_TEXT)
    with t2:
        if len(cins):
            fig = go.Figure()
            fig.add_hline(y=0, line=dict(color="#c3c2b7", width=1))
            fig.add_trace(go.Scatter(
                x=cins.CALL_TS, y=cins.SENTIMENT_SCORE, mode="lines+markers", line=dict(color=INK2, width=2),
                marker=dict(size=12, color=[NEG if s <= -0.25 else POS if s >= 0.25 else NEU for s in cins.SENTIMENT_SCORE],
                            line=dict(color="white", width=2)),
                customdata=list(zip(cins.TRANSCRIPT_ID, cins.PRIMARY_INTENT.map(INTENT_LABEL), cins.SUMMARY)),
                hovertemplate="<b>%{customdata[0]}</b> · %{x|%d %b %Y}<br>%{customdata[1]} · sentiment %{y:+.2f}"
                              "<br>%{customdata[2]}<extra></extra>", name="sentiment"))
            fig.update_yaxes(range=[-1.05, 1.05], title="customer sentiment", tickvals=[-1, -0.5, 0, 0.5, 1])
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig, 300), width="stretch")
            st.caption("Each dot is a call: red negative, gray neutral, blue positive. Hover for the AI summary.")
    with t3:
        st.dataframe(cpol.drop(columns=["CUSTOMER_ID"]), hide_index=True, width="stretch",
                     column_config={"ANNUAL_PREMIUM": st.column_config.NumberColumn("Premium ₹", format="₹%d"),
                                    "SUM_INSURED": st.column_config.NumberColumn("Sum insured ₹", format="₹%d")})
    with t4:
        if cclm.empty:
            st.info("No claims in the last 18 months.")
        else:
            st.dataframe(cclm.drop(columns=["CUSTOMER_ID"]), hide_index=True, width="stretch",
                         column_config={"CLAIM_AMOUNT": st.column_config.NumberColumn("Claimed ₹", format="₹%d"),
                                        "APPROVED_AMOUNT": st.column_config.NumberColumn("Approved ₹", format="₹%d")})
    with t5:
        if len(cpay):
            m = cpay.assign(M=cpay.DUE_DATE.dt.to_period("M").dt.to_timestamp()).groupby(["M", "PAYMENT_STATUS"]).size().unstack(fill_value=0)
            fig = go.Figure()
            for s, col in [("On-time", LOW), ("Late", MED), ("Missed", HIGH)]:
                if s in m:
                    fig.add_trace(go.Bar(x=m.index, y=m[s], name=s, marker=dict(color=col, line=dict(color="white", width=2)),
                                         hovertemplate=f"%{{x|%b %Y}} · {s}: %{{y}}<extra></extra>"))
            fig.update_layout(barmode="stack")
            fig.update_yaxes(title="instalments", dtick=1)
            st.plotly_chart(style_fig(fig, 260), width="stretch")
            st.dataframe(cpay.drop(columns=["CUSTOMER_ID"]).sort_values("DUE_DATE", ascending=False), hide_index=True,
                         width="stretch")


# ============================================================================= PORTFOLIO
def portfolio_tab():
    f1, f2, f3 = st.columns(3)
    prod = f1.multiselect("Product line", ["Health", "Motor", "Life", "Home"], placeholder="All products")
    seg = f2.multiselect("Segment", sorted(nba.SEGMENT.unique()), placeholder="All segments")
    city = f3.multiselect("City", sorted(nba.CITY.unique()), placeholder="All cities")
    df = nba.copy()
    if prod:
        df = df[df.CUSTOMER_ID.isin(pol[pol.PRODUCT_LINE.isin(prod)].CUSTOMER_ID)]
    if seg:
        df = df[df.SEGMENT.isin(seg)]
    if city:
        df = df[df.CITY.isin(city)]
    if df.empty:
        st.info("No customers match these filters.")
        return
    hi = df[df.RISK_BAND == "High"]
    k = st.columns(5)
    k[0].metric("Customers", len(df))
    k[1].metric("High risk", f"{len(hi)}", f"{len(hi) / len(df):.0%} of book", delta_color="off")
    k[2].metric("Premium at risk (High)", inr(hi.TOTAL_ANNUAL_PREMIUM.sum()),
                f"{hi.TOTAL_ANNUAL_PREMIUM.sum() / max(df.TOTAL_ANNUAL_PREMIUM.sum(), 1):.0%} of premium", delta_color="off")
    k[3].metric("Expected premium loss", inr(df.EXPECTED_PREMIUM_LOSS.sum()), help="Σ premium × risk score / 100")
    k[4].metric("Renewals ≤ 30d at High risk", int(((hi.DAYS_TO_RENEWAL <= 30)).sum()))

    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        st.markdown("**Annual premium by product line and risk band**")
        pp = pol[pol.CUSTOMER_ID.isin(df.CUSTOMER_ID) & (pol.STATUS != "Lapsed")].merge(df[["CUSTOMER_ID", "RISK_BAND"]], on="CUSTOMER_ID")
        g = pp.groupby(["PRODUCT_LINE", "RISK_BAND"]).ANNUAL_PREMIUM.sum().unstack(fill_value=0)
        fig = go.Figure()
        for band in ["High", "Medium", "Low"]:
            if band in g:
                fig.add_trace(go.Bar(x=g.index, y=g[band] / 1e5, name=f"{BAND_ICON[band]} {band}",
                                     marker=dict(color=BAND_COLOR[band], line=dict(color="white", width=2)),
                                     hovertemplate="%{x} · " + band + ": ₹%{y:.1f} L<extra></extra>"))
        fig.update_layout(barmode="stack")
        fig.update_yaxes(title="₹ lakh")
        st.plotly_chart(style_fig(fig, 300), width="stretch")
    with b, st.container(border=True):
        st.markdown("**What customers call about**: intent × sentiment (Cortex, 180d)")
        ii = ins[ins.CUSTOMER_ID.isin(df.CUSTOMER_ID) & (ins.CALL_TS >= AS_OF - pd.Timedelta(days=180))]
        g = ii.groupby(["PRIMARY_INTENT", "SENTIMENT_LABEL"]).size().unstack(fill_value=0)
        g = g.loc[g.sum(axis=1).sort_values().index]
        fig = go.Figure()
        for s, col in [("negative", NEG), ("neutral", NEU), ("positive", POS)]:
            if s in g:
                fig.add_trace(go.Bar(y=[INTENT_LABEL.get(i, i) for i in g.index], x=g[s], name=s, orientation="h",
                                     marker=dict(color=col, line=dict(color="white", width=2)),
                                     hovertemplate="%{y} · " + s + ": %{x} calls<extra></extra>"))
        fig.update_layout(barmode="stack")
        fig.update_xaxes(title="calls")
        st.plotly_chart(style_fig(fig, 300), width="stretch")

    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        st.markdown("**Renewal pipeline**: next 90 days, by week")
        up = pol[pol.CUSTOMER_ID.isin(df.CUSTOMER_ID) & pol.RENEWAL_DATE.between(AS_OF, AS_OF + pd.Timedelta(days=90))]
        up = up.merge(df[["CUSTOMER_ID", "RISK_BAND"]], on="CUSTOMER_ID")
        up["WEEK"] = up.RENEWAL_DATE.dt.to_period("W-SUN").dt.start_time
        g = up.groupby(["WEEK", "RISK_BAND"]).ANNUAL_PREMIUM.sum().unstack(fill_value=0)
        fig = go.Figure()
        for band in ["High", "Medium", "Low"]:
            if band in g:
                fig.add_trace(go.Bar(x=g.index, y=g[band] / 1e5, name=f"{BAND_ICON[band]} {band}",
                                     marker=dict(color=BAND_COLOR[band], line=dict(color="white", width=2)),
                                     hovertemplate="wk of %{x|%d %b} · " + band + ": ₹%{y:.1f} L<extra></extra>"))
        fig.update_layout(barmode="stack")
        fig.update_yaxes(title="₹ lakh renewing")
        st.plotly_chart(style_fig(fig, 280), width="stretch")
    with b, st.container(border=True):
        st.markdown("**Recommended plays** (customers per next best action)")
        g = df.ACTION_CATEGORY.value_counts().sort_values()
        fig = go.Figure(go.Bar(y=[f"{ACTION_ICON.get(i, '')} {i.replace('_', ' ').title()}" for i in g.index], x=g.values,
                               orientation="h", marker=dict(color=POS, cornerradius=4), text=g.values,
                               textposition="outside", textfont=dict(color=INK2),
                               hovertemplate="%{y}: %{x} customers<extra></extra>"))
        fig.update_xaxes(range=[0, g.max() * 1.15])
        st.plotly_chart(style_fig(fig, 280), width="stretch")

    st.markdown("#### Call list: top at-risk customers")
    top = df.sort_values(["RISK_SCORE", "TOTAL_ANNUAL_PREMIUM"], ascending=False).head(25).copy()
    top["TOP_DRIVERS"] = top.RISK_DRIVERS.map(lambda ds: " · ".join([f"{x['factor']} +{x['points']:.0f}" for x in ds if x["points"] > 0][:3]))
    top["RISK"] = top.RISK_BAND.map(lambda b: f"{BAND_ICON[b]} {b}")
    st.dataframe(top[["CUSTOMER_ID", "FULL_NAME", "CITY", "SEGMENT", "RISK_SCORE", "RISK", "TOTAL_ANNUAL_PREMIUM",
                      "NEXT_RENEWAL_PRODUCT", "DAYS_TO_RENEWAL", "TOP_DRIVERS", "ACTION"]],
                 hide_index=True, width="stretch",
                 column_config={"RISK_SCORE": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%.0f"),
                                "TOTAL_ANNUAL_PREMIUM": st.column_config.NumberColumn("Premium ₹", format="₹%d"),
                                "DAYS_TO_RENEWAL": st.column_config.NumberColumn("Renews in (d)")})


# ============================================================================= ASK
def ask_tab():
    st.markdown("Ask in plain English, for example:")
    cols = st.columns(3)
    for i, ex in enumerate(chat.EXAMPLES):
        if cols[i % 3].button(ex, key=f"ex{i}", width="stretch"):
            st.session_state.ask_q = ex
    q = st.chat_input("Ask about customers, risk, renewals, premium…")
    q = q or st.session_state.pop("ask_q", None)
    hist = st.session_state.setdefault("ask_hist", [])
    if q:
        if LIVE:
            a = chat.answer_live(q, cortex_complete)
            if a.sql and not a.text:
                try:
                    a.table = sql(a.sql)
                    a.text = f"Cortex wrote and ran this query; **{len(a.table)} rows**."
                except Exception as e:
                    a.text = f"Query failed: {e}"
        else:
            a = chat.answer_demo(q, D)
        if a.customer_id:
            st.session_state.focus_customer = a.customer_id
        hist.append((q, a))
    for q, a in reversed(hist[-6:]):
        with st.chat_message("user"):
            st.write(q)
        with st.chat_message("assistant", avatar="🛡️"):
            st.markdown(a.text)
            if a.filters:
                st.caption("Interpreted as: " + " · ".join(a.filters))
            if a.sql:
                with st.expander("SQL generated by Cortex AI_COMPLETE"):
                    st.code(a.sql, language="sql")
            if a.table is not None and len(a.table):
                st.dataframe(a.table, hide_index=True, width="stretch",
                             column_config={"TOTAL_ANNUAL_PREMIUM": st.column_config.NumberColumn("Premium ₹", format="₹%d")})
            if a.customer_id:
                st.caption("Tip: the Customer 360 tab now opens on this customer.")
    if not LIVE:
        st.caption("Demo mode uses a transparent rule-based interpreter. With Snowflake secrets, questions go to "
                   "Cortex AI_COMPLETE (text-to-SQL, read-only, allow-listed tables).")


# ============================================================================= HOW IT WORKS
def how_tab():
    from pathlib import Path
    img = Path(__file__).parent / "submission" / "architecture.png"
    if img.exists():
        st.image(str(img), width="stretch")
    st.markdown("""
| CoCo CLI skill | Input | Cortex / Snowflake | Output |
|---|---|---|---|
| `$c360-unify` | RAW customers, policies, claims, payments, transcripts | SQL views, `AS_OF_DATE()` | `CURATED.CUSTOMER_360` |
| `$interaction-intel` | RAW.CALL_TRANSCRIPTS (unstructured) | `CORTEX.SENTIMENT`, `AI_CLASSIFY`, `AI_COMPLETE`, Cortex Search | `CURATED.INTERACTION_INSIGHTS` |
| `$next-best-action` | 360 + insights | Weighted explainable risk, grounded `AI_COMPLETE` | `APP.CHURN_RISK`, `APP.NEXT_BEST_ACTIONS` |

**Run alone or chained** in Cortex Code CLI: `$c360-unify` → `$interaction-intel` → `$next-best-action`.
The skills share Snowflake tables as their contract, so each one can be re-run on its own. This app reads `APP.NEXT_BEST_ACTIONS`
(LIVE mode), or the same tables exported to Parquet (DEMO mode).
""")
    st.caption(f"Data source: {META.get('source')} · {META.get('note', '')}")


with tab_c:
    customer_tab()
with tab_p:
    portfolio_tab()
with tab_a:
    ask_tab()
with tab_h:
    how_tab()
