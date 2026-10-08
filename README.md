# Data Analytics Projects

## Task 2: KPI Dictionary & Data Quality Contract (retail orders)

| File | Purpose |
|---|---|
| `kpi_dictionary.xlsx` | 10 KPIs with formula, grain, filters, owner, refresh cadence; DQ check catalog; live-formula verification |
| `data_profile_notebook.ipynb` | Executable data profile: 18 checks across completeness, uniqueness, validity, consistency, freshness |
| `data_quality_contract.md` | Thresholds, severity levels, escalation actions |
| `retail-orders-raw.csv`, `retail-data-dictionary.csv` | Input data |
| `dq_results.csv`, `clean_orders.csv`, `quarantine_orders.csv`, `kpi_values.csv` | Notebook outputs |

**Result:** 12 of 18 checks fail (7 at P1), the extract is 260 days stale, and only 6 of 11 distinct orders are KPI-ready, so the contract verdict is BLOCK.

## Task 3: Data Ingestion, Cleaning & Preprocessing with Pandas

Cleans a messy 12,420-row e-commerce extract into 11,822 standardized rows. The dataset is **synthetic**, generated with known defects so the result can be verified.

| File | Purpose |
|---|---|
| `data_cleaning.ipynb` | Executed notebook: before/after profile, cleaning decisions, validation, charts |
| `clean_dataset.csv` | Cleaned output (31 columns incl. engineered features) |
| `raw_retail_sales.csv` | Raw input |
| `dataset_generation.py`, `generation_log.json` | Generator and ground-truth log |

**Fixed:** 420 duplicates, 7,895 text-in-number cells, 5 date formats, 20+ spellings per category, impossible quantities/discounts/prices, missing values (imputed and flagged).

## How to run
Install: `pip install pandas numpy matplotlib jupyter`. Keep the CSV files in the same folder as the notebooks, then run `jupyter nbconvert --to notebook --execute data_profile_notebook.ipynb` (task 2) or `data_cleaning.ipynb` (task 3).
## Task 4: Exploratory Data Analysis & Statistical Insights

`eda_analysis.ipynb` analyses `clean_dataset.csv` (output of Task 3): descriptive statistics, distributions, box plots, correlation heatmaps, multivariate views, 3 hypothesis tests and top 5 findings.

| Hypothesis | Test | Result |
|---|---|---|
| Q4 revenue is higher than the rest of the year | Welch t-test + Mann-Whitney | Confirmed: +44%, p < 0.0001 |
| Profit margin differs by category | Kruskal-Wallis + Tukey HSD | Confirmed: epsilon-squared 0.68 |
| First-order discount improves 180-day retention | Chi-square | No effect: 47.6% vs 47.5%, p = 0.96 |

**Top findings:** Q4 seasonality (+44%); Electronics is 32% of revenue but 22.6% of profit; discounts cut margin from 38.5% to 21.6% without lifting order size or retention; all 27 loss-making orders are Electronics at 20-25% discount; only 81% of orders become revenue.
## Task 5: Interactive Dashboard & KPI Visualizations

**Live app:** https://YOUR-APP-NAME.streamlit.app  |  **PDF export:** [Dashboard_Export.pdf](Dashboard_Export.pdf)

Streamlit + Plotly dashboard on the cleaned orders from Task 3: headline KPIs (Revenue, AOV, CAC, Churn) with sparklines and period-over-period change, area trend chart, India regional heatmap, customer acquisition and churn charts, and a category-to-product sunburst.

- **Slicers:** period, region, category, payment method
- **Drill-down:** Year → Quarter → Month → Day (trend), Category → Product (sunburst)
- **Files:** `app.py` (UI), `dashboard_metrics.py` (KPI engine shared with the PDF), `build_dashboard_pdf.py` (PDF export)

**Data notes:** the dataset is synthetic. Marketing spend (`marketing_spend.csv`) is illustrative because the orders data has no spend; replace it with real spend and CAC updates automatically.

**Run locally:** `pip install -r requirements.txt` then `streamlit run app.py`
