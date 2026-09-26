# TraceImpact — 3-Minute Demo Walkthrough

A structured 3-minute portfolio presentation and spoken script for technical reviewers, recruiters, and engineering interviewers.

**Central Message:**  
*"Not only can the system report a KPI, it can trace that KPI back to the original source record."*

---

## 0:00–0:20 — Problem

### What to show
Open the browser at `http://localhost:8501/` displaying the TraceImpact landing page (`app.py`), highlighting the PostgreSQL connection status and the high-level volume metrics.

### What to say
"Most small nonprofits track their core operations across disconnected spreadsheets—attendance rosters, expense slips, and intake surveys. When grantors ask for an impact report, organizations manually compile numbers into a deck. But the real problem isn't just calculating a KPI; it's answering the audit question: *'Where did this number actually come from?'* TraceImpact was built to solve this by providing traceable impact reporting with verifiable data quality."

### Technical point
Demonstrates the business context: solving spreadsheet fragmentation, unvalidated metrics, and lack of auditability in operational impact reporting.

---

## 0:20–0:45 — Architecture

### What to show
The system architecture flow (or the terminal showing the clean pipeline layout: `src/ingestion`, `src/cleaning`, `sql/views.sql`, and `pages/`).

```
Raw source files (CSV)
       ↓
Raw ingestion (source_files & source_records with JSONB staging)
       ↓
Validation & cleaning (normalizers, schema validators, anomaly quarantine)
       ↓
PostgreSQL relational tables (programs, beneficiaries, attendance, expenses, outcomes)
       ↓
Analytical SQL views (11 views calculating KPIs & DQ aggregations)
       ↓
Data quality observability (severity classification & triage)
       ↓
Streamlit dashboard (5 interactive pages)
       ↓
Source-level traceability (1-to-1 linkage back to raw CSV lines)
```

### What to say
"Here is how the system is engineered. Raw CSV files are first ingested verbatim into PostgreSQL staging tables—preserving the unedited row as JSONB along with a cryptographic SHA-256 file fingerprint. Next, a deterministic cleaning and validation pipeline normalizes dates, locations, and currencies, quarantining blocking errors into a data quality log. Valid records populate relational domain tables, which feed 11 analytical SQL views. Finally, our Streamlit dashboard reads from these views, maintaining a direct foreign-key link from every domain record back to its raw source record."

### Technical point
Explains the ELT/ETL pattern: immutable raw ingestion into JSONB, idempotent data cleansing, analytical database views, and 1-to-1 foreign key lineage.

---

## 0:45–1:20 — Executive Dashboard

### What to show
Navigate to **1 Executive Summary** (`pages/1_Executive_Summary.py`). Point to the metric cards and the live charts.

- **KPI Cards:**
  - `Total Programs`: 5
  - `Total Beneficiaries`: 51
  - `Total Attendance Records`: 612
  - `Total Program Expenses`: ₹666,950.36
  - `Total Outcomes Surveys`: 39
  - `Data Quality Issues`: 177
  - `Issue Resolution Rate`: 84.18%
- **SQL-Backed Visualizations:**
  - Program Reach (`v_program_reach`)
  - Attendance Consistency (`v_attendance_consistency`)
  - Cost per Beneficiary (`v_cost_per_beneficiary`)
  - Outcome Improvement (`v_outcome_improvement`)

### What to say
"Moving to the Executive Summary page, leadership gets a unified view of organization-wide performance. Every card and chart here is powered live by PostgreSQL analytical views rather than static CSV exports. We can see 51 verified beneficiaries across 5 programs, 612 attendance check-ins, and ₹666,950 in total expenses. Down below, our analytical views calculate unit economics—like cost per beneficiary ranging from ₹2,044 up to ₹4,346—and pre/post outcome score improvements between +21 and +31 points. Every aggregation handles division-by-zero safely using SQL `NULLIF` and `COALESCE`."

### Technical point
Highlights analytical SQL view design, pre-aggregated database queries, division safety, and clear separation between application UI and database logic.

---

## 1:20–1:50 — Program Analysis

### What to show
Navigate to **2 Program Analysis** (`pages/2_Program_Analysis.py`).
1. Open the **"Select a Program Initiative to Inspect"** dropdown.
2. Select **`PRG-005: Community Nutrition Drive`**.
3. Point to the budget alert: **"156.75% Budget Utilization (Over Budget)"** (Total Spent: ₹148,913.20 vs Budget: ₹95,000.00).
4. Click through the domain record tabs (**Beneficiaries**, **Attendance**, **Expenses**, **Outcomes**) showing individual records and salted SHA-256 beneficiary identifiers (`BEN-XXXXXXXXXXXX`).

### What to say
"On the Program Analysis page, we can drill down from organization-level numbers to individual initiatives. If we inspect PRG-005, the Community Nutrition Drive, the system immediately surfaces a variance: it is at 156% budget utilization, having spent ₹148,913 against an allocated budget of ₹95,000. Below the scorecard, we can inspect individual domain records across attendance, expenses, and outcomes. Notice that beneficiary records display salted pseudonymized codes, ensuring community privacy while maintaining relational consistency."

### Technical point
Demonstrates parameterized SQL filtering, financial variance monitoring, PII pseudonymization, and interactive multi-table domain exploration.

---

## 1:50–2:15 — Data Quality

### What to show
Navigate to **3 Data Quality** (`pages/3_Data_Quality.py`).
1. Point to the summary cards:
   - `Total Cataloged Issues`: 177
   - `Blocking Errors (Quarantined)`: 10
   - `Non-Blocking Warnings`: 12
   - `Auto-Sanitized Info`: 155
   - `Clean Record Rate`: 98.72%
2. Show the multi-dimensional tabs (`Issues by Source File`, `Issues by Program`, `Issues by Anomaly Type`).
3. Point to the interactive triage filter showing issue types like `DUPLICATE`, `INVALID_FORMAT`, and `MISSING_VALUE`.

### What to say
"Before anyone trusts impact metrics, we have to prove the data is clean. The Data Quality page surfaces our automated observability findings. Out of 177 cataloged issues, 10 critical blocking errors—such as duplicate check-ins or negative expenses—were quarantined so they never corrupt downstream KPI views. 155 informational formatting issues, like non-standard date formats, were automatically normalized. Our Clean Record Rate stands at 98.72%, and users can slice issues by source file, program, severity, or triage status."

### Technical point
Covers automated data validation, severity classification (`ERROR`, `WARNING`, `INFO`), quarantine isolation, and multidimensional defect analysis.

---

## 2:15–2:50 — Traceability

### What to show

Navigate to the Traceability page.

Select:

- Program: `PRG-001: Digital Literacy Initiative`
- Domain Entity: `attendance`
- `source_record_id`: `1` — Attendance `ATT-0001`

Show the four-step lineage:

1. **Domain Table Record**
   - `attendance_id: ATT-0001`
   - `program_id: PRG-001`
   - `session_date: 2024-02-01`
   - `session_hours: 2.00`

2. **JSONB Staging Record**
   - Show the original raw payload captured during ingestion.

3. **Source File Provenance**
   - `attendance.csv`
   - SHA-256 file hash

4. **Physical Source Verification**
   - Live read from `data/raw/attendance.csv`
   - Show the corresponding source row.

### What to say

"This is the key engineering feature of TraceImpact: the system doesn't stop at the cleaned database record.

For this attendance record, we can move from the domain table back to the original JSONB payload captured during ingestion, identify the exact source file, verify its SHA-256 fingerprint, and inspect the corresponding raw CSV record.

So if someone asks where a reported data point came from, we can follow the lineage back to the source instead of relying on an unexplained number."

### Technical point

"TraceImpact implements record-level data lineage using source records, immutable raw staging, source-file provenance, and cryptographic file hashing."

---

## 2:50–3:00 — Closing / Technical Takeaway

### What to show
Return to the main page or display the test suite summary in the terminal (`69 passed in 0.81s`).

### What to say
"To summarize: TraceImpact integrates automated ingestion, data cleaning, relational PostgreSQL modeling, 11 analytical SQL views, automated data-quality scoring, and full audit lineage. 

TraceImpact is designed so that reporting does not stop at the KPI. The system preserves the path back to the underlying source record, making the reported data easier to investigate and trust."

### Technical point
Reiterates the end-to-end data engineering lifecycle: ingestion → validation → SQL modeling → observability → dashboarding → cryptographic auditability.

---

## Bonus / Optional — AI Query Assistant

If time permits, open the AI Query Assistant page (`pages/5_AI_Query_Assistant.py`).

### What to show
Navigate to **5 AI Query Assistant** in the sidebar. Switch to **"Custom Natural-Language Question"** and submit:

> *"Show outcome improvements for Youth Coding Bootcamp."*

Show that the system maps the question to the appropriate approved analytical view (`v_outcome_improvement`) and returns the program-level result.

### What to say
"The assistant is intentionally constrained to approved analytical queries and read-only database access rather than allowing arbitrary SQL execution."

### Technical point
Demonstrates safe, constrained natural-language querying grounded strictly in pre-verified analytical database views with read-only query execution.

---

## TraceImpact 2.0 Walkthrough — Public Data Explorer, ML Anomaly Detection & AI Investigation

For interviews or technical presentations focusing on **TraceImpact 2.0**:

### What to show
Navigate to **6 Public Data Explorer** (`pages/6_Public_Data_Explorer.py`).

1. **Dual Domain Architecture**:
   - Highlight the banner: World Bank Public API domain is completely separate from the synthetic nonprofit operational database.
   - Point to the live KPIs: 264 Countries, 4 Global Indicators, 5,588 Verified Observations (2018–2025).

2. **Automated Ingestion & SHA-256 Provenance**:
   - Show the Ingestion Execution History table (`api_ingestion_runs`) with automated daily scheduler status, duration (e.g. 1.84s), and record upsert counts.
   - Show the 1-to-1 Public API Lineage trace: drill down into any country-year observation to inspect the verbatim JSON array record and its 64-character SHA-256 response hash.

3. **Machine Learning Anomaly Detection (Isolation Forest)**:
   - Scroll to the ML Anomaly Detection section.
   - Show active model: `IsolationForest_WorldBank (v1.0.0)` trained on multi-year Z-scores and YoY growth features with 4.0% baseline contamination.
   - Display the sorted table of 224 statistical anomalies with anomaly decision scores.

4. **AI-Assisted Investigation & Grounded Insights**:
   - Select an anomaly (e.g. *Central African Republic 2019: Life expectancy at birth contraction*).
   - Click **"🔍 Investigate Anomaly"**.
   - Show the grounded structured finding:
     - Exact Z-Score (-1.60) and historical baseline comparison.
     - Co-occurring contextual indicators (e.g. GDP per capita, Drinking Water Access for that country and year).
     - Clear segregation of **FACTS** from **POTENTIAL INTERPRETATIONS**.
     - Explicit **NON-CAUSALITY NOTICE** stating observational data cannot prove causal attribution.
   - Show the 7-step source-to-insight lineage trace: Insight ➔ Investigation ➔ Anomaly ➔ Observation ➔ Bronze JSONB ➔ SHA-256 Hash ➔ Run ID.

### What to say
"In TraceImpact 2.0, we expand beyond internal CSV files to real-world REST APIs, automated scheduling, machine learning anomaly detection, and grounded AI investigations. Every AI explanation is anchored in statistical feature baselines and verified PostgreSQL records, preserving complete lineage back to the immutable SHA-256 hashed API payload."

