# TraceImpact — KPI Definitions & Metric Formulation Guide

**Document Version:** 1.0.0  
**Milestone:** Day 3 (SQL Analytics & KPI Layer)  
**Target Audience:** Impact Evaluators, Nonprofit Finance Teams, Donors & Data Engineers

---

## 1. Overview & Architectural Principles

The TraceImpact analytical layer converts clean relational records (`programs`, `beneficiaries`, `attendance`, `expenses`, `outcomes`) into standard nonprofit performance indicators.

### Key Analytical Invariants:
1. **Pre-Aggregation Isolation:** All metrics are calculated inside isolated Common Table Expressions (CTEs) before being joined to master `programs`. This completely prevents **Cartesian row multiplication** (e.g., joining 14 expenses directly with 123 attendance rows would artificially multiply financial records).
2. **Defensive Division:** All denominators use `NULLIF(denominator, 0)` to guarantee mathematical safety against division-by-zero errors.
3. **Inclusive Reporting (`LEFT JOIN`):** Master programs with zero or partial records remain visible in consolidated scorecards rather than silently dropping off dashboards.
4. **Bi-Directional Provenance:** Every metric can be audited down to individual underlying domain rows and their original `source_record_id` in `source_records`.

---

## 2. Comprehensive KPI Catalog

```
+--------------------------------------------------------------------------------------------------+
|                                    KPI CATALOG SUMMARY                                           |
+------------------------------+---------------------------+---------------------------------------+
| KPI Name                     | Category                  | Primary Purpose                       |
+------------------------------+---------------------------+---------------------------------------+
| Distinct Beneficiaries       | Reach                     | Community reach headcount             |
| Total Session Hours          | Engagement                | Total dosage / delivery volume        |
| Attendance per Beneficiary   | Consistency               | Engagement depth & retention          |
| Total Program Expenses       | Financial                 | Operational cost per initiative       |
| Budget Utilization Rate      | Fiscal Discipline         | Actual spend vs allocated target      |
| Cost per Beneficiary         | Cost-Effectiveness        | Financial efficiency per person       |
| Cost per Beneficiary Hour    | Hourly Unit Economics     | Standardized cost per contact hour    |
| Average Outcome Improvement  | Impact Efficacy           | Mean skill/knowledge point gain       |
| Outcome Improvement Rate %   | Relative Impact           | Percentage gain over baseline         |
+------------------------------+---------------------------+---------------------------------------+
```

---

### KPI 1: Distinct Beneficiaries Served (Program Reach)

- **Business Meaning:** The unique number of distinct community members who participated in at least one program session.
- **Formula:**
  $$\text{Distinct Beneficiaries} = \text{COUNT}(\text{DISTINCT } \text{attendance.beneficiary_id})$$
- **Source Tables:** `attendance` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  COUNT(DISTINCT a.beneficiary_id) AS distinct_beneficiaries_served
  ```
- **Important Filters:** None (only verified attendance records loaded into domain table).
- **Null / Zero Handling:** Coerced to `0` using `COALESCE(..., 0)` if a program has no attendees.
- **Traceability Path:**
  $$\text{Metric} \longrightarrow \text{attendance rows} \longrightarrow \text{attendance.beneficiary_id} \longrightarrow \text{beneficiaries(source_record_id)} \longrightarrow \text{raw CSV}$$

---

### KPI 2: Total Session Hours Delivered (Dosage)

- **Business Meaning:** Cumulative contact hours of workshops, training, or clinical outreach delivered to community participants.
- **Formula:**
  $$\text{Total Session Hours} = \sum \text{attendance.session_hours}$$
- **Source Tables:** `attendance` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  COALESCE(SUM(a.session_hours), 0.00) AS total_session_hours
  ```
- **Important Filters:** Excludes quarantined duplicate check-ins (handled during Day 2 ingestion).
- **Null / Zero Handling:** Defaults to `0.00` if no session hours exist.
- **Traceability Path:**
  Each hour originates from an individual `attendance_id` with its own `source_record_id`.

---

### KPI 3: Attendance Consistency (Sessions per Beneficiary)

- **Business Meaning:** The average number of sessions attended by each participating beneficiary, reflecting program engagement depth and participant retention.
- **Formula:**
  $$\text{Attendance per Beneficiary} = \frac{\text{Total Attendance Records}}{\text{Distinct Beneficiaries Served}}$$
- **Source Tables:** `attendance` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  ROUND(COUNT(a.attendance_id)::numeric / NULLIF(COUNT(DISTINCT a.beneficiary_id), 0), 2) AS attendance_per_beneficiary
  ```
- **Important Filters:** Standard session logs.
- **Null / Zero Handling:** `NULLIF` prevents division by zero if reach is 0; wrapped in `COALESCE(..., 0.00)` in consolidated KPI views.
- **Traceability Path:**
  Audit query aggregates count of `attendance_id` per `beneficiary_id`.

---

### KPI 4: Total Program Expenditures

- **Business Meaning:** Total operational funds disbursed for a specific program initiative across all expense categories (equipment, stipends, venues, materials).
- **Formula:**
  $$\text{Total Expenses} = \sum \text{expenses.amount}$$
- **Source Tables:** `expenses` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  COALESCE(SUM(e.amount), 0.00) AS total_expenses
  ```
- **Important Filters:** Excludes quarantined negative amounts and unallocated expenses.
- **Null / Zero Handling:** Defaults to `0.00` if no expenses are recorded.
- **Traceability Path:**
  $$\text{Program Expense} \longrightarrow \text{expenses.expense_id} \longrightarrow \text{source_record_id} \longrightarrow \text{expenses.csv row index}$$

---

### KPI 5: Budget Utilization Rate (%)

- **Business Meaning:** Percentage of allocated organizational budget that has been spent. Helps identify under-utilized initiatives or fiscal overruns.
- **Formula:**
  $$\text{Budget Utilization \%} = \left( \frac{\text{Total Program Expenses}}{\text{Budget Allocated}} \right) \times 100$$
- **Source Tables:** `programs` ⟕ `expenses`
- **SQL Calculation:**
  ```sql
  ROUND((COALESCE(e.total_expenses, 0.00) / NULLIF(p.budget_allocated, 0.00)) * 100, 2) AS budget_utilization_pct
  ```
- **Important Filters:** None.
- **Null / Zero Handling:** `NULLIF(p.budget_allocated, 0.00)` guards against zero budget.
- **Traceability Path:**
  Budget originates from `programs.budget_allocated`; spend drills down to individual `expenses` rows.

---

### KPI 6: Cost per Beneficiary Served

- **Business Meaning:** The average financial investment required to reach and serve a single unique community participant.
- **Formula:**
  $$\text{Cost per Beneficiary} = \frac{\text{Total Program Expenses}}{\text{Distinct Beneficiaries Served}}$$
- **Source Tables:** Pre-aggregated `expenses` + pre-aggregated `attendance` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  ROUND(COALESCE(exp.total_expenses, 0.00) / NULLIF(att.beneficiaries_served, 0), 2) AS cost_per_beneficiary
  ```
- **Important Filters:** Only valid, verified beneficiaries with at least one attendance record.
- **Null / Zero Handling:** Returns `NULL` or `0.00` if no beneficiaries have been reached yet.
- **Traceability Path:**
  Combines expense drilldown list with participant drilldown list.

---

### KPI 7: Cost per Beneficiary Contact Hour

- **Business Meaning:** The unit cost per hour of direct community service delivered. Standard metric for comparing high-dosage intensive programs (e.g. coding bootcamps) against broad-reach brief outreach drives.
- **Formula:**
  $$\text{Cost per Beneficiary Hour} = \frac{\text{Total Program Expenses}}{\text{Total Session Hours}}$$
- **Source Tables:** Pre-aggregated `expenses` + pre-aggregated `attendance` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  ROUND(COALESCE(exp.total_expenses, 0.00) / NULLIF(att.total_session_hours, 0.00), 2) AS cost_per_beneficiary_hour
  ```
- **Important Filters:** None.
- **Null / Zero Handling:** `NULLIF(att.total_session_hours, 0.00)` prevents division by zero.
- **Traceability Path:**
  Total spend linked to `expenses.csv`; total hours linked to `attendance.csv`.

---

### KPI 8: Average Outcome Improvement (Score Delta)

- **Business Meaning:** The average points gained by participants on pre/post standardized survey assessments (0 to 100 scale).
- **Formula:**
  $$\text{Average Score Improvement} = \frac{1}{N} \sum (\text{exit\_score} - \text{baseline\_score})$$
- **Source Tables:** `outcomes` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  ROUND(COALESCE(AVG(o.exit_score - o.baseline_score), 0.00), 2) AS avg_improvement
  ```
- **Important Filters:** Excludes out-of-range exit scores (e.g. `145.0` quarantined during Day 2). Rows with missing baseline scores are safely skipped by SQL `AVG()`.
- **Null / Zero Handling:** Defaults to `0.00` if no evaluations exist.
- **Traceability Path:**
  $$\text{Average Improvement} \longrightarrow \text{outcomes.outcome_id} \longrightarrow \text{source_record_id} \longrightarrow \text{outcomes.csv}$$

---

### KPI 9: Outcome Improvement Rate (%)

- **Business Meaning:** The average percentage gain achieved relative to initial baseline competence.
- **Formula:**
  $$\text{Improvement Rate \%} = \text{AVG}\left( \frac{\text{exit\_score} - \text{baseline\_score}}{\text{baseline\_score}} \times 100 \right)$$
- **Source Tables:** `outcomes` ⟕ `programs`
- **SQL Calculation:**
  ```sql
  ROUND(COALESCE(AVG((o.exit_score - o.baseline_score) / NULLIF(o.baseline_score, 0.00)) * 100, 0.00), 2) AS avg_improvement_pct
  ```
- **Important Filters:** `NULLIF(o.baseline_score, 0.00)` prevents division by zero if baseline is zero.
- **Traceability Path:**
  Individual survey evaluation drilldown via `outcome_id`.

---

## 3. Current Live KPI Baseline Outputs

| Program | Category | Budget Allocated | Total Spent | Budget Util | Beneficiaries | Total Hours | Att/Ben | Cost / Ben | Cost / Hour | Eval Count | Baseline Score | Exit Score | Score Gain | % Gain |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **PRG-001** (Digital Literacy) | Education | ₹150,000 | ₹130,311.93 | 86.87% | 42 | 224.0 hrs | 2.93 | ₹3,102.67 | ₹581.75 | 14 | 35.38 | 60.41 | **+25.04** | +85.09% |
| **PRG-002** (Vocational Sewing) | Livelihood | ₹220,000 | ₹182,570.35 | 82.99% | 42 | 217.5 hrs | 2.76 | ₹4,346.91 | ₹839.40 | 6 | 39.62 | 64.50 | **+24.88** | +64.97% |
| **PRG-003** (Youth Coding) | Skill Dev | ₹180,000 | ₹115,177.59 | 63.99% | 43 | 227.5 hrs | 2.63 | ₹2,678.55 | ₹506.28 | 6 | 34.96 | 64.78 | **+31.40** | +95.45% |
| **PRG-004** (Healthcare Outreach)| Healthcare | ₹120,000 | ₹89,977.29 | 74.98% | 44 | 259.0 hrs | 2.91 | ₹2,044.94 | ₹347.40 | 7 | 35.84 | 64.23 | **+28.39** | +83.98% |
| **PRG-005** (Community Nutrition)| Nutrition | ₹95,000 | ₹148,913.20 | 156.75% | 43 | 255.0 hrs | 3.07 | ₹3,463.10 | ₹583.97 | 6 | 42.40 | 64.88 | **+21.75** | +54.16% |

---

## 4. Lineage Drilldown Blueprint

When a user in the future Streamlit dashboard clicks on any aggregate KPI card, the backend executes the corresponding drilldown query:

```
[ High-Level Card: PRG-001 Total Spend: ₹130,311.93 ]
                         │
                         ▼ (Click / Drilldown Query)
[ Underlying Rows: 14 domain records from `expenses` ]
                         │
                         ▼ (Inspect single transaction: EXP-0001 ₹11,271.75)
[ Staging Record: source_record_id = 671, file_id = 4 ]
                         │
                         ▼ (Provenance verification)
[ Raw Origin: Row #1 in expenses.csv | SHA-256: a8814ee9b4205b95... ]
```
