"""
Generates raw_retail_sales.csv: a SYNTHETIC, intentionally messy e-commerce sales extract (12,000+ rows).

Every defect is injected on purpose at a known rate so the cleaning notebook can be checked against
generation_log.json. Run:  python dataset_generation.py   (seed is fixed, output is reproducible)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_ORDERS = 12_000
HERE = Path(__file__).parent
rng = np.random.default_rng(SEED)

# ------------------------------------------------------------------ catalogue
CATALOG = {
    "Electronics": [("Wireless Earbuds", 2499), ("Smart Watch", 4999), ("Bluetooth Speaker", 3299), ("Power Bank", 1599), ("Webcam", 2799)],
    "Home & Kitchen": [("Air Fryer", 5499), ("Mixer Grinder", 3999), ("Water Bottle", 599), ("Cookware Set", 2999), ("LED Lamp", 899)],
    "Fashion": [("Running Shoes", 3499), ("Denim Jacket", 2799), ("T-Shirt", 699), ("Backpack", 1799), ("Sunglasses", 1299)],
    "Beauty": [("Face Serum", 899), ("Perfume", 1999), ("Hair Dryer", 1899), ("Lipstick", 599), ("Sunscreen", 449)],
    "Books & Stationery": [("Notebook Pack", 349), ("Novel", 399), ("Pen Set", 249), ("Planner", 549), ("Textbook", 1099)],
}
COST_RATIO = {"Electronics": 0.72, "Home & Kitchen": 0.62, "Fashion": 0.55, "Beauty": 0.50, "Books & Stationery": 0.65}
PRODUCT_COST = {p: round(bp * COST_RATIO[c] * (1 + rng.uniform(-0.04, 0.04)), 2) for c, items in CATALOG.items() for p, bp in items}

REGIONS = ["North", "South", "East", "West", "Central"]
PAY_METHODS = ["Credit Card", "Debit Card", "UPI", "Net Banking", "COD"]
STATUSES = ["Paid", "Pending", "Failed", "Refunded"]

# ------------------------------------------------------------------ clean "truth" table
days = pd.date_range("2023-01-01", "2025-12-31")
month_w = np.array([1, 1, 1, 1, 1, 1, 1, 1.1, 1.1, 1.3, 1.5, 1.6])
w = month_w[days.month - 1]
order_dates = np.sort(rng.choice(days, N_ORDERS, p=w / w.sum()))

cat = rng.choice(list(CATALOG), N_ORDERS, p=[.22, .22, .24, .17, .15])
product, base = [], []
for c in cat:
    name, bp = CATALOG[c][rng.integers(len(CATALOG[c]))]
    product.append(name)
    base.append(bp)

t = pd.DataFrame({
    "order_id": [f"ORD-{100001 + i}" for i in range(N_ORDERS)],
    "order_date": pd.to_datetime(order_dates),
    "customer_id": [f"C{n:05d}" for n in rng.integers(1, 3001, N_ORDERS)],
    "category": cat,
    "product": product,
    "region": rng.choice(REGIONS, N_ORDERS, p=[.25, .30, .15, .20, .10]),
    "quantity": rng.choice([1, 2, 3, 4, 5], N_ORDERS, p=[.55, .25, .10, .06, .04]).astype(float),
    "unit_price": np.round(np.array(base) * rng.uniform(0.92, 1.08, N_ORDERS), 2),
    "cost_price": np.round(np.array([PRODUCT_COST[p] for p in product]) * rng.uniform(0.98, 1.02, N_ORDERS), 2),
    "discount_pct": rng.choice([0, 5, 10, 15, 20, 25], N_ORDERS, p=[.40, .20, .20, .10, .07, .03]).astype(float),
    "payment_method": rng.choice(PAY_METHODS, N_ORDERS, p=[.25, .15, .35, .10, .15]),
    "payment_status": rng.choice(STATUSES, N_ORDERS, p=[.82, .06, .05, .07]),
    "customer_rating": rng.choice([1, 2, 3, 4, 5], N_ORDERS, p=[.05, .07, .15, .33, .40]).astype(float),
})
t["payment_method"] = t["payment_method"].astype(object)

log = {"seed": SEED, "clean_orders_generated": N_ORDERS, "injected": {}}


def inject(col, frac, label, fn=None):
    """Pick ~frac of rows (not already NaN) and either blank them (fn=None) or transform them."""
    m = (rng.random(N_ORDERS) < frac) & t[col].notna().to_numpy()
    if fn is None:
        t.loc[m, col] = np.nan if t[col].dtype != object else None
    else:
        t.loc[m, col] = fn(t.loc[m, col])
    log["injected"][label] = int(m.sum())
    return m


# ---- missing values
inject("order_id", .003, "missing order_id")
m_date_missing = inject("order_date", .010, "missing order_date")
inject("customer_id", .030, "missing customer_id")
inject("region", .040, "missing region")
inject("product", .015, "missing product")
inject("quantity", .020, "missing quantity")
inject("unit_price", .020, "missing unit_price")
inject("cost_price", .030, "missing cost_price")
inject("discount_pct", .050, "missing discount_pct")
inject("payment_method", .020, "missing payment_method")
inject("payment_status", .010, "missing payment_status")
inject("customer_rating", .250, "missing customer_rating")

# ---- invalid values / outliers
inject("unit_price", .004, "unit_price x10 outlier", lambda s: s * 10)
inject("unit_price", .0015, "negative unit_price", lambda s: -s)
inject("quantity", .003, "quantity outlier (50/99/100)", lambda s: pd.Series(rng.choice([50, 99, 100], len(s)), index=s.index, dtype=float))
inject("quantity", .004, "quantity zero/negative", lambda s: pd.Series(rng.choice([0, -1, -2], len(s)), index=s.index, dtype=float))
inject("discount_pct", .0025, "discount outside 0-100", lambda s: pd.Series(rng.choice([105, 150, -5], len(s)), index=s.index, dtype=float))
inject("order_date", .002, "order_date typo (year +27, in the future)", lambda s: s + pd.DateOffset(years=27))

# ------------------------------------------------------------------ turn into messy text
MISSING_TOKENS = ["", "NA", "N/A", "null", "-"]
miss = lambda: str(rng.choice(MISSING_TOKENS, p=[.40, .20, .15, .15, .10]))
isna = lambda v: v is None or (isinstance(v, float) and np.isnan(v)) or v is pd.NaT or (not isinstance(v, str) and pd.isna(v))


def f_date(d):
    if isna(d):
        return miss()
    k = rng.random()
    if k < .55: return d.strftime("%Y-%m-%d")
    if k < .75: return d.strftime("%d/%m/%Y")
    if k < .87: return d.strftime("%d-%b-%Y")
    if k < .97: return d.strftime("%b %d, %Y")
    return d.strftime("%d.%m.%Y")


def f_price(v):
    if isna(v): return miss()
    k = rng.random()
    if k < .70: return f"{v:.2f}"
    if k < .85: return f"\u20b9{v:,.2f}"
    if k < .95: return f"Rs. {v:.2f}"
    return f"{v:.2f} INR"


def f_cost(v):
    if isna(v): return miss()
    return f"{v:.2f}" if rng.random() < .9 else f"\u20b9{v:,.2f}"


WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}


def f_qty(v):
    if isna(v): return miss()
    v = int(v)
    k = rng.random()
    if k < .91: return str(v)
    if k < .99 or v not in WORDS: return f"{v}.0"
    return WORDS[v]


def f_disc(v):
    if isna(v): return miss()
    k = rng.random()
    if k < .70: return f"{int(v)}"
    if k < .95: return f"{int(v)}%"
    return f"{v:.1f}"


def f_rating(v):
    if isna(v): return miss()
    return f"{int(v)}" if rng.random() < .8 else f"{int(v)}.0"


def variants(canon, others, p_canon=.80):
    def f(v):
        if isna(v): return miss()
        opts = others.get(v, [])
        if not opts or rng.random() < p_canon: return v
        return str(rng.choice(opts))
    return f


f_region = variants(None, {"North": ["north", "NORTH", " North ", "N"], "South": ["south", "SOUTH", " South ", "S"],
                           "East": ["east", "EAST", " East ", "E"], "West": ["west", "WEST", " West ", "W"],
                           "Central": ["central", "CENTRAL", " Central ", "C"]})
f_cat = variants(None, {"Electronics": ["electronics", "ELECTRONICS", "Electronics ", "Electronic"],
                        "Home & Kitchen": ["home & kitchen", "Home and Kitchen", "HOME & KITCHEN", "Home & Kitchen "],
                        "Fashion": ["fashion", "FASHION", "Fashion "], "Beauty": ["beauty", "BEAUTY", "Beauty "],
                        "Books & Stationery": ["Books & Stationary", "books & stationery", "Books and Stationery", "BOOKS & STATIONERY"]}, .85)
f_pay = variants(None, {"Credit Card": ["credit card", "CC", "Credit-Card", "Credit card"], "Debit Card": ["debit card", "DC", "Debit card"],
                        "UPI": ["upi", "Upi", "U.P.I"], "Net Banking": ["netbanking", "Net-Banking", "net banking"],
                        "COD": ["cod", "Cash on Delivery", "Cod"]}, .75)
f_status = variants(None, {s: [s.lower(), s.upper(), f" {s}", f"{s} "] for s in STATUSES}, .85)


def f_prod(v):
    if isna(v): return miss()
    k = rng.random()
    if k < .92: return v
    return v.lower() if k < .96 else f"{v} "


def f_cust(v):
    if isna(v): return miss()
    return v if rng.random() < .97 else v.lower()


def f_id(v):
    return miss() if isna(v) else v


def to_raw(df):
    return pd.DataFrame({
        "order_id": df["order_id"].map(f_id), "order_date": df["order_date"].map(f_date),
        "customer_id": df["customer_id"].map(f_cust), "category": df["category"].map(f_cat),
        "product": df["product"].map(f_prod), "region": df["region"].map(f_region),
        "quantity": df["quantity"].map(f_qty), "unit_price": df["unit_price"].map(f_price),
        "cost_price": df["cost_price"].map(f_cost), "discount_pct": df["discount_pct"].map(f_disc),
        "payment_method": df["payment_method"].map(f_pay), "payment_status": df["payment_status"].map(f_status),
        "customer_rating": df["customer_rating"].map(f_rating),
    })


raw = to_raw(t)
raw["_pos"] = np.arange(N_ORDERS, dtype=float)

# ---- duplicates: exact copies + "near" copies (same order, re-typed with different formatting)
exact_idx = rng.choice(N_ORDERS, 300, replace=False)
near_idx = rng.choice(np.setdiff1d(np.arange(N_ORDERS), exact_idx), 120, replace=False)
exact = raw.iloc[exact_idx].copy()
near = to_raw(t.iloc[near_idx]).assign(_pos=near_idx.astype(float))
for d in (exact, near):
    d["_pos"] = rng.uniform(0, N_ORDERS, len(d))
log["injected"]["exact duplicate rows"] = len(exact)
log["injected"]["near-duplicate rows (same values, different formatting)"] = len(near)

final = pd.concat([raw, exact, near]).sort_values("_pos", kind="stable").drop(columns="_pos").reset_index(drop=True)

# ---- rows a correct cleaning process must drop for lack of a usable key (order_id / valid date)
bad_date = t["order_date"].isna() | (t["order_date"] > "2025-12-31")
unusable = t["order_id"].isna() | bad_date
log["expected_unusable_orders_to_drop"] = int(unusable.sum())
log["expected_clean_rows"] = int((~unusable).sum())
log["raw_rows"] = len(final)

final.to_csv(HERE / "raw_retail_sales.csv", index=False, encoding="utf-8")
(HERE / "generation_log.json").write_text(json.dumps(log, indent=2))
print(json.dumps(log, indent=2))
