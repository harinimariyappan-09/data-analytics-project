# KPI Dictionary & Data Quality Contract: Retail Orders

| File | What it is |
|---|---|
| `kpi_dictionary.xlsx` | KPI dictionary (10 KPIs: formula, grain, filters, owner, refresh cadence) plus DQ check catalog and live-formula KPI verification |
| `data_profile_notebook.ipynb` | Executable data profile: 18 checks across completeness, uniqueness, validity, consistency, freshness; cleaning; KPI calculation |
| `data_quality_contract.md` | Quality contract: thresholds, severities, escalation actions, remediation rules |
| `retail-orders-raw.csv`, `retail-data-dictionary.csv` | Input data and its dictionary |
| `dq_results.csv`, `clean_orders.csv`, `quarantine_orders.csv`, `kpi_values.csv` | Outputs written by the notebook |

**Run:** `pip install pandas jupyter`, then `jupyter nbconvert --to notebook --execute data_profile_notebook.ipynb` (CSV files must sit next to the notebook).

**Headline result:** 12 of 18 checks fail (7 at P1), the extract is 260 days stale, and only 6 of 11 distinct orders are KPI-ready, so the contract verdict is BLOCK.
