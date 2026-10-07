# Data Analytics Projects

## Task 2: KPI Dictionary & Data Quality Contract (retail orders)
| File | Purpose |
|---|---|
| `kpi_dictionary.xlsx` | 10 KPIs with formula, grain, filters, owner, refresh cadence; DQ check catalog; live-formula verification |
| `data_profile_notebook.ipynb` | Executable data profile: 18 checks across completeness, uniqueness, validity, consistency, freshness |
| `data_quality_contract.md` | Thresholds, severity levels, escalation actions |
| `retail-orders-raw.csv`, `retail-data-dictionary.csv` | Input data |
| `dq_results.csv`, `clean_orders.csv`, `quarantine_orders.csv`, `kpi_values.csv` | Notebook outputs |

Result: 12 of 18 checks fail (7 at P1), data is 260 days stale, only 6 of 11 distinct orders are KPI-ready, so the contract verdict is BLOCK.

## Task 3: Data Ingestion, Cleaning & Preprocessing with Pandas
Cleans a messy 12,420-row e-commerce extract into 11,822 standardized rows. The dataset is **synthetic**, generated with known defects so the result can be verified.

| File | Purpose |
|---|---|
| `data_cleaning.ipynb` | Executed notebook: before/after profile, cleaning decisions, validation, charts |
| `clean_dataset.csv` | Cleaned output (31 columns incl. engineered features) |
| `raw_retail_sales.csv` | Raw input |
| `dataset_generation.py`, `generation_log.json` | Generator and ground-truth log |

Fixed: 420 duplicates, 7,895 text-in-number cells, 5 date formats, 20+ spellings per category, impossible quantities/discounts/prices, missing values (imputed and flagged).

**Run:** `pip install pandas numpy matplotlib jupyter`, then execute the notebooks with the CSV files in the same folder.
