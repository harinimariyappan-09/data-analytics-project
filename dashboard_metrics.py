"""
Shared KPI engine for the dashboard (used by app.py AND build_dashboard_pdf.py so both show identical numbers).

KPI definitions
  Revenue          sum of `revenue` of PAID orders
  AOV              Revenue / number of paid orders
  New customer     customer whose first PAID order falls in the period (customer region = region of that first order)
  CAC              marketing spend / new customers            (spend: marketing_spend.csv, ILLUSTRATIVE - see README)
  Active customer  customer with a paid order in the trailing 180 days
  Churn rate       share of customers active at the end of the previous month that are NOT active at the end of this month
                   (i.e. their last purchase is now more than 180 days old). Needs a 180-day history, so it starts Jul 2023.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
CHURN_WINDOW_DAYS = 180
ZONES = ["North", "South", "East", "West", "Central"]
REGIONS_ALL = ZONES + ["Unknown"]
EPOCH = pd.Timestamp("2000-01-01")


def load_orders(path=None) -> pd.DataFrame:
    df = pd.read_csv(path or HERE / "clean_dataset.csv", parse_dates=["order_date"])
    df["ym"] = df["order_date"].dt.to_period("M")
    df["quarter_label"] = df["year"].astype(str) + " Q" + df["quarter"].astype(str)
    return df


def load_spend(path=None) -> pd.DataFrame:
    s = pd.read_csv(path or HERE / "marketing_spend.csv", parse_dates=["month"])
    s["ym"] = s["month"].dt.to_period("M")
    return s


def load_geojson() -> dict:
    return json.load(open(HERE / "india_zones.geojson"))


def _pct_change(cur, prev):
    if cur is None or prev is None or pd.isna(cur) or pd.isna(prev) or prev == 0:
        return None
    return cur / prev - 1


class DashboardData:
    """Loads the data once and answers every question the dashboard asks."""

    def __init__(self, orders: pd.DataFrame, spend: pd.DataFrame):
        self.orders = orders
        self.spend = spend
        self.paid = orders[orders["counts_as_revenue"]].copy()
        self.months = pd.period_range(orders["ym"].min(), orders["ym"].max(), freq="M")
        self.data_min = orders["order_date"].min()
        self.categories = sorted(orders["category"].unique())
        self.methods = sorted(orders["payment_method"].unique())
        self.customers = self._build_customers()
        self.active = self._build_activity()
        ends = [m.end_time.normalize() for m in self.months]
        lag = pd.Timedelta(days=CHURN_WINDOW_DAYS)
        floor = self.data_min - pd.Timedelta(days=1)
        self.valid_active = np.array([(e - lag) >= floor for e in ends])
        self.valid_churn = np.array([False] + [(ends[i - 1] - lag) >= floor for i in range(1, len(ends))])

    # ------------------------------------------------------------------ customers
    def _build_customers(self) -> pd.DataFrame:
        p = self.paid[self.paid["customer_id"] != "UNKNOWN"].sort_values(["order_date", "order_id"])
        first = p.groupby("customer_id").head(1).set_index("customer_id")[["order_date", "region"]]
        first.columns = ["first_date", "region"]
        first["first_ym"] = first["first_date"].dt.to_period("M")
        return first

    def _build_activity(self) -> pd.DataFrame:
        p = self.paid[self.paid["customer_id"].isin(self.customers.index)]
        tmp = pd.DataFrame({"c": p["customer_id"].values, "ym": p["ym"].values, "d": (p["order_date"] - EPOCH).dt.days.values})
        last = tmp.groupby(["c", "ym"])["d"].max().unstack("ym").reindex(index=self.customers.index, columns=self.months)
        last = last.fillna(-10**6).cummax(axis=1)                      # last purchase on or before each month end
        ends = np.array([(m.end_time.normalize() - EPOCH).days for m in self.months])
        return pd.DataFrame(last.values > (ends - CHURN_WINDOW_DAYS)[None, :], index=self.customers.index, columns=self.months)

    # ------------------------------------------------------------------ monthly frame
    def paid_filtered(self, regions=None, categories=None, methods=None) -> pd.DataFrame:
        p = self.paid
        if regions is not None:    p = p[p["region"].isin(regions)]
        if categories is not None: p = p[p["category"].isin(categories)]
        if methods is not None:    p = p[p["payment_method"].isin(methods)]
        return p

    def customer_monthly(self, regions) -> pd.DataFrame:
        idx = self.customers.index[self.customers["region"].isin(regions)]
        A = self.active.loc[idx].values
        prev = np.zeros_like(A)
        prev[:, 1:] = A[:, :-1]
        prev_n = prev.sum(0)
        churned = (prev & ~A).sum(0)
        churn = np.where(self.valid_churn & (prev_n > 0), churned / np.maximum(prev_n, 1), np.nan)
        new = self.customers.loc[idx].groupby("first_ym").size().reindex(self.months, fill_value=0).values
        return pd.DataFrame({"new_customers": new,
                             "active_customers": np.where(self.valid_active, A.sum(0), np.nan),
                             "churn_rate": churn}, index=self.months)

    def monthly(self, regions, categories, methods) -> pd.DataFrame:
        """One row per month with every KPI, for the given slicers (no date filter)."""
        p = self.paid_filtered(regions, categories, methods)
        g = p.groupby("ym").agg(revenue=("revenue", "sum"), orders=("order_id", "count"), profit=("profit", "sum"))
        m = g.reindex(self.months, fill_value=0.0)
        m["aov"] = m["revenue"] / m["orders"].replace(0, np.nan)
        m["margin"] = m["profit"] / m["revenue"].replace(0, np.nan)
        m = m.join(self.customer_monthly(regions))
        m["spend"] = self.spend[self.spend["region"].isin(regions)].groupby("ym")["spend_inr"].sum().reindex(self.months, fill_value=0.0)
        m["cac"] = m["spend"] / m["new_customers"].replace(0, np.nan)
        return m

    # ------------------------------------------------------------------ KPI summary over a month range
    @staticmethod
    def summarize(m: pd.DataFrame, i0: int, i1: int) -> dict:
        w = m.iloc[i0:i1 + 1]
        rev, orders, profit = w["revenue"].sum(), w["orders"].sum(), w["profit"].sum()
        new, spend = w["new_customers"].sum(), w["spend"].sum()
        churn = w["churn_rate"].dropna()
        active = w["active_customers"].iloc[-1]
        return {"revenue": rev, "orders": orders, "profit": profit,
                "aov": rev / orders if orders else np.nan,
                "margin": profit / rev if rev else np.nan,
                "new_customers": new, "spend": spend,
                "cac": spend / new if new else np.nan,
                "churn": churn.mean() if len(churn) else np.nan,
                "active": active}

    def kpis_with_delta(self, m: pd.DataFrame, i0: int, i1: int) -> tuple[dict, dict | None, dict]:
        """Current KPIs, previous-period KPIs (same length, immediately before) and deltas."""
        cur = self.summarize(m, i0, i1)
        n = i1 - i0 + 1
        prev = self.summarize(m, i0 - n, i0 - 1) if i0 - n >= 0 else None
        delta = {}
        for k in ["revenue", "orders", "profit", "aov", "new_customers", "cac", "active"]:
            delta[k] = _pct_change(cur[k], prev[k]) if prev else None
        for k in ["churn", "margin"]:                          # percentage-point change
            delta[k] = (cur[k] - prev[k]) if prev and not pd.isna(cur[k]) and not pd.isna(prev[k]) else None
        return cur, prev, delta

    # ------------------------------------------------------------------ region / category views
    def region_table(self, i0: int, i1: int, categories, methods) -> pd.DataFrame:
        start, end = self.months[i0], self.months[i1]
        p = self.paid_filtered(None, categories, methods)
        p = p[(p["ym"] >= start) & (p["ym"] <= end)]
        g = p.groupby("region").agg(revenue=("revenue", "sum"), orders=("order_id", "count"), profit=("profit", "sum"))
        c = self.customers[(self.customers["first_ym"] >= start) & (self.customers["first_ym"] <= end)].groupby("region").size().rename("new_customers")
        s = self.spend[(self.spend["ym"] >= start) & (self.spend["ym"] <= end)].groupby("region")["spend_inr"].sum().rename("spend")
        t = pd.DataFrame(index=REGIONS_ALL).join(g).join(c).join(s).fillna(0.0)
        t["aov"] = t["revenue"] / t["orders"].replace(0, np.nan)
        t["margin"] = t["profit"] / t["revenue"].replace(0, np.nan)
        t["cac"] = t["spend"] / t["new_customers"].replace(0, np.nan)
        return t

    @staticmethod
    def trend(p: pd.DataFrame, level: str) -> pd.DataFrame:
        """Aggregate paid orders at Year / Quarter / Month / Day level."""
        key = {"Year": "year", "Quarter": "quarter_label", "Month": "ym", "Day": "order_date"}[level]
        g = p.groupby(key).agg(revenue=("revenue", "sum"), profit=("profit", "sum"), orders=("order_id", "count")).reset_index().rename(columns={key: "period"})
        if level == "Month":
            g["period"] = g["period"].dt.to_timestamp()
        g["aov"] = g["revenue"] / g["orders"]
        return g
