# TraceImpact — Streamlit Dashboard Architecture & User Guide

**Document Version:** 1.0.0  
**Status:** Production Ready  
**Milestone:** Day 5 Completed  

---

## 1. Application Overview & Architecture

The **TraceImpact Streamlit Dashboard** serves as the executive and operational presentation layer over the PostgreSQL data platform. It avoids brittle frontend calculations by delegating all aggregations directly to Day 3 SQL Analytics Views and Day 4 Data Quality Views.

```
PostgreSQL Database (`traceimpact`)
  ├── Day 3 Views: v_program_reach, v_attendance_consistency, v_cost_per_beneficiary, v_outcome_improvement, v_program_kpis
  └── Day 4 Views: v_data_quality_summary, v_data_quality_by_file, v_data_quality_by_program, v_data_quality_by_type, v_data_quality_blocking
          │
          ▼
Data Access Layer (`src/dashboard/queries.py`)
  ├── Uses thread-safe connection pooling from `src.database.connection`
  └── Returns typed dictionaries and structured Pandas DataFrames
          │
          ▼
Formatting & Presentation (`src/dashboard/formatting.py`, `src/dashboard/components.py`)
  └── Standardizes INR currency (`₹`), percentages, number rounding, and status badges
          │
          ▼
Streamlit Multi-Page UI (`app.py`, `pages/`)
  ├── app.py: Portal & System Health Overview
  ├── 1_Executive_Summary.py: Portfolio KPIs & Visualizations
  ├── 2_Program_Analysis.py: Individual Initiative Drilldowns & Domain Records
  ├── 3_Data_Quality.py: Observability Scorecard & Anomaly Triage
  └── 4_Traceability.py: Cryptographic 1-to-1 Raw CSV Lineage Explorer
```

---

## 2. Dashboard Pages & Capabilities

### Page 1: Portal Overview (`app.py`)
- Platform introduction and architectural data flow.
- Real-time PostgreSQL health probe (`check_db_health()`).
- High-level platform volume metrics (Programs, Beneficiaries, Attendance, Expenses, Outcomes).
- Guided navigation cards.

### Page 2: Executive Summary (`pages/1_Executive_Summary.py`)
- **Executive Metric Cards**: Total Programs (5), Beneficiaries (51), Attendance (612), Expenses (₹666,950.36), Outcomes (39), Cataloged Issues (177), Open Items (28), Resolution Rate (84.18%).
- **5 Core Visualizations**:
  1. *Program Reach*: Unique community members engaged per initiative (`v_program_reach`).
  2. *Attendance Consistency*: Average check-ins per participant and total contact hours (`v_attendance_consistency`).
  3. *Cost per Beneficiary*: Capital efficiency per person served (`v_cost_per_beneficiary`).
  4. *Outcome Improvement*: Baseline vs. exit evaluation score gains (`v_outcome_improvement`).
  5. *Data Quality Severity*: Proportions of ERROR (5.6%), WARNING (6.8%), and INFO (87.6%).

### Page 3: Program Analysis (`pages/2_Program_Analysis.py`)
- Dynamic program selector populated live from PostgreSQL `programs` table.
- Scorecard KPI breakdown from `v_program_kpis` (12 metrics spanning reach, economics, and outcomes).
- Budget utilization metric with automated over/under status indicators (highlights PRG-005 over-budget finding).
- **Tabbed Domain Record Explorer**:
  - Participating Beneficiaries (with salted SHA-256 `anonymized_code`).
  - Attendance check-in logs.
  - Expense line items with receipt verification flags.
  - Outcome evaluation surveys with score gains.
- Program-specific anomaly log with direct links to `source_record_id`.

### Page 4: Data Quality Scorecard (`pages/3_Data_Quality.py`)
- Complete data health scorecard from `v_data_quality_summary`.
- Three analytical breakdown tabs: By File, By Program, and By Anomaly Type.
- **Interactive Multi-Parameter Filter**:
  - Filter simultaneously by Severity (`ERROR`, `WARNING`, `INFO`), Status (`OPEN`, `RESOLVED`, `ACCEPTED`), Issue Type, Source File, and Program.
- Comprehensive audit table with exact row coordinates and error descriptions.

---

## 3. Database Connection & Caching Design

1. **Security**: Database credentials are loaded securely via `python-dotenv` from `.env`. No credentials or connection strings are hardcoded in UI scripts.
2. **Resource Management**: Sessions are managed using context managers (`with get_db() as db:`), ensuring connections are immediately returned to the pool after query execution.
3. **Resilience**: If PostgreSQL is down, a user-friendly alert banner is displayed (`render_db_error()`) rather than leaking Python stack traces to non-technical users.

---

## 4. How to Launch and Operate

```bash
# 1. Activate environment
source .venv/bin/activate

# 2. Run Streamlit server
streamlit run app.py

# 3. View in browser
http://localhost:8501
```
