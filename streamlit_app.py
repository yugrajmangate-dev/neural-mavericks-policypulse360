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

# ----------------------------------------------------------------------------- design tokens (dark)
BG, SURFACE, LINE = "#0B1220", "#111A2E", "#1E2A44"
INK, INK2, MUTED = "#E5E7EB", "#CBD5E1", "#8B98AE"
GRID, AXIS = "rgba(148,163,184,0.13)", "rgba(148,163,184,0.32)"
ACCENT = "#22D3EE"
HIGH, MED, LOW = "#F87171", "#FBBF24", "#34D399"            # status: critical / warning / good
NEG, NEU, POS = "#F87171", "#64748B", "#38BDF8"             # diverging sentiment: red / slate / blue
BAND_COLOR = {"High": HIGH, "Medium": MED, "Low": LOW}
BAND_ICON = {"High": "▲", "Medium": "●", "Low": "▼"}
INTENT_LABEL = {"cancellation_intent": "Cancellation", "claim_issue": "Claim issue", "price_concern": "Price concern",
                "upsell_interest": "Upsell interest", "service_praise": "Service praise",
                "general_service": "General service"}
ACTION_ICON = {"RETENTION_CALL": "📞", "CLAIM_ESCALATION": "⚡", "PRICE_MATCH": "🏷️", "PAYMENT_FLEX": "💳",
               "RENEWAL_NUDGE": "🔔", "CROSS_SELL": "➕", "ADVOCACY": "⭐", "NURTURE": "🌱"}
TTL = 3600  # demo files never change; in LIVE mode this bounds Snowflake round-trips to one per hour

st.markdown(f"""
<style>
  .block-container {{padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1320px;}}
  h1, h2, h3, h4 {{letter-spacing: -0.01em;}}
  .pp-brand {{display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; margin:.2rem 0 .15rem 0; line-height:1.25;}}
  .pp-brand .name {{font-size:1.95rem; font-weight:750; color:{INK};}}
  .pp-brand .name b {{color:{ACCENT}; font-weight:750;}}
  .pp-brand .tag {{color:{MUTED}; font-size:.98rem;}}
  .pp-mode {{display:inline-flex; align-items:center; gap:.35rem; padding:1px 8px; border-radius:999px;
            font-size:.66rem; font-weight:600; letter-spacing:.05em; text-transform:uppercase; white-space:nowrap;
            color:{MUTED}; border:1px solid {LINE}; background:rgba(148,163,184,.06);}}
  .pp-mode i {{width:6px; height:6px; border-radius:50%; background:{MUTED}; display:inline-block;}}
  .pp-mode.cortex {{color:#7DD3FC; border-color:rgba(56,189,248,.35); background:rgba(56,189,248,.08);}}
  .pp-mode.cortex i {{background:#38BDF8;}}
  .pp-mode.live {{color:{LOW}; border-color:rgba(52,211,153,.35); background:rgba(52,211,153,.08);}}
  .pp-mode.live i {{background:{LOW}; box-shadow:0 0 6px {LOW};}}
  .pp-badge {{display:inline-block; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:650;
             border:1px solid {LINE}; color:{INK};}}
  .pp-card {{background:{SURFACE}; border:1px solid {LINE}; border-radius:14px; padding:1rem 1.15rem;
            box-shadow:0 1px 0 rgba(255,255,255,.03) inset, 0 8px 24px rgba(0,0,0,.25); height:100%;}}
  .pp-profile {{display:flex; gap:1.4rem; flex-wrap:wrap; align-items:center;}}
  .pp-profile .who {{font-size:1.45rem; font-weight:720; color:{INK};}}
  .pp-profile .meta {{color:{MUTED}; font-size:.92rem;}}
  .pp-profile .meta b {{color:{INK2};}}
  .pp-chip {{display:inline-block; padding:2px 9px; margin:2px 4px 2px 0; border-radius:999px; font-size:.78rem;
            background:rgba(148,163,184,.10); color:{INK2}; border:1px solid {LINE};}}
  .pp-chip.ev {{background:rgba(34,211,238,.08); color:#67E8F9; border-color:rgba(34,211,238,.25);
               font-family:ui-monospace,Consolas,monospace;}}
  .pp-kpis {{display:grid; grid-template-columns:repeat(auto-fit, minmax(165px, 1fr)); gap:.75rem; margin:.85rem 0 1rem 0;}}
  .pp-kpi {{position:relative; overflow:hidden; background:linear-gradient(180deg, #132036 0%, {SURFACE} 100%);
           border:1px solid {LINE}; border-radius:14px; padding:.8rem 1rem .75rem 1rem;}}
  .pp-kpi::before {{content:""; position:absolute; left:0; top:0; right:0; height:2px;
                   background:linear-gradient(90deg, var(--tone, {ACCENT}), transparent 80%);}}
  .pp-kpi .l {{color:{MUTED}; font-size:.7rem; font-weight:600; text-transform:uppercase; letter-spacing:.07em;}}
  .pp-kpi .v {{color:{INK}; font-size:1.5rem; font-weight:720; margin-top:.2rem; line-height:1.2;
              font-variant-numeric:tabular-nums;}}
  .pp-kpi .s {{color:{MUTED}; font-size:.78rem; margin-top:.15rem; min-height:1em;}}
  .pp-action {{font-size:1.18rem; font-weight:700; color:{INK}; margin:.2rem 0 .5rem 0; line-height:1.35;}}
  .pp-reason {{color:{INK2}; font-size:.95rem; line-height:1.5;}}
  .pp-reason b {{color:{INK};}}
  .pp-small {{color:{MUTED}; font-size:.78rem;}}
  .pp-small b {{color:{INK2};}}
  .pp-call {{border-left:3px solid {LINE}; padding:.35rem 0 .55rem .85rem; margin-left:.3rem;}}
  .pp-call .when {{color:{MUTED}; font-size:.8rem;}}
  .pp-call .sum {{color:{INK}; font-size:.95rem;}}
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


def sent_color(s: float) -> str:
    return NEG if s <= -0.25 else POS if s >= 0.25 else NEU


def band_badge(band: str, score: float | None = None) -> str:
    c = BAND_COLOR[band]
    txt = f"{BAND_ICON[band]} {band} risk" + (f" · {score:.0f}" if score is not None else "")
    return f'<span class="pp-badge" style="background:{rgba(c, .14)};color:{c};border-color:{rgba(c, .45)}">{txt}</span>'


def kpi_row(items: list[tuple]) -> None:
    """items: (label, value, sub, tone colour or None, tooltip or None)."""
    cells = "".join(
        f'<div class="pp-kpi" style="--tone:{tone or ACCENT}" title="{html.escape(tip or "", quote=True)}">'
        f'<div class="l">{label}</div><div class="v">{value}</div><div class="s">{sub or "&nbsp;"}</div></div>'
        for label, value, sub, tone, tip in items)
    st.markdown(f'<div class="pp-kpis">{cells}</div>', unsafe_allow_html=True)


def style_fig(fig: go.Figure, h: int = 300) -> go.Figure:
    fig.update_layout(height=h, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="system-ui, Segoe UI, sans-serif", color=INK2, size=12),
                      legend=dict(orientation="h", y=1.12, x=0, title=None, font=dict(color=INK2)),
                      hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE, font=dict(color=INK)), bargap=0.28)
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=AXIS, linecolor=AXIS, tickfont=dict(color=MUTED),
                     title_font=dict(color=MUTED))
    return fig


PLOT_CFG = {"displayModeBar": False}
SEP = dict(color=BG, width=1.5)  # thin background-coloured separators between stacked bars


# ----------------------------------------------------------------------------- data (cached once per TTL)
@st.cache_data(ttl=TTL, show_spinner="Loading PolicyPulse data…")
def get_bundle() -> tuple[bool, dict[str, pd.DataFrame], dict, str | None]:
    """Load everything once. A failed live connection is cached as a demo fallback, so it isn't retried on
    every widget interaction."""
    live, err = is_live(), None
    try:
        d = load(live)
    except Exception as e:  # live connection failed -> fall back to demo files
        live, err = False, type(e).__name__
        d = load(False)
    return live, d, meta(live), err


@st.cache_data(ttl=TTL, show_spinner=False)
def customer_index() -> tuple[list[str], dict[str, str]]:
    nba = get_bundle()[1]["nba"]
    order = nba.sort_values("RISK_SCORE", ascending=False)
    labels = {r.CUSTOMER_ID: f"{r.FULL_NAME} · {r.CUSTOMER_ID} · {r.CITY} · {r.RISK_BAND} {r.RISK_SCORE:.0f}"
              for r in order.itertuples()}
    return list(labels), labels


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=256)
def customer_view(cid: str) -> dict:
    D = get_bundle()[1]
    ins, pol, clm, pay = D["ins"], D["pol"], D["clm"], D["pay"]
    cpay = pay[pay.CUSTOMER_ID == cid]
    pay_m = (cpay.assign(M=cpay.DUE_DATE.dt.to_period("M").dt.to_timestamp())
             .groupby(["M", "PAYMENT_STATUS"]).size().unstack(fill_value=0)) if len(cpay) else None
    return dict(n=D["nba"][D["nba"].CUSTOMER_ID == cid].iloc[0], c=D["c360"][D["c360"].CUSTOMER_ID == cid].iloc[0],
                cins=ins[ins.CUSTOMER_ID == cid].sort_values("CALL_TS"), cpol=pol[pol.CUSTOMER_ID == cid],
                cclm=clm[clm.CUSTOMER_ID == cid], cpay=cpay.sort_values("DUE_DATE", ascending=False), pay_m=pay_m)


@st.cache_data(ttl=TTL, show_spinner=False)
def filter_options() -> tuple[list[str], list[str]]:
    nba = get_bundle()[1]["nba"]
    return sorted(nba.SEGMENT.unique()), sorted(nba.CITY.unique())


@st.cache_data(ttl=TTL, show_spinner=False, max_entries=128)
def portfolio_view(prod: tuple, seg: tuple, city: tuple) -> dict | None:
    D = get_bundle()[1]
    nba, pol, ins = D["nba"], D["pol"], D["ins"]
    df = nba
    if prod:
        df = df[df.CUSTOMER_ID.isin(pol[pol.PRODUCT_LINE.isin(prod)].CUSTOMER_ID)]
    if seg:
        df = df[df.SEGMENT.isin(seg)]
    if city:
        df = df[df.CITY.isin(city)]
    if df.empty:
        return None
    hi = df[df.RISK_BAND == "High"]
    bands = df[["CUSTOMER_ID", "RISK_BAND"]]

    pp = pol[pol.CUSTOMER_ID.isin(df.CUSTOMER_ID) & (pol.STATUS != "Lapsed")].merge(bands, on="CUSTOMER_ID")
    by_product = pp.groupby(["PRODUCT_LINE", "RISK_BAND"]).ANNUAL_PREMIUM.sum().unstack(fill_value=0)

    ii = ins[ins.CUSTOMER_ID.isin(df.CUSTOMER_ID) & (ins.CALL_TS >= AS_OF - pd.Timedelta(days=180))]
    intents = ii.groupby(["PRIMARY_INTENT", "SENTIMENT_LABEL"]).size().unstack(fill_value=0)
    intents = intents.loc[intents.sum(axis=1).sort_values().index]

    up = pol[pol.CUSTOMER_ID.isin(df.CUSTOMER_ID) & pol.RENEWAL_DATE.between(AS_OF, AS_OF + pd.Timedelta(days=90))]
    up = up.merge(bands, on="CUSTOMER_ID")
    up["WEEK"] = up.RENEWAL_DATE.dt.to_period("W-SUN").dt.start_time
    renewals = up.groupby(["WEEK", "RISK_BAND"]).ANNUAL_PREMIUM.sum().unstack(fill_value=0)

    plays = df.ACTION_CATEGORY.value_counts().sort_values()

    top = df.sort_values(["RISK_SCORE", "TOTAL_ANNUAL_PREMIUM"], ascending=False).head(25).copy()
    top["TOP_DRIVERS"] = top.RISK_DRIVERS.map(lambda ds: " · ".join([f"{x['factor']} +{x['points']:.0f}"
                                                                    for x in ds if x["points"] > 0][:3]))
    top["RISK"] = top.RISK_BAND.map(lambda b: f"{BAND_ICON[b]} {b}")
    top = top[["CUSTOMER_ID", "FULL_NAME", "CITY", "SEGMENT", "RISK_SCORE", "RISK", "TOTAL_ANNUAL_PREMIUM",
               "NEXT_RENEWAL_PRODUCT", "DAYS_TO_RENEWAL", "TOP_DRIVERS", "ACTION"]]

    prem = df.TOTAL_ANNUAL_PREMIUM.sum()
    return dict(n=len(df), n_hi=len(hi), hi_prem=hi.TOTAL_ANNUAL_PREMIUM.sum(), prem=prem,
                exp_loss=df.EXPECTED_PREMIUM_LOSS.sum(), hi_renew30=int((hi.DAYS_TO_RENEWAL <= 30).sum()),
                by_product=by_product, intents=intents, renewals=renewals, plays=plays, top=top)


LIVE, D, META, LOAD_ERR = get_bundle()
if LOAD_ERR:
    st.warning(f"Live Snowflake connection failed ({LOAD_ERR}); showing demo data.")
nba, c360, ins, pol = D["nba"], D["c360"], D["ins"], D["pol"]

# Mode badge: real Cortex export is detected from meta.json (written by scripts/export_demo_data.py)
src = str(META.get("source", ""))
if LIVE:
    mode_html = '<span class="pp-mode live"><i></i>Live · Snowflake + Cortex</span>'
elif src.startswith("snowflake"):
    exported = str(META.get("generated_at", ""))[:10]
    mode_html = (f'<span class="pp-mode cortex" title="Pipeline outputs exported from Snowflake Cortex">'
                 f'<i></i>Demo · Cortex outputs{" · " + exported if exported else ""}</span>')
else:
    mode_html = ('<span class="pp-mode" title="Offline simulation of the Cortex pipeline; re-export from Snowflake '
                 'for real Cortex outputs"><i></i>Demo mode</span>')

st.markdown(f"""<div class="pp-brand"><span class="name">Policy<b>Pulse</b> 360</span>
<span class="tag">Customer 360 + Next Best Action for insurance retention teams</span>{mode_html}</div>""",
            unsafe_allow_html=True)
st.caption(f"Fictional insurer *Kavach Insurance* · {len(c360)} customers · {len(pol)} policies · "
           f"{len(ins)} AI-analysed call transcripts · as of {AS_OF:%d %b %Y}")


# ============================================================================= CUSTOMER 360
def gauge(score: float, band: str) -> go.Figure:
    col = BAND_COLOR[band]
    g = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number=dict(font=dict(size=44, color=col), valueformat=".0f"),
        title=dict(text=f"<span style='font-size:12px;color:{MUTED}'>{BAND_ICON[band]} {band} risk · of 100</span>"),
        gauge=dict(shape="angular", axis=dict(range=[0, 100], tickvals=[0, 30, 55, 100], tickwidth=0,
                                              tickcolor="rgba(0,0,0,0)", tickfont=dict(size=10, color=MUTED)),
                   bar=dict(color=col, thickness=1.0), bgcolor=rgba("#94A3B8", .12), borderwidth=0),
        domain=dict(x=[0, 1], y=[0, 0.92])))
    g = style_fig(g, 200)
    g.update_layout(margin=dict(l=24, r=24, t=34, b=4))
    return g


def drivers_fig(drv: list[dict]) -> go.Figure:
    dd = pd.DataFrame(drv)[::-1]
    mx = max(dd.points.abs().max(), 1)
    # intensity scales with weight; red adds risk, green is protective
    colors = [rgba(HIGH if p > 0 else LOW, 0.30 + 0.70 * abs(p) / mx) for p in dd.points]
    fig = go.Figure(go.Bar(
        x=dd.points, y=dd.factor, orientation="h",
        marker=dict(color=colors, cornerradius=4, line=dict(width=0)),
        text=[f"{p:+.0f}" for p in dd.points], textposition="outside",
        textfont=dict(color=[HIGH if p > 0 else LOW for p in dd.points]),
        customdata=dd.detail, hovertemplate="<b>%{y}</b><br>%{customdata}<br>%{x:+.1f} pts<extra></extra>"))
    fig.update_xaxes(range=[min(-7, dd.points.min() - 3), max(28, dd.points.max() + 5)], title=None)
    fig.update_yaxes(tickfont=dict(color=INK2))
    return style_fig(fig, 40 + 34 * len(dd))


@st.fragment
def customer_tab():
    ids, labels = customer_index()
    default = st.session_state.get("focus_customer", "C0004")
    idx = ids.index(default) if default in ids else 0
    cid = st.selectbox("Search customer (name, ID or city)", ids, index=idx, format_func=labels.get,
                       help="Sorted by churn risk. Type to search.")
    v = customer_view(cid)
    n, c, cins, cpol, cclm, cpay = v["n"], v["c"], v["cins"], v["cpol"], v["cclm"], v["cpay"]

    # profile strip
    st.markdown(f"""<div class="pp-card"><div class="pp-profile">
      <div><div class="who">{html.escape(c.FULL_NAME)}</div>
      <div class="meta">{c.CUSTOMER_ID} · {c.AGE} yrs · {c.CITY}, {c.STATE} · {c.SEGMENT} · customer {c.TENURE_YEARS:.1f} yrs</div>
      <div class="meta">Prefers <b>{c.PREFERRED_CHANNEL}</b> · {c.PREFERRED_LANGUAGE} · KYC {c.KYC_STATUS}</div></div>
      <div style="margin-left:auto">{band_badge(n.RISK_BAND, n.RISK_SCORE)}</div></div>
      <div style="margin-top:.5rem">{''.join(f'<span class="pp-chip">{p}</span>' for p in str(c.PRODUCT_LINES).split(', '))}</div>
    </div>""", unsafe_allow_html=True)

    dtr = c.DAYS_TO_RENEWAL
    s90 = c.AVG_SENTIMENT_90D if pd.notna(c.AVG_SENTIMENT_90D) else c.AVG_SENTIMENT_180D
    kpi_row([
        ("Annual premium", inr(c.TOTAL_ANNUAL_PREMIUM), None, ACCENT, None),
        ("Active policies", int(c.N_ACTIVE_POLICIES), None, ACCENT, None),
        ("Next renewal", f"{int(dtr)} days" if pd.notna(dtr) else "—",
         html.escape(str(c.NEXT_RENEWAL_PRODUCT)) if pd.notna(dtr) else None,
         HIGH if pd.notna(dtr) and dtr <= 30 else ACCENT, f"{c.NEXT_RENEWAL_PRODUCT} · {c.NEXT_RENEWAL_POLICY_ID}"),
        ("Claims (18m)", int(c.N_CLAIMS), f"{int(c.N_OPEN_CLAIMS)} open", MED if c.N_OPEN_CLAIMS else ACCENT, None),
        ("Sentiment (90d)", f"{s90:+.2f}" if pd.notna(s90) else "—", "Cortex SENTIMENT, −1…+1",
         sent_color(s90) if pd.notna(s90) else ACCENT, "Cortex SENTIMENT on the customer's words, −1…+1"),
    ])

    left, right = st.columns([5, 7], gap="medium")
    with left:
        with st.container(border=True):
            st.markdown("**Churn risk** — explainable score")
            st.plotly_chart(gauge(float(n.RISK_SCORE), n.RISK_BAND), width="stretch", config=PLOT_CFG)
            drv = [d for d in n.RISK_DRIVERS if d["points"] != 0]
            if drv:
                st.plotly_chart(drivers_fig(drv), width="stretch", config=PLOT_CFG)
                st.markdown('<span class="pp-small">Red adds risk, green is protective; brighter bars weigh more. '
                            'Weights are documented in the <code>next-best-action</code> skill.</span>',
                            unsafe_allow_html=True)
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
                        st.rerun(scope="fragment")
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
            st.markdown(f"""<div class="pp-call" style="border-left-color:{sent_color(r.SENTIMENT_SCORE)}">
              <div class="when">{r.CALL_TS:%a %d %b %Y, %H:%M} · {r.TRANSCRIPT_ID} · {html.escape(str(r.AGENT_ID))} ·
              <span class="pp-chip">{INTENT_LABEL.get(r.PRIMARY_INTENT, r.PRIMARY_INTENT)}</span>
              <span class="pp-chip">sentiment {r.SENTIMENT_SCORE:+.2f} ({r.SENTIMENT_LABEL})</span></div>
              <div class="sum">{html.escape(str(r.SUMMARY))}</div></div>""", unsafe_allow_html=True)
            with st.expander(f"Full transcript {r.TRANSCRIPT_ID}"):
                st.text(r.TRANSCRIPT_TEXT)
    with t2:
        if len(cins):
            fig = go.Figure()
            fig.add_hline(y=0, line=dict(color=AXIS, width=1))
            fig.add_trace(go.Scatter(
                x=cins.CALL_TS, y=cins.SENTIMENT_SCORE, mode="lines+markers", line=dict(color=MUTED, width=2),
                marker=dict(size=12, color=[sent_color(s) for s in cins.SENTIMENT_SCORE], line=dict(color=BG, width=2)),
                customdata=list(zip(cins.TRANSCRIPT_ID, cins.PRIMARY_INTENT.map(INTENT_LABEL), cins.SUMMARY)),
                hovertemplate="<b>%{customdata[0]}</b> · %{x|%d %b %Y}<br>%{customdata[1]} · sentiment %{y:+.2f}"
                              "<br>%{customdata[2]}<extra></extra>", name="sentiment"))
            fig.update_yaxes(range=[-1.05, 1.05], title="customer sentiment", tickvals=[-1, -0.5, 0, 0.5, 1])
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig, 300), width="stretch", config=PLOT_CFG)
            st.caption("Each dot is a call: red negative, slate neutral, blue positive. Hover for the AI summary.")
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
        m = v["pay_m"]
        if m is not None:
            fig = go.Figure()
            for s, col in [("On-time", LOW), ("Late", MED), ("Missed", HIGH)]:
                if s in m:
                    fig.add_trace(go.Bar(x=m.index, y=m[s], name=s, marker=dict(color=col, line=SEP),
                                         hovertemplate=f"%{{x|%b %Y}} · {s}: %{{y}}<extra></extra>"))
            fig.update_layout(barmode="stack")
            fig.update_yaxes(title="instalments", dtick=1)
            st.plotly_chart(style_fig(fig, 260), width="stretch", config=PLOT_CFG)
            st.dataframe(cpay.drop(columns=["CUSTOMER_ID"]), hide_index=True, width="stretch")


# ============================================================================= PORTFOLIO
def band_bars(g: pd.DataFrame, hover_x: str) -> go.Figure:
    fig = go.Figure()
    for band in ["High", "Medium", "Low"]:
        if band in g:
            fig.add_trace(go.Bar(x=g.index, y=g[band] / 1e5, name=f"{BAND_ICON[band]} {band}",
                                 marker=dict(color=BAND_COLOR[band], line=SEP),
                                 hovertemplate=hover_x + " · " + band + ": ₹%{y:.1f} L<extra></extra>"))
    fig.update_layout(barmode="stack")
    return fig


@st.fragment
def portfolio_tab():
    segs, cities = filter_options()
    f1, f2, f3 = st.columns(3)
    prod = f1.multiselect("Product line", ["Health", "Motor", "Life", "Home"], placeholder="All products")
    seg = f2.multiselect("Segment", segs, placeholder="All segments")
    city = f3.multiselect("City", cities, placeholder="All cities")
    p = portfolio_view(tuple(sorted(prod)), tuple(sorted(seg)), tuple(sorted(city)))
    if p is None:
        st.info("No customers match these filters.")
        return
    kpi_row([
        ("Customers", f"{p['n']:,}", "in current filter", ACCENT, None),
        ("High risk", f"{p['n_hi']:,}", f"{p['n_hi'] / p['n']:.0%} of book", HIGH, None),
        ("Premium at risk (High)", inr(p["hi_prem"]), f"{p['hi_prem'] / max(p['prem'], 1):.0%} of premium", HIGH, None),
        ("Expected premium loss", inr(p["exp_loss"]), "Σ premium × risk / 100", MED, "Σ premium × risk score / 100"),
        ("Renewals ≤ 30d · High risk", p["hi_renew30"], "call these first", HIGH if p["hi_renew30"] else LOW, None),
    ])

    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        st.markdown("**Annual premium by product line and risk band**")
        fig = band_bars(p["by_product"], "%{x}")
        fig.update_yaxes(title="₹ lakh")
        st.plotly_chart(style_fig(fig, 300), width="stretch", config=PLOT_CFG)
    with b, st.container(border=True):
        st.markdown("**What customers call about**: intent × sentiment (Cortex, 180d)")
        g = p["intents"]
        fig = go.Figure()
        for s, col in [("negative", NEG), ("neutral", NEU), ("positive", POS)]:
            if s in g:
                fig.add_trace(go.Bar(y=[INTENT_LABEL.get(i, i) for i in g.index], x=g[s], name=s, orientation="h",
                                     marker=dict(color=col, line=SEP),
                                     hovertemplate="%{y} · " + s + ": %{x} calls<extra></extra>"))
        fig.update_layout(barmode="stack")
        fig.update_xaxes(title="calls")
        fig.update_yaxes(tickfont=dict(color=INK2))
        st.plotly_chart(style_fig(fig, 300), width="stretch", config=PLOT_CFG)

    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        st.markdown("**Renewal pipeline**: next 90 days, by week")
        fig = band_bars(p["renewals"], "wk of %{x|%d %b}")
        fig.update_yaxes(title="₹ lakh renewing")
        st.plotly_chart(style_fig(fig, 280), width="stretch", config=PLOT_CFG)
    with b, st.container(border=True):
        st.markdown("**Recommended plays** (customers per next best action)")
        g = p["plays"]
        fig = go.Figure(go.Bar(y=[f"{ACTION_ICON.get(i, '')} {i.replace('_', ' ').title()}" for i in g.index], x=g.values,
                               orientation="h", marker=dict(color=ACCENT, cornerradius=4), text=g.values,
                               textposition="outside", textfont=dict(color=INK2),
                               hovertemplate="%{y}: %{x} customers<extra></extra>"))
        fig.update_xaxes(range=[0, g.max() * 1.15])
        fig.update_yaxes(tickfont=dict(color=INK2))
        st.plotly_chart(style_fig(fig, 280), width="stretch", config=PLOT_CFG)

    st.markdown("#### Call list: top at-risk customers")
    st.dataframe(p["top"], hide_index=True, width="stretch",
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


# Lazy tabs: only the open tab executes, so first paint renders one tab instead of all four.
tab_c, tab_p, tab_a, tab_h = st.tabs(["🎯 Customer 360 + NBA", "📊 Portfolio", "💬 Ask PolicyPulse", "🧩 How it works"],
                                     key="main_tab", on_change="rerun")
if tab_c.open:
    with tab_c:
        customer_tab()
if tab_p.open:
    with tab_p:
        portfolio_tab()
if tab_a.open:
    with tab_a:
        ask_tab()
if tab_h.open:
    with tab_h:
        how_tab()
