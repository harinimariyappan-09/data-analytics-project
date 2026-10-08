"""
Retail Executive Dashboard (Streamlit + Plotly)

Run locally:   streamlit run app.py
Data:          clean_dataset.csv (Task 3 output), marketing_spend.csv (illustrative), india_zones.geojson
KPI logic:     dashboard_metrics.py (shared with build_dashboard_pdf.py)
"""
import calendar

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from dashboard_metrics import CHURN_WINDOW_DAYS, REGIONS_ALL, ZONES, DashboardData, load_geojson, load_orders, load_spend

st.set_page_config(page_title="Retail Executive Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------------------------------------- style
BLUE, GREEN, ORANGE, RED, GREY = "#2563EB", "#16A34A", "#F97316", "#DC2626", "#94A3B8"
st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 1.5rem; max-width: 1500px;}
[data-testid="stMetricValue"] {font-size: 2.1rem; font-weight: 700;}
[data-testid="stMetricLabel"] p {font-size: 0.95rem; font-weight: 600; text-transform: uppercase; letter-spacing: .03em;}
.tile {border: 1px solid rgba(128,128,128,.28); border-radius: 10px; padding: 10px 14px; background: rgba(128,128,128,.07);}
.tile .l {font-size: .74rem; font-weight: 600; text-transform: uppercase; letter-spacing: .03em; opacity: .7;}
.tile .v {font-size: 1.45rem; font-weight: 700; line-height: 1.25;}
.tile .d {font-size: .8rem;}
.badge {display: inline-block; font-size: .72rem; padding: 2px 9px; border-radius: 99px; background: rgba(249,115,22,.15); color: #c2410c; margin-right: 6px;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------- data
@st.cache_resource(show_spinner="Loading data...")
def get_data() -> DashboardData:
    return DashboardData(load_orders(), load_spend())


@st.cache_resource
def get_geo() -> dict:
    return load_geojson()


dd = get_data()
geo = get_geo()


@st.cache_data(show_spinner=False)
def monthly_cached(regions: tuple, categories: tuple, methods: tuple) -> pd.DataFrame:
    return dd.monthly(list(regions), list(categories), list(methods))


# ---------------------------------------------------------------------------------------------- helpers
def inr(x):
    return "n/a" if x is None or pd.isna(x) else f"₹{x:,.0f}"


def inr_short(x):
    if x is None or pd.isna(x):
        return "n/a"
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.1f} L"
    return f"₹{x:,.0f}"


def pct(x, d=1):
    return "n/a" if x is None or pd.isna(x) else f"{x * 100:.{d}f}%"


def rel(x):
    return None if x is None else f"{x:+.1%}"


def tile(label, value, delta_txt=None, good=None):
    color = {True: GREEN, False: RED, None: "inherit"}[good]
    d = f"<div class='d' style='color:{color}'>{delta_txt}</div>" if delta_txt else "<div class='d'>&nbsp;</div>"
    return f"<div class='tile'><div class='l'>{label}</div><div class='v'>{value}</div>{d}</div>"


def good_if(delta, higher_is_good=True):
    if delta is None or delta == 0:
        return None
    return (delta > 0) == higher_is_good


def spark(series):
    s = series.dropna()
    return s.tolist() if len(s) >= 2 else None


# ---------------------------------------------------------------------------------------------- sidebar slicers
labels = [m.strftime("%b %Y") for m in dd.months]
PRESETS = ["Custom", "All time", "Last 12 months", "Last 6 months", "Year 2025", "Year 2024", "Year 2023"]

if "period_ver" not in st.session_state:
    st.session_state["period_ver"] = 0
    st.session_state["period_default"] = (labels[0], labels[-1])


def apply_preset():
    p = st.session_state["preset"]
    n = len(labels)
    if p == "All time":
        a, b = 0, n - 1
    elif p == "Last 12 months":
        a, b = n - 12, n - 1
    elif p == "Last 6 months":
        a, b = n - 6, n - 1
    elif p.startswith("Year"):
        yr = int(p.split()[1])
        idx = [i for i, m in enumerate(dd.months) if m.year == yr]
        a, b = idx[0], idx[-1]
    else:
        return
    st.session_state["period_default"] = (labels[a], labels[b])
    st.session_state["period_ver"] += 1          # new widget key -> slider restarts at the preset range


with st.sidebar:
    st.header("🎛️ Slicers")
    st.selectbox("Quick range", PRESETS, key="preset", on_change=apply_preset)
    period = st.select_slider("Period (drag both ends)", options=labels, value=st.session_state["period_default"],
                              key=f"period_{st.session_state['period_ver']}")
    regions = st.multiselect("Region (sales zone)", REGIONS_ALL, default=REGIONS_ALL)
    categories = st.multiselect("Product category", dd.categories, default=dd.categories)
    methods = st.multiselect("Payment method", dd.methods, default=dd.methods)
    st.divider()
    st.caption("**Which KPIs respond to which slicer?**\n\n"
               "- Revenue, AOV, Orders, Profit: all slicers\n"
               "- CAC, New / Active customers, Churn: Period and Region only (spend and customer history are not split by category or payment method)")

if not (regions and categories and methods):
    st.warning("Select at least one value in every slicer.")
    st.stop()

i0, i1 = labels.index(period[0]), labels.index(period[1])
n_months = i1 - i0 + 1
m = monthly_cached(tuple(regions), tuple(categories), tuple(methods))
cur, prev, delta = dd.kpis_with_delta(m, i0, i1)
win = m.iloc[i0:i1 + 1]
start_p, end_p = dd.months[i0], dd.months[i1]

# ---------------------------------------------------------------------------------------------- header
st.markdown("## 📊 Retail Executive Dashboard")
st.markdown(f"<span class='badge'>Synthetic data</span><span class='badge'>Marketing spend is illustrative</span>"
            f"**{period[0]} → {period[1]}** ({n_months} months) &nbsp;·&nbsp; {len(regions)} region(s) &nbsp;·&nbsp; "
            f"{len(categories)} categor{'y' if len(categories) == 1 else 'ies'}", unsafe_allow_html=True)

# ---------------------------------------------------------------------------------------------- level 1: headline KPIs
vs = f"vs previous {n_months} month{'s' if n_months > 1 else ''}"
c1, c2, c3, c4 = st.columns(4)
with c1, st.container(border=True):
    st.metric("Revenue", inr_short(cur["revenue"]), rel(delta["revenue"]), help=f"Paid orders only. Delta {vs}.",
              chart_data=spark(win["revenue"]), chart_type="area")
with c2, st.container(border=True):
    st.metric("Average order value", inr(cur["aov"]), rel(delta["aov"]), help=f"Revenue / paid orders. Delta {vs}.",
              chart_data=spark(win["aov"]), chart_type="line")
with c3, st.container(border=True):
    st.metric("Customer acquisition cost", inr(cur["cac"]), rel(delta["cac"]), delta_color="inverse",
              help=f"Marketing spend / new customers (spend is ILLUSTRATIVE). Lower is better. Delta {vs}.",
              chart_data=spark(win["cac"]), chart_type="line")
with c4, st.container(border=True):
    ch = None if delta["churn"] is None else f"{round(delta['churn'] * 100, 1) + 0:+.1f} pp"
    st.metric("Churn rate (monthly)", pct(cur["churn"]), ch, delta_color="inverse",
              help=f"Share of customers active last month who have now gone {CHURN_WINDOW_DAYS} days without buying (average per month). "
                   f"Needs {CHURN_WINDOW_DAYS} days of history, so it starts Jul 2023. Lower is better. Delta {vs} in percentage points.",
              chart_data=spark(win["churn_rate"]), chart_type="line")

# ---------------------------------------------------------------------------------------------- level 2: supporting KPIs
t1, t2, t3, t4 = st.columns(4)
t1.markdown(tile("Paid orders", f"{cur['orders']:,.0f}", rel(delta["orders"]), good_if(delta["orders"])), unsafe_allow_html=True)
mg = f"margin {pct(cur['margin'])}" + (f" ({round(delta['margin'] * 100, 1) + 0:+.1f} pp)" if delta["margin"] is not None else "")
t2.markdown(tile("Gross profit", inr_short(cur["profit"]), mg, good_if(delta["margin"])), unsafe_allow_html=True)
t3.markdown(tile("New customers", f"{cur['new_customers']:,.0f}", rel(delta["new_customers"]), good_if(delta["new_customers"])), unsafe_allow_html=True)
t4.markdown(tile(f"Active customers ({CHURN_WINDOW_DAYS}d)", "n/a" if pd.isna(cur["active"]) else f"{cur['active']:,.0f}", rel(delta["active"]), good_if(delta["active"])),
            unsafe_allow_html=True)
st.write("")

# ---------------------------------------------------------------------------------------------- level 3: trend (drill-down) + map
period_orders = dd.paid_filtered(regions, categories, methods)
period_orders = period_orders[(period_orders["ym"] >= start_p) & (period_orders["ym"] <= end_p)]

left, right = st.columns([3, 2])

with left, st.container(border=True):
    st.markdown("#### Revenue & profit trend &nbsp; <small>(drill down: Year → Quarter → Month → Day)</small>", unsafe_allow_html=True)

    if "level" not in st.session_state:
        st.session_state["level"] = "Month"
    years = sorted(period_orders["year"].unique())
    for k, opts in (("drill_year", ["All"] + [str(y) for y in years]),):
        if st.session_state.get(k) not in opts:
            st.session_state[k] = "All"

    def reset_drill():
        st.session_state["drill_year"] = st.session_state["drill_quarter"] = st.session_state["drill_month"] = "All"
        st.session_state["level"] = "Month"

    d1, d2, d3, d4, d5 = st.columns([2.2, 1, 1, 1, 1])
    level = d1.segmented_control("Granularity", ["Year", "Quarter", "Month", "Day"], key="level") or "Month"
    year_sel = d2.selectbox("Year", ["All"] + [str(y) for y in years], key="drill_year")

    q_opts = ["All"]
    if year_sel != "All":
        q_opts += [f"Q{q}" for q in sorted(period_orders.loc[period_orders["year"] == int(year_sel), "quarter"].unique())]
    if st.session_state.get("drill_quarter") not in q_opts:
        st.session_state["drill_quarter"] = "All"
    q_sel = d3.selectbox("Quarter", q_opts, key="drill_quarter", disabled=year_sel == "All")

    mo_opts = ["All"]
    if q_sel != "All":
        sub = period_orders[(period_orders["year"] == int(year_sel)) & (period_orders["quarter"] == int(q_sel[1]))]
        mo_opts += [calendar.month_abbr[x] for x in sorted(sub["month"].unique())]
    if st.session_state.get("drill_month") not in mo_opts:
        st.session_state["drill_month"] = "All"
    mo_sel = d4.selectbox("Month", mo_opts, key="drill_month", disabled=q_sel == "All")
    d5.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
    d5.button("↩ Reset", on_click=reset_drill, width="stretch")

    view = period_orders
    crumbs = ["All periods in range"]
    if year_sel != "All":
        view = view[view["year"] == int(year_sel)]; crumbs.append(year_sel)
    if q_sel != "All":
        view = view[view["quarter"] == int(q_sel[1])]; crumbs.append(q_sel)
    if mo_sel != "All":
        view = view[view["month"] == list(calendar.month_abbr).index(mo_sel)]; crumbs.append(mo_sel)
    st.caption("📍 " + " › ".join(crumbs))

    if view.empty:
        st.info("No paid orders for this selection.")
    else:
        g = dd.trend(view, level)
        hover = "<b>%{x}</b><br>Revenue ₹%{y:,.0f}<br>Orders %{customdata[0]:,}<br>AOV ₹%{customdata[1]:,.0f}<extra></extra>"
        cd = np.c_[g["orders"], g["aov"]]
        fig = go.Figure()
        if level == "Year":
            x = g["period"].astype(str)
            fig.add_bar(x=x, y=g["revenue"], name="Revenue", marker_color=BLUE, customdata=cd, hovertemplate=hover,
                        text=[inr_short(v) for v in g["revenue"]], textposition="outside")
            fig.add_bar(x=x, y=g["profit"], name="Profit", marker_color=GREEN, hovertemplate="<b>%{x}</b><br>Profit ₹%{y:,.0f}<extra></extra>")
            fig.update_layout(barmode="group")
        else:
            x = g["period"].astype(str) if level == "Quarter" else g["period"]
            mode = "lines+markers" if level != "Day" else "lines"
            fig.add_trace(go.Scatter(x=x, y=g["revenue"], name="Revenue", mode=mode, fill="tozeroy", line=dict(color=BLUE, width=2.5),
                                     fillcolor="rgba(37,99,235,.18)", customdata=cd, hovertemplate=hover))
            fig.add_trace(go.Scatter(x=x, y=g["profit"], name="Gross profit", mode=mode, line=dict(color=GREEN, width=2),
                                     hovertemplate="<b>%{x}</b><br>Profit ₹%{y:,.0f}<extra></extra>"))
            if level == "Month":
                fig.update_xaxes(tickformat="%b %Y")
        fig.update_layout(height=370, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white", hovermode="x unified",
                          legend=dict(orientation="h", y=1.08, x=0), yaxis=dict(title="INR", tickformat=",.0f"))
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        v_rev, v_ord = view["revenue"].sum(), len(view)
        st.caption(f"**In view:** {len(g)} {level.lower()}{'s' if len(g) != 1 else ''} · revenue {inr_short(v_rev)} · {v_ord:,} orders · "
                   f"AOV {inr(v_rev / v_ord)} · margin {pct(view['profit'].sum() / v_rev)}")

with right, st.container(border=True):
    st.markdown("#### Regional heatmap")
    rt = dd.region_table(i0, i1, categories, methods)
    metric_opts = {"Revenue": ("revenue", inr_short, "Blues"), "Orders": ("orders", lambda v: f"{v:,.0f}", "Blues"),
                   "AOV": ("aov", inr, "Blues"), "Profit margin": ("margin", pct, "Greens"),
                   "New customers": ("new_customers", lambda v: f"{v:,.0f}", "Purples"), "CAC": ("cac", inr, "Oranges")}
    mname = st.selectbox("Map metric", list(metric_opts), key="map_metric")
    col, fmt, scale = metric_opts[mname]
    zt = rt.loc[ZONES].copy()
    zt["value"] = zt[col].where(zt.index.isin(regions))
    zt = zt.reset_index().rename(columns={"index": "zone"})
    zt["label"] = zt["value"].map(lambda v: "" if pd.isna(v) else fmt(v))
    fig = px.choropleth(zt, geojson=geo, locations="zone", featureidkey="properties.zone", color="value", color_continuous_scale=scale)
    fig.update_traces(marker_line_color="white", marker_line_width=1.2, hovertemplate="<b>%{location}</b><br>" + mname + ": %{customdata}<extra></extra>",
                      customdata=zt["label"])
    centers = {"North": (76.5, 29.5), "Central": (79.5, 24.0), "East": (86.5, 24.5), "West": (73.0, 20.5), "South": (77.8, 14.0)}
    fig.add_trace(go.Scattergeo(lon=[centers[z][0] for z in zt["zone"]], lat=[centers[z][1] for z in zt["zone"]],
                                text=[f"<b>{z}</b><br>{l}" if l else f"<b>{z}</b>" for z, l in zip(zt["zone"], zt["label"])],
                                mode="text", textfont=dict(size=11), hoverinfo="skip", showlegend=False))
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0), coloraxis_colorbar=dict(title="", thickness=12, len=.7))
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    unk = rt.loc["Unknown", col] if "Unknown" in regions else np.nan
    st.caption(f"Zones are sales regions (state groupings, see Definitions). Orders with an unknown region are not mapped"
               + ("." if pd.isna(unk) else f" ({mname.lower()}: {fmt(unk)})."))

st.write("")

# ---------------------------------------------------------------------------------------------- level 4: customer economics + category drill-down
a, b, c = st.columns(3)
x = win.index.to_timestamp()

with a, st.container(border=True):
    st.markdown("#### Acquisition: new customers & CAC")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=x, y=win["new_customers"], name="New customers", marker_color="rgba(37,99,235,.55)", secondary_y=False,
                hovertemplate="%{x|%b %Y}<br>New customers %{y:,}<extra></extra>")
    fig.add_trace(go.Scatter(x=x, y=win["cac"], name="CAC (₹)", mode="lines+markers", line=dict(color=ORANGE, width=2.5),
                             hovertemplate="%{x|%b %Y}<br>CAC ₹%{y:,.0f}<extra></extra>"), secondary_y=True)
    fig.update_yaxes(title_text="New customers", secondary_y=False); fig.update_yaxes(title_text="CAC (₹)", secondary_y=True, showgrid=False)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white", legend=dict(orientation="h", y=1.12, x=0), hovermode="x unified")
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    st.caption("CAC rises as new-customer volume falls: the spend base is partly fixed.")

with b, st.container(border=True):
    st.markdown("#### Customer health: active base & churn")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=x, y=win["active_customers"], name="Active customers", fill="tozeroy", mode="lines",
                             line=dict(color="rgba(22,163,74,.9)"), fillcolor="rgba(22,163,74,.18)",
                             hovertemplate="%{x|%b %Y}<br>Active %{y:,.0f}<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=x, y=win["churn_rate"], name="Churn rate", mode="lines+markers", line=dict(color=RED, width=2.5),
                             hovertemplate="%{x|%b %Y}<br>Churn %{y:.1%}<extra></extra>"), secondary_y=True)
    fig.update_yaxes(title_text="Active customers", secondary_y=False)
    fig.update_yaxes(title_text="Churn", tickformat=".0%", secondary_y=True, showgrid=False, rangemode="tozero")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white", legend=dict(orientation="h", y=1.12, x=0), hovermode="x unified")
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
    st.caption(f"Churn = last purchase now older than {CHURN_WINDOW_DAYS} days. Shown from Jul 2023 (first month with full history).")

with c, st.container(border=True):
    st.markdown("#### Category → product &nbsp; <small>(click a slice to drill in)</small>", unsafe_allow_html=True)
    if period_orders.empty:
        st.info("No paid orders for this selection.")
    else:
        pr = period_orders.groupby(["category", "product"]).agg(revenue=("revenue", "sum"), profit=("profit", "sum")).reset_index()
        pr["margin"] = pr["profit"] / pr["revenue"]
        fig = px.sunburst(pr, path=["category", "product"], values="revenue", color="margin", color_continuous_scale="RdYlGn",
                          range_color=[max(pr["margin"].min() - .02, 0), pr["margin"].max() + .02])
        fig.update_traces(hovertemplate="<b>%{label}</b><br>Revenue ₹%{value:,.0f}<br>Margin %{color:.1%}<extra></extra>", insidetextorientation="radial")
        fig.update_layout(height=340, margin=dict(l=0, r=0, t=10, b=0), coloraxis_colorbar=dict(title="Margin", tickformat=".0%", thickness=10, len=.8))
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        st.caption("Slice size = revenue, colour = profit margin (green = healthier).")

# ---------------------------------------------------------------------------------------------- level 5: detail tabs
st.write("")
tab1, tab2, tab3 = st.tabs(["🗓️ Seasonality heatmap", "🗺️ Region scorecard", "ℹ️ Definitions & data notes"])

with tab1:
    if period_orders.empty:
        st.info("No paid orders for this selection.")
    else:
        hm = period_orders.pivot_table(index="category", columns="month", values="revenue", aggfunc="sum").reindex(columns=range(1, 13))
        fig = go.Figure(go.Heatmap(z=hm.values / 1e5, x=[calendar.month_abbr[i] for i in hm.columns], y=hm.index, colorscale="YlOrRd",
                                   hovertemplate="%{y}<br>%{x}: ₹%{z:.1f} L<extra></extra>", colorbar=dict(title="₹ lakh")))
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), template="plotly_white")
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False})
        st.caption("Revenue by category and calendar month for the selected period and slicers (darker = more revenue).")

with tab2:
    show = rt.copy()
    show["is_selected"] = show.index.isin(regions)
    show = show[show["is_selected"]].drop(columns="is_selected")
    st.dataframe(show[["revenue", "orders", "aov", "margin", "new_customers", "spend", "cac"]].rename(columns={
        "revenue": "Revenue", "orders": "Paid orders", "aov": "AOV", "margin": "Profit margin", "new_customers": "New customers",
        "spend": "Marketing spend", "cac": "CAC"}),
        width="stretch", column_config={
            "Revenue": st.column_config.NumberColumn(format="₹%,.0f"), "Paid orders": st.column_config.NumberColumn(format="%,d"),
            "AOV": st.column_config.NumberColumn(format="₹%,.0f"), "Profit margin": st.column_config.NumberColumn(format="percent"),
            "New customers": st.column_config.NumberColumn(format="%,d"), "Marketing spend": st.column_config.NumberColumn(format="₹%,.0f"),
            "CAC": st.column_config.NumberColumn(format="₹%,.0f")})
    st.caption("Revenue-side columns follow all slicers; new customers, spend and CAC follow Period only (not category / payment method).")

with tab3:
    st.markdown(f"""
**KPI definitions**

| KPI | Definition |
|---|---|
| **Revenue** | Sum of order revenue (after discount) for **Paid** orders. Pending, Failed and Refunded orders are excluded. |
| **Average order value (AOV)** | Revenue / number of paid orders. |
| **Customer acquisition cost (CAC)** | Marketing spend / new customers in the period. A *new customer* is one whose first paid order falls in the period. |
| **Churn rate** | A customer is *active* if they paid for an order in the last {CHURN_WINDOW_DAYS} days. Monthly churn = share of customers active at the end of last month who are no longer active at the end of this month. The card shows the average monthly churn in the selected period. |
| **Gross profit / margin** | Revenue minus cost of goods (`cost_price x quantity`), as a share of revenue. Excludes shipping, fees and marketing. |

**Data notes (please read)**
- **The dataset is synthetic** (generated in Task 3). Patterns such as seasonality and category margins were built in.
- **Marketing spend is illustrative.** The orders data has no spend, so `marketing_spend.csv` was generated with a documented model
  (INR 450 per acquired customer + INR 30,000 per month always-on spend, +25% in Oct-Dec). Replace the file with real spend and CAC updates automatically.
- **New customers fall sharply over time** because the synthetic data draws buyers from a fixed pool of about 3,000 customer IDs. In real data this would signal
  that acquisition is drying up, so CAC would deserve urgent attention.
- **Regions are sales zones.** Zones are shown as groupings of Indian states: North (J&K, Ladakh, Himachal, Punjab, Haryana, Delhi, Chandigarh, Uttarakhand, Rajasthan),
  Central (UP, MP, Chhattisgarh), East (Bihar, Jharkhand, West Bengal, Odisha, North-East states, Andaman & Nicobar), West (Gujarat, Maharashtra, Goa, DNH&DD),
  South (AP, Telangana, Karnataka, Kerala, Tamil Nadu, Puducherry, Lakshadweep). A customer's region is the region of their first order.
  Boundary data: udit-001/india-maps-data (public GitHub), simplified.
- Orders with an unknown customer ID (about 3%) count in revenue but not in customer metrics.
""")
    kp = win.copy()
    kp.index = kp.index.astype(str)
    st.download_button("⬇️ Download monthly KPIs for this selection (CSV)", kp.round(4).to_csv().encode("utf-8"), "monthly_kpis.csv", "text/csv")
