# Data Ingestion, Cleaning & Preprocessing with Pandas

Cleaning a messy 12,420-row e-commerce order extract (13 columns, INR, 2023-2025) into a standardized 11,822-row dataset.

> **Note:** the dataset is **synthetic**. `dataset_generation.py` (seeded) injects realistic defects at known rates, so the notebook's result can be verified against `generation_log.json`.

| File | Purpose |
|---|---|
| `data_cleaning.ipynb` | Main deliverable: executed notebook with before/after profile, every cleaning decision explained, validation checks, charts |
| `clean_dataset.csv` | Cleaned output (11,822 rows, 31 columns incl. engineered features and `*_imputed` flags) |
| `raw_retail_sales.csv` | Raw input (12,420 rows) |
| `dataset_generation.py`, `generation_log.json` | Generator and ground-truth log for the synthetic data |

## What was fixed
| Problem | Raw | Clean |
|---|---|---|
| Duplicate rows (exact + re-typed) | 420 | 0 |
| Missing values in key columns / impossible dates | 178 rows dropped | 0 |
| Missing values elsewhere (rows affected, excl. rating) | 2,746 | 0 (imputed and flagged) |
| Text in numeric columns (`Rs. 1299`, `10%`, `two`) | 7,895 cells | 0 |
| Date formats | 5 | 1 |
| Spellings of category / region / payment method / status | 23 / 25 / 21 / 20 | 5 / 5 / 5 / 4 |
| Impossible quantities, discounts, price outliers | 65 / 30 / 61 | 0 |

## Features engineered
`year, month, month_name, quarter, year_month, day_of_week, is_weekend, gross_amount, discount_amount, revenue, total_cost, profit, profit_margin_pct, counts_as_revenue`

## Run
```bash
pip install pandas numpy matplotlib jupyter
jupyter nbconvert --to notebook --execute data_cleaning.ipynb
```
(keep `raw_retail_sales.csv` and `generation_log.json` next to the notebook)

## Assumptions to review
Blank discount = 0 (flagged); dates are DD/MM/YYYY; quantity above 10 is an entry error; only `Paid` orders count as revenue; `customer_rating` is left empty (25% missing) rather than invented.
