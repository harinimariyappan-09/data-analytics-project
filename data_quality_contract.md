# Data Quality Contract: Retail Orders

| | |
|---|---|
| **Dataset** | `retail-orders-raw.csv`: one row per order line, columns defined in `retail-data-dictionary.csv` |
| **Producer (data owner)** | Retail Operations / order-system team |
| **Steward** | Data Platform Owner |
| **Consumer & decision owner** | Head of Growth & Revenue Operations (pricing, discounting and campaign-spend decisions) |
| **Version / date** | v1.0, 2026-10-05 |
| **Executable proof** | `data_profile_notebook.ipynb` runs every check below; `kpi_dictionary.xlsx` (sheet *DQ_Checks*) mirrors the results |

*Roles are proposed for this exercise; replace them with real names and on-call channels.*

## 1. What "trustworthy" means

An order is **trustworthy** when it has a unique `order_id`, a real ISO date between 2025-01-01 and today, a whole-number quantity above zero, a non-negative price, an explicit discount between 0 and 100, and a segment, category and payment status from the allowed lists. The extract as a whole is **fresh** when its newest order is no more than 2 days old.

Only trustworthy orders feed the 10 KPIs in `kpi_dictionary.xlsx`. Everything else goes to quarantine with a reason.

## 2. Checks, thresholds and severity

Threshold = maximum tolerated failure rate (share of rows), except freshness (days). **0% means zero tolerance.**

| ID | Dimension | Rule | Threshold | Severity | Result on this extract |
|---|---|---|---|---|---|
| C1 | Completeness | `order_date` not null | 0% | P1 | FAIL: 1 of 12 (8.3%) |
| C2 | Completeness | `city` not null | 2% | P2 | FAIL: 1 of 12 (8.3%) |
| C3 | Completeness | `discount_pct` not null (missing is not assumed 0) | 0% | P2 | FAIL: 1 of 12 (8.3%) |
| C4 | Completeness | all other required columns not null | 0% | P1 | PASS |
| U1 | Uniqueness | `order_id` appears once | 0% | P1 | FAIL: 1 duplicate (RT-1004) |
| U2 | Uniqueness | no fully duplicated rows | 0% | P1 | FAIL: 1 row |
| V1 | Validity | ISO `order_date` is a real date in 2025-01-01..today | 0% | P1 | FAIL: `2026-13-10` |
| V2 | Validity | `quantity` is a whole number > 0 | 0% | P1 | FAIL: 2 rows (`-1`, `two`) |
| V3 | Validity | `unit_price` is non-negative | 0% | P1 | PASS |
| V4 | Validity | `discount_pct` between 0 and 100 | 0% | P1 | FAIL: 105 |
| V5 | Validity | `category` in {Learning Kit, Course Access, Mentor Session} | 0% | P2 | PASS |
| V6 | Validity | segment and status valid after normalization | 0% | P2 | PASS |
| K1 | Consistency | segment uses canonical casing | 0% | P3 | FAIL: `student` |
| K2 | Consistency | payment status uses canonical casing | 0% | P3 | FAIL: `paid` |
| K3 | Consistency | one date format (`YYYY-MM-DD`) | 0% | P2 | FAIL: `03/01/2026` |
| K4 | Consistency | one `unit_price` per category | 0% | P2 | PASS |
| K5 | Consistency | no `order_id` with conflicting versions | 0% | P1 | PASS |
| F1 | Freshness | newest valid order at most 2 days old | 2 days | P1 | FAIL: 260 days old (latest 2026-01-18) |

**Result: 12 of 18 checks fail, including 7 at P1. Contract verdict: BLOCK.**

## 3. Failure thresholds that trigger escalation

* **Any single P1 failure** triggers the P1 path.
* **Any P2 failure** (or a P2 rate above its threshold) triggers the P2 path.
* **Data Quality Pass Rate (KPI-10) below 98%** over a load is treated as a P1, even if each individual check is within tolerance.
* **Two consecutive loads failing the same P2 check** are promoted to P1.

## 4. Escalation actions

| Severity | Automatic action | Who is told | Response | Resolution |
|---|---|---|---|---|
| **P1** | **Block** the dashboard refresh; keep the last good snapshot and show a "data on hold" banner | Page the Data Platform Owner; email the Decision Owner | Within 4 business hours | Fix at source, or a written exception signed by the Decision Owner, within 1 business day |
| **P2** | **Warn**: publish with a visible data-quality warning; flag affected rows | Ticket to the source-system owner; line in the daily DQ digest | Within 1 business day | Fix within 3 business days |
| **P3** | **Auto-fix**: normalize in the pipeline and log the change | Weekly DQ review | Next weekly review | Fix at source within 2 weeks |

If a P1 is still open after its resolution deadline, it escalates to the Head of Data / Engineering lead and the affected KPIs are marked "unavailable" rather than shown with doubtful numbers.

## 5. Remediation rules (applied by the notebook)

1. Exact duplicate rows are dropped; the first is kept.
2. Segment and payment-status casing is normalized (`student` to `Student`, `paid` to `Paid`).
3. `DD/MM/YYYY` dates are repaired to ISO and flagged as a repair (India date convention).
4. A row with a **blocking defect** is quarantined and excluded from all KPIs: missing or invalid date, invalid quantity, missing or out-of-range discount.
5. Nothing is guessed: `"two"` is not converted to 2, and a missing discount is not treated as 0 unless the data owner supplies a documented justification.
6. Missing `city` is non-blocking; the row stays in revenue KPIs but is excluded from city-level breakdowns.

Outcome on this extract: 12 raw rows = 6 clean + 5 quarantined (RT-1003, RT-1006, RT-1007, RT-1008, RT-1011) + 1 duplicate dropped. **6 of 11 distinct orders (54.5%) are KPI-ready.**

## 6. Producer commitments

* Deliver a fresh extract every day by 06:00 IST, with `order_date` in ISO format.
* Use a primary key on `order_id`; send one row per order line without duplicates.
* Validate quantity, discount and enumerated fields at entry (reject `two`, `-1`, `105`).
* Record a reason code whenever discount is intentionally blank.

## 7. Consumer commitments

* Report KPIs only from the clean set and show the Data Quality Pass Rate beside them.
* Never override a P1 block without the signed exception described above.

## 8. Change control

Thresholds, rules or severities change only by pull request approved by both the Data Platform Owner and the Decision Owner. Every change bumps the contract version and re-runs the notebook.
