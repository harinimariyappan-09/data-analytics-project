"""
Creates marketing_spend.csv - ILLUSTRATIVE marketing spend (the order data contains no spend, but CAC needs it).

Assumed model (documented in the dashboard and README):
  performance spend  = INR 450 per newly acquired customer (pay-per-acquisition channels) x seasonal factor x noise
  always-on spend    = INR 30,000 per month (brand, content, tools) shared across regions by order share
  seasonal factor    = 1.25 in Oct-Dec (festive campaigns), 1.0 otherwise
Replace this file with real spend (same columns) and every CAC number in the dashboard updates.
Run: python generate_marketing_spend.py
"""
import numpy as np
import pandas as pd

from dashboard_metrics import DashboardData, REGIONS_ALL, load_orders

rng = np.random.default_rng(2026)
orders = load_orders()
dd = DashboardData(orders, pd.DataFrame({"region": [], "spend_inr": [], "ym": []}))
months = dd.months

region_w = orders["region"].value_counts(normalize=True).reindex(REGIONS_ALL).fillna(0.0)
new = dd.customers.groupby(["first_ym", "region"]).size().unstack("region").reindex(index=months, columns=REGIONS_ALL).fillna(0)
channels = {"Paid Search": 0.38, "Social Media": 0.30, "Influencer & Affiliate": 0.20, "Email & CRM": 0.12}

rows = []
for m in months:
    season = 1.25 if m.month >= 10 else 1.0
    for r in REGIONS_ALL:
        perf = new.loc[m, r] * 450 * season * rng.lognormal(0, 0.12)
        brand = 30_000 * region_w[r] * season * rng.lognormal(0, 0.10)
        total = perf + brand
        shares = np.array(list(channels.values())) * rng.uniform(0.9, 1.1, len(channels))
        shares = shares / shares.sum()
        for ch, sh in zip(channels, shares):
            rows.append({"month": m.to_timestamp().date().isoformat(), "region": r, "channel": ch, "spend_inr": round(total * sh, 2)})

out = pd.DataFrame(rows)
out.to_csv("marketing_spend.csv", index=False)
print(out.shape, "| total spend INR", f"{out.spend_inr.sum():,.0f}")
