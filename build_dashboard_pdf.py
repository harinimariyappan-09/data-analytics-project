"""
Builds Dashboard_Export.pdf - a 3-page static export of the dashboard (A4 landscape).
Uses the same KPI engine as app.py, so every number matches the live dashboard.

  Page 1  Executive overview (KPI cards, trend, regional heatmap, CAC, churn, categories)
  Page 2  Drill-down & detail (Year -> Quarter -> Month, seasonality heatmap, products, region scorecard)
  Page 3  KPI definitions, assumptions and data notes

Run: python build_dashboard_pdf.py
"""
import calendar
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import FancyBboxPatch, Polygon

from dashboard_metrics import CHURN_WINDOW_DAYS, REGIONS_ALL, ZONES, DashboardData, load_geojson, load_orders, load_spend

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
                     "axes.titlesize": 10, "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5})
NAVY, BLUE, GREEN, ORANGE, RED, GREY, INK, CARD = "#0F172A", "#2563EB", "#16A34A", "#F97316", "#DC2626", "#94A3B8", "#1E293B", "#F8FAFC"
W, H = 11.69, 8.27

dd = DashboardData(load_orders(), load_spend())
geo = load_geojson()
regions, cats, methods = REGIONS_ALL, dd.categories, dd.methods
m = dd.monthly(regions, cats, methods)
months = dd.months
I0, I1 = 24, 35                                  # cards: Jan-Dec 2025 vs Jan-Dec 2024
cur, prev, delta = dd.kpis_with_delta(m, I0, I1)
PERIOD_LABEL = f"{months[I0].strftime('%b %Y')} - {months[I1].strftime('%b %Y')}"


# ---------------------------------------------------------------------------------------------- helpers
def inr(x):
    return "n/a" if pd.isna(x) else f"₹{x:,.0f}"


def inr_short(x):
    if pd.isna(x): return "n/a"
    if abs(x) >= 1e7: return f"₹{x / 1e7:.2f} Cr"
    if abs(x) >= 1e5: return f"₹{x / 1e5:.1f} L"
    return f"₹{x:,.0f}"


def pct(x, d=1):
    return "n/a" if pd.isna(x) else f"{x * 100:.{d}f}%"


def header(fig, title, right):
    ax = fig.add_axes([0, 0.925, 1, 0.075]); ax.set_facecolor(NAVY); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values(): s.set_visible(False)
    ax.text(0.02, 0.5, title, color="white", fontsize=17, fontweight="bold", va="center", transform=ax.transAxes)
    ax.text(0.98, 0.5, right, color="#CBD5E1", fontsize=9, va="center", ha="right", transform=ax.transAxes)
    fig.text(0.02, 0.905, "Synthetic data  |  Marketing spend is illustrative  |  Revenue = Paid orders only", fontsize=7.5, color="#64748B")


def footer(fig, n):
    fig.text(0.02, 0.012, "Source: clean_dataset.csv (Task 3), marketing_spend.csv (illustrative), india_zones.geojson. Same KPI engine as the live Streamlit app.", fontsize=6.5, color="#94A3B8")
    fig.text(0.98, 0.012, f"Page {n} of 3", fontsize=6.5, color="#94A3B8", ha="right")


def card(fig, x, y, w, h, label, value, dtxt, dcolor, series=None, big=True):
    ax = fig.add_axes([x, y, w, h]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.005, 0.02), 0.99, 0.96, boxstyle="round,pad=0,rounding_size=0.05", fc=CARD, ec="#CBD5E1", lw=0.9))
    ax.text(0.06, 0.82 if big else 0.76, label.upper(), fontsize=7.5 if big else 6.8, fontweight="bold", color="#64748B", va="center")
    ax.text(0.06, 0.52 if big else 0.43, value, fontsize=21 if big else 14, fontweight="bold", color=INK, va="center")
    if dtxt:
        ax.text(0.06, 0.20 if big else 0.14, dtxt, fontsize=8 if big else 7, color=dcolor, va="center", fontweight="bold")
    if series is not None and len(series.dropna()) >= 2 and big:
        s = series.dropna().values
        sp = fig.add_axes([x + w * 0.58, y + h * 0.12, w * 0.37, h * 0.50]); sp.axis("off")
        sp.fill_between(range(len(s)), s, s.min() - (s.max() - s.min()) * 0.1, color=BLUE, alpha=0.15); sp.plot(s, color=BLUE, lw=1.5)


def dates(ax):
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))


def good_color(d, higher_good=True):
    if d is None or abs(d) < 5e-4: return "#64748B"
    return GREEN if (d > 0) == higher_good else RED


def rel(d):  return None if d is None else f"{d:+.1%}"
def pp(d):   return None if d is None else f"{round(d * 100, 1) + 0:+.1f} pp"


def draw_map(ax, values, fmt, cmap="Blues"):
    vals = [values.get(z, np.nan) for z in ZONES]
    norm = Normalize(vmin=np.nanmin(vals) * 0.6, vmax=np.nanmax(vals))
    cm = plt.get_cmap(cmap)
    for f in geo["features"]:
        z = f["id"]; g = f["geometry"]; polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for p in polys:
            ax.add_patch(Polygon(p[0], closed=True, fc=cm(norm(values[z])), ec="white", lw=1.0))
    centers = {"North": (76.5, 29.5), "Central": (79.5, 24.0), "East": (86.5, 24.5), "West": (73.0, 20.5), "South": (77.8, 14.0)}
    for z, (x, y) in centers.items():
        ax.text(x, y, f"{z}\n{fmt(values[z])}", ha="center", va="center", fontsize=6.8, fontweight="bold", color=INK,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.82))
    ax.set_xlim(67, 98.5); ax.set_ylim(6, 37.5); ax.set_aspect(1.12); ax.axis("off")
    return norm, cm


# ============================================================================================== PAGE 1
def page1():
    fig = plt.figure(figsize=(W, H), facecolor="white")
    header(fig, "Retail Executive Dashboard", f"KPI cards: {PERIOD_LABEL} vs previous 12 months   |   Trends: all 36 months   |   All regions & categories")

    cw, ch, gap = 0.232, 0.175, 0.0153
    w1 = m.iloc[I0:I1 + 1]
    cards = [("Revenue", inr_short(cur["revenue"]), (rel(delta["revenue"]) or "") + " vs 2024", good_color(delta["revenue"]), w1["revenue"]),
             ("Average order value", inr(cur["aov"]), (rel(delta["aov"]) or "") + " vs 2024", good_color(delta["aov"]), w1["aov"]),
             ("Customer acquisition cost", inr(cur["cac"]), (rel(delta["cac"]) or "") + " vs 2024", good_color(delta["cac"], False), w1["cac"]),
             ("Churn rate (monthly avg)", pct(cur["churn"]), (pp(delta["churn"]) or "") + " vs 2024", good_color(delta["churn"], False), w1["churn_rate"])]
    for i, (l, v, d, c, s) in enumerate(cards):
        card(fig, 0.02 + i * (cw + gap), 0.715, cw, ch, l, v, d, c, s)

    t = [("Paid orders", f"{cur['orders']:,.0f}", rel(delta["orders"]), good_color(delta["orders"])),
         ("Gross profit", inr_short(cur["profit"]), f"margin {pct(cur['margin'])} ({pp(delta['margin'])})", good_color(delta["margin"])),
         ("New customers", f"{cur['new_customers']:,.0f}", rel(delta["new_customers"]), good_color(delta["new_customers"])),
         (f"Active customers ({CHURN_WINDOW_DAYS}d)", f"{cur['active']:,.0f}", rel(delta["active"]), good_color(delta["active"]))]
    for i, (l, v, d, c) in enumerate(t):
        card(fig, 0.02 + i * (cw + gap), 0.635, cw, 0.065, l, v, d, c, big=False)

    # revenue & profit trend
    ax = fig.add_axes([0.05, 0.345, 0.50, 0.245])
    x = months.to_timestamp()
    ax.fill_between(x, m["revenue"] / 1e5, color=BLUE, alpha=0.18); ax.plot(x, m["revenue"] / 1e5, color=BLUE, lw=2, label="Revenue")
    ax.plot(x, m["profit"] / 1e5, color=GREEN, lw=1.8, label="Gross profit")
    for y in (2023, 2024, 2025): ax.axvspan(pd.Timestamp(f"{y}-10-01"), pd.Timestamp(f"{y}-12-31"), color=ORANGE, alpha=0.10)
    ax.set_title("Monthly revenue & gross profit (INR lakh), Q4 shaded", loc="left"); ax.set_ylabel("INR lakh"); ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=2)
    ax.grid(axis="y", alpha=0.25); dates(ax)

    # regional heatmap
    rt = dd.region_table(I0, I1, cats, methods)
    ax = fig.add_axes([0.60, 0.295, 0.38, 0.315])
    vals = rt.loc[ZONES, "revenue"].to_dict()
    norm, cm = draw_map(ax, vals, inr_short)
    fig.text(0.60, 0.618, f"Regional heatmap: revenue, {months[I0].strftime('%b %Y')} - {months[I1].strftime('%b %Y')}", fontsize=10, fontweight="bold")

    # CAC & new customers
    ax = fig.add_axes([0.06, 0.075, 0.235, 0.195]); ax2 = ax.twinx(); dates(ax)
    ax.bar(x, m["new_customers"], width=22, color=BLUE, alpha=0.45); ax2.plot(x, m["cac"], color=ORANGE, lw=2.2)
    ax2.spines["right"].set_visible(True); ax.set_title("New customers & CAC", loc="left")
    ax.set_ylabel("New customers"); ax2.set_ylabel("CAC (INR)", color=ORANGE); ax.grid(axis="y", alpha=0.2)

    # active & churn
    ax = fig.add_axes([0.39, 0.075, 0.235, 0.195]); ax2 = ax.twinx(); dates(ax)
    ax.fill_between(x, m["active_customers"], color=GREEN, alpha=0.18); ax.plot(x, m["active_customers"], color=GREEN, lw=1.6)
    ax2.plot(x, m["churn_rate"] * 100, color=RED, lw=2.2); ax2.set_ylim(0, 25); ax2.spines["right"].set_visible(True)
    ax.set_title("Active customers & churn %", loc="left"); ax.set_ylabel("Active customers"); ax2.set_ylabel("Churn %", color=RED)
    ax.grid(axis="y", alpha=0.2)

    # categories
    p = dd.paid_filtered(regions, cats, methods); p = p[(p["ym"] >= months[I0]) & (p["ym"] <= months[I1])]
    cg = p.groupby("category").agg(rev=("revenue", "sum"), profit=("profit", "sum")).sort_values("rev")
    ax = fig.add_axes([0.80, 0.075, 0.17, 0.195])
    bars = ax.barh(cg.index, cg["rev"] / 1e5, color=BLUE, alpha=0.8)
    for b_, (rev, prof) in zip(bars, zip(cg["rev"], cg["profit"])):
        ax.text(b_.get_width() + 0.5, b_.get_y() + b_.get_height() / 2, f"{rev / 1e5:.0f} L | {prof / rev * 100:.0f}%", va="center", fontsize=6.8)
    ax.set_xlim(0, (cg["rev"] / 1e5).max() * 2.1); ax.set_title("Revenue & margin by category", loc="left", x=-0.55); ax.set_xlabel("INR lakh")
    footer(fig, 1)
    return fig


# ============================================================================================== PAGE 2
def page2():
    fig = plt.figure(figsize=(W, H), facecolor="white")
    header(fig, "Drill-down & Detail", "Temporal drill: Year -> Quarter -> Month   |   Categorical drill: Category -> Product")
    p = dd.paid_filtered(regions, cats, methods)

    # drill chain
    yr = dd.trend(p, "Year")
    ax = fig.add_axes([0.05, 0.60, 0.22, 0.24])
    b_ = ax.bar(yr["period"].astype(str), yr["revenue"] / 1e5, color=[GREY, GREY, BLUE])
    for r_, v in zip(b_, yr["revenue"]): ax.text(r_.get_x() + r_.get_width() / 2, v / 1e5 + 5, inr_short(v), ha="center", fontsize=8)
    ax.set_title("1  Year", loc="left"); ax.set_ylabel("INR lakh"); ax.set_ylim(0, yr["revenue"].max() / 1e5 * 1.18)
    p25 = p[p["year"] == 2025]
    q = dd.trend(p25, "Quarter")
    ax = fig.add_axes([0.37, 0.60, 0.22, 0.24])
    b_ = ax.bar([s[-2:] for s in q["period"]], q["revenue"] / 1e5, color=[GREY, GREY, GREY, BLUE])
    for r_, v in zip(b_, q["revenue"]): ax.text(r_.get_x() + r_.get_width() / 2, v / 1e5 + 2, inr_short(v), ha="center", fontsize=8)
    ax.set_title("2  Drill into 2025: quarters", loc="left"); ax.set_ylim(0, q["revenue"].max() / 1e5 * 1.18)
    mo = dd.trend(p25[p25["quarter"] == 4], "Month")
    ax = fig.add_axes([0.69, 0.60, 0.28, 0.24])
    b_ = ax.bar([calendar.month_abbr[t.month] for t in mo["period"]], mo["revenue"] / 1e5, color=BLUE)
    for r_, v in zip(b_, mo["revenue"]): ax.text(r_.get_x() + r_.get_width() / 2, v / 1e5 + 0.5, inr_short(v), ha="center", fontsize=8)
    ax.set_title("3  Drill into Q4 2025: months (next level: days)", loc="left"); ax.set_ylim(0, mo["revenue"].max() / 1e5 * 1.18)
    for xa in (0.295, 0.615):
        fig.text(xa, 0.715, "▶", fontsize=20, color=ORANGE, ha="center")

    # seasonality heatmap
    ax = fig.add_axes([0.14, 0.33, 0.40, 0.20])
    hm = p.pivot_table(index="category", columns="month", values="revenue", aggfunc="sum").reindex(columns=range(1, 13)) / 1e5
    im = ax.imshow(hm.values, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(12)); ax.set_xticklabels([calendar.month_abbr[i] for i in range(1, 13)]); ax.set_yticks(range(len(hm))); ax.set_yticklabels(hm.index)
    for i in range(hm.shape[0]):
        for j in range(hm.shape[1]):
            ax.text(j, i, f"{hm.values[i, j]:.0f}", ha="center", va="center", fontsize=6.8, color="white" if hm.values[i, j] > hm.values.max() * 0.6 else INK)
    ax.set_title("Revenue by category x month (INR lakh, 2023-25)", loc="left", fontsize=9.5)
    for s in ax.spines.values(): s.set_visible(False)

    # top products
    pr = p.groupby(["category", "product"]).agg(rev=("revenue", "sum"), profit=("profit", "sum")).reset_index()
    pr["margin"] = pr["profit"] / pr["rev"]; pr = pr.nlargest(10, "rev").sort_values("rev")
    ax = fig.add_axes([0.70, 0.33, 0.27, 0.20])
    norm = Normalize(0.15, 0.55); cm = plt.get_cmap("RdYlGn")
    ax.barh(pr["product"], pr["rev"] / 1e5, color=[cm(norm(v)) for v in pr["margin"]])
    for i, (r_, mg) in enumerate(zip(pr["rev"], pr["margin"])): ax.text(r_ / 1e5 + 1, i, f"{mg * 100:.0f}%", va="center", fontsize=6.8)
    ax.set_title("Top 10 products (label = margin)", loc="left", fontsize=9.5); ax.set_xlabel("INR lakh")
    ax.set_xlim(0, pr["rev"].max() / 1e5 * 1.15)

    # region scorecard
    rt = dd.region_table(0, 35, cats, methods)
    ax = fig.add_axes([0.04, 0.06, 0.92, 0.19]); ax.axis("off")
    ax.set_title("Region scorecard, all 36 months", loc="left", fontsize=10)
    rows = [[r, inr_short(rt.loc[r, "revenue"]), f"{rt.loc[r, 'orders']:,.0f}", inr(rt.loc[r, "aov"]), pct(rt.loc[r, "margin"]),
             f"{rt.loc[r, 'new_customers']:,.0f}", inr_short(rt.loc[r, "spend"]), inr(rt.loc[r, "cac"])] for r in REGIONS_ALL]
    tot = dd.summarize(m, 0, 35)
    rows.append(["Total", inr_short(tot["revenue"]), f"{tot['orders']:,.0f}", inr(tot["aov"]), pct(tot["margin"]), f"{tot['new_customers']:,.0f}", inr_short(tot["spend"]), inr(tot["cac"])])
    tb = ax.table(cellText=rows, colLabels=["Region", "Revenue", "Paid orders", "AOV", "Profit margin", "New customers", "Marketing spend*", "CAC*"],
                  loc="upper center", cellLoc="center", colLoc="center")
    tb.auto_set_font_size(False); tb.set_fontsize(8); tb.scale(1, 1.12)
    for (r_, c_), cell in tb.get_celld().items():
        cell.set_edgecolor("#E2E8F0")
        if r_ == 0: cell.set_facecolor(NAVY); cell.set_text_props(color="white", fontweight="bold")
        elif r_ == len(rows): cell.set_facecolor("#E2E8F0"); cell.set_text_props(fontweight="bold")
        elif r_ % 2 == 0: cell.set_facecolor(CARD)
    fig.text(0.04, 0.045, "* Illustrative marketing spend (see page 3).", fontsize=7, color="#64748B")
    footer(fig, 2)
    return fig


# ============================================================================================== PAGE 3
def page3():
    fig = plt.figure(figsize=(W, H), facecolor="white")
    header(fig, "KPI Definitions, Assumptions & Data Notes", "Read before using the numbers")
    ax = fig.add_axes([0.04, 0.50, 0.92, 0.34]); ax.axis("off")
    rows = [["Revenue", "Sum of order revenue (after discount), Paid orders only", "Order", "Head of Growth", "Daily"],
            ["Average order value", "Revenue / number of paid orders", "Order", "Growth Analyst", "Daily"],
            ["Customer acquisition cost", "Marketing spend / new customers (first paid order in period)", "Customer", "Marketing Lead", "Monthly"],
            ["Churn rate (monthly)", f"Active last month but now inactive ({CHURN_WINDOW_DAYS} days no purchase) / active last month", "Customer", "Customer Success Lead", "Monthly"],
            ["Gross profit & margin", "Revenue - (cost_price x quantity); margin = profit / revenue", "Order", "Finance Controller", "Daily"],
            ["New customers", "Customers whose first paid order falls in the period", "Customer", "Marketing Lead", "Monthly"],
            ["Active customers", f"Customers with a paid order in the trailing {CHURN_WINDOW_DAYS} days (month end)", "Customer", "Customer Success Lead", "Monthly"],
            ["Paid orders", "Count of orders with payment status Paid", "Order", "Retail Operations", "Daily"]]
    tb = ax.table(cellText=rows, colLabels=["KPI", "Definition / formula", "Grain", "Owner (proposed)", "Refresh"], colWidths=[0.17, 0.50, 0.08, 0.18, 0.07],
                  loc="upper center", cellLoc="left", colLoc="left")
    tb.auto_set_font_size(False); tb.set_fontsize(7.6); tb.scale(1, 1.6)
    for (r_, c_), cell in tb.get_celld().items():
        cell.set_edgecolor("#E2E8F0")
        if r_ == 0: cell.set_facecolor(NAVY); cell.set_text_props(color="white", fontweight="bold")
        elif r_ % 2 == 0: cell.set_facecolor(CARD)
    fig.text(0.04, 0.868, "KPI dictionary (see Task 2 for the full dictionary and data-quality contract)", fontsize=10, fontweight="bold")

    notes = [
        ("Dashboard design (visual hierarchy)",
         "1) Four headline KPIs with trend sparklines and change vs the previous period at the top; 2) four supporting KPIs as compact tiles; 3) the trend and the regional heatmap as the main analysis; "
         "4) customer economics (acquisition, churn) and the category mix below; 5) detail views (seasonality, products, scorecard) last. Colour is used sparingly: blue = revenue, green = profit/health, "
         "orange = cost, red = risk."),
        ("Interactivity in the live app",
         "Slicers: period range, quick ranges, region, category, payment method. Drill-down: Year -> Quarter -> Month -> Day on the trend chart; Category -> Product on the sunburst; map metric selector. "
         "This PDF is a static export of the default view and of one drill path (2025 -> Q4 -> months)."),
        ("Data limitations",
         "The dataset is synthetic. Marketing spend does not exist in the order data: marketing_spend.csv was generated (INR 450 per acquired customer + INR 30,000 per month always-on spend, +25% in Oct-Dec), "
         "so CAC is illustrative and should be replaced by real spend. New customers decline sharply over time because the data draws buyers from a fixed pool of ~3,000 customer IDs; in real data this would be a serious "
         "warning about acquisition. Churn needs 180 days of history, so it starts in Jul 2023."),
        ("Regions",
         "Regions in the data are sales zones, drawn here as groupings of Indian states (North, Central, East, West, South). Orders with an unknown region (~4%) are excluded from the map. A customer's region is the region of their first order. "
         "Boundaries: udit-001/india-maps-data (public), dissolved to zones and simplified."),
    ]
    y = 0.462
    for title, body in notes:
        fig.text(0.04, y, title, fontsize=9.5, fontweight="bold", color=INK)
        import textwrap
        wrapped = "\n".join(textwrap.wrap(body, 190))
        fig.text(0.04, y - 0.018, wrapped, fontsize=7.6, color="#334155", va="top", linespacing=1.5)
        y -= 0.018 + 0.0215 * (wrapped.count("\n") + 1) + 0.03
    footer(fig, 3)
    return fig


if __name__ == "__main__":
    with PdfPages("Dashboard_Export.pdf") as pdf:
        for f in (page1(), page2(), page3()):
            pdf.savefig(f)
            plt.close(f)
        info = pdf.infodict(); info["Title"] = "Retail Executive Dashboard - PDF export"; info["Author"] = "Data Analytics Project"
    print("saved Dashboard_Export.pdf")
