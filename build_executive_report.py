"""Builds Executive_Decision_Report.pdf (13 slides, 16:9) from the same data/KPI engine as the dashboard. Run from the repo root."""
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

from dashboard_metrics import REGIONS_ALL, DashboardData, load_orders, load_spend

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold"})
NAVY, BLUE, GREEN, ORANGE, RED, GREY, INK = "#0F172A", "#2563EB", "#16A34A", "#F97316", "#DC2626", "#94A3B8", "#1E293B"
dd = DashboardData(load_orders(), load_spend())
m = dd.monthly(REGIONS_ALL, dd.categories, dd.methods)
cur, prev, d = dd.kpis_with_delta(m, 24, 35)
P = dd.paid[dd.paid["year"] == 2025]
L = lambda v: f"Rs {v / 1e5:,.1f} L"
L2 = lambda v: f"Rs {v / 1e5:,.2f} L"

# ------------------------------------------------------------------ ROI model (2025 base year, annualised, all inputs shown on slide 10)
el = P[(P.category == "Electronics") & (P.discount_pct > 15)]
r1 = 0.85 * (el.gross_amount * (el.discount_pct - 15) / 100).sum() - 0.15 * el.profit.sum()      # cap at 15%, lose 15% of those orders
q4 = P[P.quarter == 4]; r2 = 0.08 * q4.revenue.sum() * (P.profit.sum() / P.revenue.sum())          # +8% Q4 revenue at 2025 margin
nonpaid = dd.orders[(dd.orders.year == 2025) & (~dd.orders.counts_as_revenue)].revenue.sum()
r3 = 0.15 * nonpaid * (P.profit.sum() / P.revenue.sum())                                           # recover 15% of non-paid value at 2025 margin
cost = {"R1": 0.1e5, "R2": 0.4e5, "R3": 0.6e5}      # internal-effort planning assumptions sized to a Rs 1 Cr business; Finance to confirm
gain = {"R1": r1, "R2": r2, "R3": r3}
tot_g, tot_c = sum(gain.values()), sum(cost.values())
print({k: round(v) for k, v in gain.items()}, round(tot_g), round(nonpaid), len(el))


def slide(title, kicker=None, n=[0]):
    n[0] += 1
    f = plt.figure(figsize=(13.33, 7.5), facecolor="white")
    f.add_artist(plt.Rectangle((0, 0.93), 1, 0.07, transform=f.transFigure, color=NAVY))
    f.text(0.04, 0.965, title, color="white", fontsize=20, fontweight="bold", va="center")
    if kicker: f.text(0.04, 0.885, kicker, fontsize=13, color=BLUE, fontweight="bold")
    f.text(0.04, 0.02, "Retail Analytics Capstone | Executive Decision Report | Data: Jan 2023 - Dec 2025 (synthetic)", fontsize=8, color=GREY)
    f.text(0.96, 0.02, f"{n[0] + 1}", fontsize=9, color=GREY, ha="right")
    return f


def text(f, x, y, s, size=12, color=INK, w=70, bold=False, gap=1.45):
    f.text(x, y, "\n".join(textwrap.wrap(s, w)), fontsize=size, color=color, va="top", linespacing=gap, fontweight="bold" if bold else "normal")


def bullets(f, x, y, items, size=12.5, w=62, step=0.085):
    for it in items:
        lines = textwrap.wrap(it, w)
        f.text(x, y, "\u2022", fontsize=size, color=BLUE, va="top")
        f.text(x + 0.016, y, "\n".join(lines), fontsize=size, va="top", color=INK, linespacing=1.4)
        y -= step * max(1, len(lines) * 0.62 + 0.38)


def card(f, x, y, w, h, head, body, color=BLUE, bsize=10.5, bw=34):
    ax = f.add_axes([x, y, w, h]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0.01, 0.01), 0.98, 0.98, boxstyle="round,pad=0,rounding_size=0.04", fc="#F8FAFC", ec="#CBD5E1"))
    ax.add_patch(plt.Rectangle((0.01, 0.9), 0.98, 0.09, color=color))
    ax.text(0.05, 0.945, head, color="white", fontsize=12, fontweight="bold", va="center")
    ax.text(0.05, 0.82, "\n".join("\n".join(textwrap.wrap(p, bw)) if p else "" for p in body.split("\n")), fontsize=bsize, va="top", color=INK, linespacing=1.45)


def kpi(f, x, y, label, val, sub, col):
    ax = f.add_axes([x, y, 0.21, 0.17]); ax.axis("off"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0.01, 0.02), 0.98, 0.96, boxstyle="round,pad=0,rounding_size=0.05", fc="#F8FAFC", ec="#CBD5E1"))
    ax.text(0.07, 0.8, label.upper(), fontsize=9, color="#64748B", fontweight="bold"); ax.text(0.07, 0.45, val, fontsize=24, fontweight="bold", color=INK)
    ax.text(0.07, 0.14, sub, fontsize=10, color=col, fontweight="bold")


pages = []

# 1 title
f = plt.figure(figsize=(13.33, 7.5), facecolor=NAVY)
f.text(0.07, 0.62, "Protecting Margin, Capturing Q4,\nClosing Revenue Leaks", color="white", fontsize=38, fontweight="bold", va="center", linespacing=1.25)
f.text(0.07, 0.40, "Executive Decision Report: three strategic recommendations from the retail analytics programme", color="#CBD5E1", fontsize=16)
f.text(0.07, 0.22, "Prepared for the Executive Committee  |  October 2026\nBased on 3 years of order data (Jan 2023 - Dec 2025). Dataset is synthetic; marketing spend is illustrative.", color=GREY, fontsize=12, linespacing=1.6)
f.add_artist(plt.Rectangle((0.07, 0.31), 0.12, 0.006, transform=f.transFigure, color=ORANGE))
pages.append(f)

# 2 executive summary
f = slide("Executive summary", "We grow profit fastest by fixing how we discount and sell, not by selling more everywhere")
bullets(f, 0.04, 0.82, [
    "Business is stable, not growing fast: 2025 revenue Rs 1.08 Cr (+2.8%), profit Rs 35.5 L at a 32.9% margin.",
    "Q4 is the engine: October-December earns 44% more per month than the rest of the year, in all three years.",
    "Electronics is our biggest category (32% of revenue) but earns only 22.6% of profit. Beauty and Fashion earn more profit per rupee.",
    "Discounts cost margin (38.5% down to 21.6%) and showed no effect on basket size or repeat purchase. All 27 loss-making orders are deep-discounted Electronics.",
    "Only 81% of orders become revenue: refunds, pending and failed payments hold about Rs 70 L (17.6%) of order value.",
], w=70)
card(f, 0.60, 0.40, 0.36, 0.44, "Decisions we ask for", "1. Approve discount guardrails\n2. Approve a profit-weighted Q4 growth plan\n3. Approve a payment and refund leakage programme", ORANGE, 12.5, 34)
card(f, 0.60, 0.10, 0.36, 0.25, "Combined impact (base case)", f"About {L(tot_g)} extra annual profit for {L(tot_c)} investment (ROI {((tot_g - tot_c) / tot_c):.0%}), payback in about {12 * tot_c / tot_g:.0f} months. Low case roughly breaks even.", GREEN, 11.5, 36)
pages.append(f)

# 3 methodology
f = slide("Approach and methodology", "Four analytical stages, every number traceable to a notebook or the live dashboard")
steps = [("1  Define & protect", "KPI dictionary (10 KPIs) and a data-quality contract with 18 checks, thresholds and escalation."),
         ("2  Clean", "12,420 raw rows to 11,822 trusted orders: duplicates, 5 date formats, currency text, impossible values fixed and flagged."),
         ("3  Analyse", "EDA with distributions, correlations and outlier review; 3 hypothesis tests with effect sizes and confidence intervals."),
         ("4  Monitor", "Interactive dashboard: slicers, drill-down, regional map, same KPI engine as this report.")]
for i, (h, b) in enumerate(steps):
    card(f, 0.04 + i * 0.235, 0.46, 0.22, 0.34, h, b, [BLUE, BLUE, BLUE, GREEN][i], 10.5, 25)
bullets(f, 0.04, 0.38, ["Revenue = Paid orders only; profit = revenue minus cost of goods (excludes shipping, fees and marketing).",
                        "Seasonality tested on 36 monthly totals (Welch t-test and Mann-Whitney); category margins with Kruskal-Wallis and Tukey; retention with a chi-square cohort test.",
                        "Limits: synthetic data, illustrative marketing spend, observational (not experimental) evidence."], size=11.5, w=105, step=0.07)
pages.append(f)

# 4 snapshot
f = slide("2025 performance snapshot", "Revenue and margin are healthy; acquisition economics are the weak spot")
rel = lambda v: f"{v:+.1%} vs 2024"
kp = [("Revenue", "Rs 1.08 Cr", rel(d["revenue"]), GREEN), ("Average order value", f"Rs {cur['aov']:,.0f}", rel(d["aov"]), GREEN),
      ("Acquisition cost (illustr.)", f"Rs {cur['cac']:,.0f}", rel(d["cac"]), RED), ("Monthly churn", f"{cur['churn']:.1%}", "flat vs 2024", "#64748B")]
for i, k in enumerate(kp): kpi(f, 0.04 + i * 0.235, 0.66, *k)
kp2 = [("Paid orders", f"{cur['orders']:,.0f}", rel(d["orders"]), RED), ("Gross profit", L(cur["profit"]), f"margin {cur['margin']:.1%}", GREEN),
       ("New customers", f"{cur['new_customers']:,.0f}", rel(d["new_customers"]), RED), ("Active customers", f"{cur['active']:,.0f}", rel(d["active"]), GREEN)]
for i, k in enumerate(kp2): kpi(f, 0.04 + i * 0.235, 0.46, *k)
bullets(f, 0.04, 0.38, ["Revenue grew 2.8% on a 4.2% higher order value while order count slipped 1.3%: growth comes from basket value, not volume.",
                        "New customers fell 66% and CAC doubled: the business increasingly lives off its existing customer base (about 1,300 active).",
                        "Churn is steady at about 12.5% a month, so the base holds only while repeat buying holds."], size=12, w=110, step=0.075)
pages.append(f)

# 5 driver 1 seasonality
f = slide("Revenue driver 1: Q4 is the peak season", "October-December earns 44% more per month, every year")
ax = f.add_axes([0.06, 0.12, 0.52, 0.66])
pm = dd.paid.groupby(["year", "month"]).revenue.sum().unstack(0) / 1e5
for y, c in zip(pm.columns, [GREY, "#64748B", BLUE]): ax.plot(pm.index, pm[y], marker="o", lw=2.5 if y == 2025 else 1.8, color=c, label=str(y))
ax.axvspan(9.5, 12.5, color=ORANGE, alpha=.12); ax.set_xticks(range(1, 13)); ax.set_xticklabels(list("JFMAMJJASOND")); ax.set_ylabel("Paid revenue, Rs lakh"); ax.legend(frameon=False)
ax.set_title("Monthly paid revenue by year (Q4 shaded)", loc="left")
bullets(f, 0.63, 0.80, ["Q4 months average Rs 11.7 L versus Rs 8.1 L in Jan-Sep: +44% (95% CI +32% to +55%, p < 0.0001).",
                        "The uplift holds in each year: +45% (2023), +37% (2024), +49% (2025). It is a stable seasonal pattern.",
                        "Every category peaks in Nov-Dec, so Q4 lifts the whole business.",
                        "So what: stock, logistics, support and ad budget must be ready by August."], size=12, w=44)
pages.append(f)

# 6 driver 2 category mix
f = slide("Revenue driver 2: category mix decides profit", "Revenue rank is not profit rank")
cg = P.groupby("category").agg(r=("revenue", "sum"), p=("profit", "sum"))
cg = cg.assign(rs=cg.r / cg.r.sum() * 100, ps=cg.p / cg.p.sum() * 100, mg=cg.p / cg.r * 100).sort_values("r", ascending=False)
ax = f.add_axes([0.06, 0.12, 0.55, 0.66]); x = np.arange(len(cg)); w = 0.38
ax.bar(x - w / 2, cg.rs, w, color=BLUE, label="Share of revenue %"); ax.bar(x + w / 2, cg.ps, w, color=GREEN, label="Share of profit %")
for i, (a, b, c) in enumerate(zip(cg.rs, cg.ps, cg.mg)): ax.text(i, max(a, b) + 1.2, f"margin {c:.0f}%", ha="center", fontsize=10, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels([c.replace(" & ", " &\n") for c in cg.index]); ax.legend(frameon=False); ax.set_ylim(0, 40); ax.set_title("2025: revenue share vs profit share", loc="left")
bullets(f, 0.65, 0.80, ["Electronics: 32% of revenue, only 22.6% of profit (23% margin).", "Beauty: 10% of revenue but 14.6% of profit (47% margin).",
                        "Category explains about 68% of the variation in margin; all ten category pairs differ significantly.",
                        "So what: judge categories by profit contribution and steer growth spend to Beauty, Fashion and Home & Kitchen."], size=12, w=38)
pages.append(f)

# 7 risk 1 discounting
f = slide("Risk 1: discounting destroys margin without buying growth", "Deeper discount, lower margin, same basket size")
bands = pd.cut(dd.paid.discount_pct, [-1, 0, 5, 10, 15, 25], labels=["0%", "1-5%", "6-10%", "11-15%", "16-25%"])
mb = dd.paid.groupby(bands, observed=True).profit_margin_pct.mean(); em = dd.paid[dd.paid.category == "Electronics"].groupby(bands[dd.paid.category == "Electronics"], observed=True).profit_margin_pct.mean()
ax = f.add_axes([0.06, 0.12, 0.52, 0.66]); ax.plot(mb.index, mb.values, marker="o", lw=3, color=BLUE, label="All categories"); ax.plot(em.index, em.values, marker="o", lw=3, color=RED, label="Electronics")
for i, v in enumerate(mb): ax.text(i, v + 1.5, f"{v:.1f}%", ha="center", fontsize=9, color=BLUE)
for i, v in enumerate(em): ax.text(i, v - 3.2, f"{v:.1f}%", ha="center", fontsize=9, color=RED)
ax.set_ylim(0, 45); ax.set_ylabel("Average profit margin %"); ax.set_xlabel("Discount band"); ax.legend(frameon=False); ax.set_title("Margin by discount level (paid orders)", loc="left")
bullets(f, 0.63, 0.80, ["Margin falls from 38.5% (no discount) to 21.6% at 16-25% off.", "Discount has no link to basket size (correlation 0.01) and no effect on 180-day repeat purchase (47.6% vs 47.5%, p = 0.96).",
                        "All 27 loss-making orders are Electronics at 20-25% off. Electronics cost is about 72% of list price.", "So what: guardrails first, then test any new discount before scaling."], size=12, w=44)
pages.append(f)

# 8 risk 2 acquisition + leakage
f = slide("Risk 2: weaker acquisition and leaking revenue", "Illustrative CAC is up 5x since 2023 and nearly 1 in 5 orders never becomes revenue")
ax = f.add_axes([0.07, 0.14, 0.33, 0.60]); ax2 = ax.twinx(); x = m.index.to_timestamp()
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7])); ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
ax.bar(x, m.new_customers, width=22, color=BLUE, alpha=.45); ax2.plot(x, m.cac, color=ORANGE, lw=2.5); ax2.spines["right"].set_visible(True)
ax.set_ylabel("New customers / month"); ax2.set_ylabel("CAC, Rs (illustrative)", color=ORANGE); ax.set_title("New customers and CAC", loc="left")
st = dd.orders.groupby("payment_status").revenue.sum().reindex(["Paid", "Refunded", "Pending", "Failed", "Unknown"]).fillna(0)
ax = f.add_axes([0.50, 0.20, 0.12, 0.54]); b = 0
for (k, v), c in zip(st.items(), [GREEN, RED, ORANGE, "#7F1D1D", GREY]):
    ax.bar(0, v / 1e5, bottom=b, color=c, width=.6, label=f"{k} {v / st.sum():.1%}"); b += v / 1e5
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.04), frameon=False, fontsize=9)
ax.set_xlim(-.4, 0.4); ax.set_xticks([]); ax.set_ylabel("Order value, Rs lakh"); ax.set_title("Where order value ends up", loc="left", fontsize=10)
bullets(f, 0.70, 0.80, ["New customers fell from 226 a month (Jan 2023) to 15 (Dec 2025). CAC rose from Rs 569 to Rs 3,014.", "Refunded, pending and failed orders hold about Rs 70 L, 17.6% of order value; refund rates are similar across categories (6.4-7.6%), so the cause is process, not product.",
                        "Caveat: spend is illustrative; the customer pool in the data is fixed."], size=11, w=36, step=0.095)
pages.append(f)

# 9 recommendations
f = slide("Three strategic recommendations", "Protect margin, capture the peak, close the leaks")
recs = [("1  Discount guardrails", "Cap Electronics discounts at 15% and add a margin check at promotion setup. Run a controlled test of first-order discounts before any scale-up.", "Evidence: margin 38.5% to 21.6%; 27 loss-making orders; no retention effect.", BLUE),
        ("2  Profit-weighted Q4 plan", "Pre-build stock and ad budget by August; weight Q4 spend to Beauty, Fashion and Home & Kitchen; track Electronics on margin, not sales.", "Evidence: Q4 +44% every year; category margin gap of 24 points.", GREEN),
        ("3  Leakage programme", "Reduce failed payments (retries, UPI-first checkout), pending-order follow-up and refund causes (product content, delivery); report a weekly paid-conversion KPI.", "Evidence: 81% of orders paid; Rs 70 L of order value not realised.", ORANGE)]
for i, (h, b, e, c) in enumerate(recs):
    card(f, 0.04 + i * 0.32, 0.20, 0.30, 0.62, h, b + "\n\n" + e, c, 12.5, 28)
pages.append(f)

# 10 ROI
f = slide("ROI projections", f"Base case: {L(tot_g)} extra profit a year for {L(tot_c)} of effort; the low case roughly breaks even")
rows = []
for k, nm in zip(["R1", "R2", "R3"], ["1 Discount guardrails", "2 Profit-weighted Q4 plan", "3 Leakage programme"]):
    g, c = gain[k], cost[k]; rows.append([nm, L2(c), L2(0.5 * g), L2(g), L2(1.5 * g), f"{(g - c) / c:.0%}", f"{12 * c / g:.1f} mo", f"{c / g:.0%}"])
rows.append(["Total", L2(tot_c), L2(0.5 * tot_g), L2(tot_g), L2(1.5 * tot_g), f"{(tot_g - tot_c) / tot_c:.0%}", f"{12 * tot_c / tot_g:.1f} mo", f"{tot_c / tot_g:.0%}"])
ax = f.add_axes([0.04, 0.50, 0.92, 0.32]); ax.axis("off")
tb = ax.table(cellText=rows, colLabels=["Recommendation", "Investment", "Annual profit: low", "Base", "High", "ROI (base)", "Payback", "Break-even (% of base)"], colWidths=[0.22, 0.09, 0.13, 0.09, 0.09, 0.1, 0.09, 0.16], loc="upper center", cellLoc="center")
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 2.0)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor("#E2E8F0")
    if r == 0: cell.set_facecolor(NAVY); cell.set_text_props(color="white", fontweight="bold")
    elif r == len(rows): cell.set_facecolor("#E2E8F0"); cell.set_text_props(fontweight="bold")
bullets(f, 0.04, 0.44, [f"R1: cap Electronics discounts at 15%; {len(el)} orders affected in 2025; assume 15% of them are lost. R2: +8% Q4 revenue at the 2025 margin (32.9%). R3: recover 15% of the Rs {nonpaid / 1e5:,.0f} L non-paid value at the 2025 margin.",
                        "Low and high cases scale benefits by 0.5x and 1.5x; investment is held fixed. Investment figures are internal-effort planning assumptions for a business of this size (rule configuration, planning and creative re-weighting with no extra media, payment-flow tuning), to be confirmed by Finance. Extra media spend would need to beat roughly 3x return to pay back at a 33% margin.",
                        "Base year is 2025 data; benefits are annual and not discounted. Upside excluded: any first-order discount savings (pending the test)."], size=11, w=125, step=0.065)
pages.append(f)

# 11 timeline
f = slide("Implementation timeline", "Quick wins first; full Q4 2027 plan in place by September 2027")
ax = f.add_axes([0.24, 0.19, 0.72, 0.59]); mo = pd.period_range("2026-11", "2027-12", freq="M")
tasks = [("R1  Discount rules live", 0, 2, BLUE), ("R1  First-order discount A/B test", 2, 6, BLUE), ("R2  Q4 2026 readiness sprint", 0, 2, GREEN), ("R2  Q4 2027 plan: stock & budget", 5, 10, GREEN),
         ("R2  Q4 2027 execution", 11, 14, GREEN), ("R3  Payment-flow fixes", 0, 4, ORANGE), ("R3  Refund root-cause actions", 3, 8, ORANGE), ("Review: KPI refresh & ROI check", 5, 6, GREY), ("Review: year-end ROI check", 13, 14, GREY)]
for i, (nm, a, b, c) in enumerate(tasks): ax.barh(len(tasks) - i, b - a, left=a, color=c, height=.55); ax.text(-0.3, len(tasks) - i, nm, ha="right", va="center", fontsize=10)
ax.set_xlim(0, len(mo)); ax.set_xticks(range(0, len(mo), 1)); ax.set_xticklabels([p.strftime("%b\n%y") if i % 2 == 0 else "" for i, p in enumerate(mo)], fontsize=8)
ax.set_yticks([]); ax.grid(axis="x", alpha=.25); ax.spines["left"].set_visible(False)
f.text(0.04, 0.085, "Owners (proposed): R1 Pricing & Promotions Lead; R2 Head of Growth with Merchandising; R3 Payments Operations & Customer Support.\nGovernance: monthly KPI review using the dashboard.", fontsize=10.5, color=INK, linespacing=1.5)
pages.append(f)

# 12 decisions / risks
f = slide("Decisions requested and key risks", "What we need from the Executive Committee today")
card(f, 0.04, 0.42, 0.44, 0.40, "Decisions requested", "1. Approve the Electronics discount cap and the first-order discount test.\n2. Approve the Q4 plan budget and start the Q4 2026 sprint now.\n3. Appoint an owner for the payment and refund leakage programme.\n4. Commission real marketing-spend data so CAC can be trusted.", ORANGE, 11.5, 48)
card(f, 0.52, 0.42, 0.44, 0.40, "Risks and mitigations", "Cap reduces Electronics volume: monitor weekly, relax if lost profit exceeds gain.\nQ4 over-stocking: stage purchase orders and use last year's curve.\nLeakage fixes slower than planned: report conversion weekly.\nEvidence is observational: test before scaling.", RED, 11.5, 48)
bullets(f, 0.04, 0.34, ["Data limits: synthetic dataset; marketing spend illustrative; the data ends Dec 2025, so a refresh is the first action before launch.",
                        "Not covered: shipping and payment fees, competitor pricing, customer-level lifetime value.",
                        "Next analysis: contribution margin after fees; retention drivers beyond discounting; real CAC by channel."], size=11.5, w=115, step=0.07)
pages.append(f)

# 13 portfolio
f = slide("Appendix: analytics portfolio and evidence", "Every claim in this deck traces to one of these deliverables")
rows = [["Task 2", "KPI dictionary and data-quality contract", "kpi_dictionary.xlsx, data_profile_notebook.ipynb, data_quality_contract.md"],
        ["Task 3", "Data ingestion, cleaning, preprocessing", "data_cleaning.ipynb, clean_dataset.csv, raw_retail_sales.csv"],
        ["Task 4", "Exploratory analysis and hypothesis tests", "eda_analysis.ipynb"],
        ["Task 5", "Interactive dashboard (Streamlit) and PDF export", "app.py, dashboard_metrics.py, Dashboard_Export.pdf"],
        ["Task 6", "Executive decision report (this deck)", "Executive_Decision_Report.pdf, build_executive_report.py"]]
ax = f.add_axes([0.04, 0.38, 0.92, 0.40]); ax.axis("off")
tb = ax.table(cellText=rows, colLabels=["Stage", "Deliverable", "Files"], colWidths=[0.1, 0.34, 0.56], loc="upper center", cellLoc="left")
tb.auto_set_font_size(False); tb.set_fontsize(11); tb.scale(1, 2.1)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor("#E2E8F0")
    if r == 0: cell.set_facecolor(NAVY); cell.set_text_props(color="white", fontweight="bold")
f.text(0.04, 0.30, "Repository: github.com/harinimariyappan-09/data-analytics-project", fontsize=13, fontweight="bold", color=BLUE)
f.text(0.04, 0.24, "The live dashboard link is in the repository README (Task 5 section).", fontsize=11.5, color=INK)
pages.append(f)

with PdfPages("Executive_Decision_Report.pdf") as pdf:
    for p in pages: pdf.savefig(p); plt.close(p)
    pdf.infodict().update({"Title": "Executive Decision Report", "Author": "Retail Analytics Capstone"})
print(len(pages), "slides saved")
