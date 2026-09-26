# TRACEIMPACT — FINAL DAY 1–6 PROJECT BASELINE

**Document Version:** 1.0.0  
**Baseline Date:** 2026-09-26  
**Status:** Verified & Frozen Baseline  
**Workspace:** `/Users/shashwat/Desktop/project1`  

> "Days 1–6 are considered verified and frozen as the baseline for Day 7."

---

## 1. Project Overview

**TraceImpact** is a data engineering, data quality observability, and impact reporting platform designed specifically for small-to-medium nonprofit organizations and grant-making foundations. 

### Core Problem Solved
Nonprofits typically rely on fragmented, messy operational datasets (spreadsheets, attendance logs, receipts, surveys). When compiling reports for donors or auditors, traditional data pipelines discard dirty data, apply non-transparent deduplications, and break the lineage between aggregate Key Performance Indicators (KPIs) and the original source files. TraceImpact solves this by providing:
1. **Verbatim Ingestion & Immutability:** Raw CSV files are preserved byte-for-byte; initial ingestion stores raw records as JSONB with SHA-256 cryptographic fingerprints.
2. **Defensible Data Quality Observability:** Anomaly detection catalogs errors, warnings, and missing values into an auditable issue log rather than silently dropping or modifying data.
3. **Audited Transformation:** Normalized, cleaned domain tables with PII protection via salted SHA-256 pseudonymization.
4. **Reliable Analytics:** PostgreSQL views calculated via non-multiplying Common Table Expressions (CTEs) and safe division.
5. **Interactive Exploration:** Multi-page Streamlit application powered directly by database views without frontend metric fabrication.
6. **1-to-1 Cryptographic Traceability:** End-to-end lineage enabling click-through drilldown from any high-level dashboard KPI back to the exact physical CSV row on disk.

---

## 2. Technology Stack

- **Language:** Python 3.14.7
- **Database Engine:** PostgreSQL 16+
- **Database ORM & Driver:** SQLAlchemy 2.0, Psycopg2-binary
- **Data Manipulation:** Pandas 2.2+
- **Interactive Web Presentation:** Streamlit 1.64+
- **Data Visualizations:** Plotly / Altair
- **Environment & Configuration:** Python-Dotenv
- **Testing Framework:** Pytest 9.1+
- **Synthetic Data Generation:** Faker

---

## 3. Day 1 Implementation (Foundation & Raw Staging)

- **Repository Structure:** Modular layout separating `data/`, `sql/`, `src/`, `pages/`, `docs/`, and `tests/`.
- **Relational DDL (`sql/schema.sql`):** 8-table relational schema establishing Lineage/Audit tables (`source_files`, `source_records`, `data_quality_issues`) and Normalized Domain tables (`programs`, `beneficiaries`, `attendance`, `expenses`, `outcomes`).
- **ORM Models (`src/database/models.py`):** Fully typed SQLAlchemy models mapping foreign key constraints and JSONB column types.
- **Raw Datasets (`data/raw/`):** 5 synthetic datasets (784 rows total) modeled with realistic real-world flaws:
  - `programs.csv` (5 rows)
  - `beneficiaries.csv` (52 rows)
  - `attendance.csv` (618 rows)
  - `expenses.csv` (69 rows)
  - `outcomes.csv` (40 rows)
- **Ingestion Engine (`src/ingestion/`):** Computes SHA-256 hashes, registers files in `source_files`, and stages raw records into `source_records` as immutable JSONB with exact `row_index`. Master programs seeded directly.
- **Verification:** 5/5 automated unit tests in `tests/test_day1.py` passing.

---

## 4. Day 2 Implementation (Cleaning, Validation & Domain Loading)

- **Non-Destructive Cleaning Engine (`src/cleaning/`):**
  - `clean_beneficiaries.py`: PII pseudonymization via salted SHA-256 (`anonymized_code`), casing normalization, duplicate detection.
  - `clean_attendance.py`: Multi-format date normalization (`YYYY-MM-DD`, `DD/MM/YYYY`, text dates), duplicate session check-in detection, foreign reference validation.
  - `clean_expenses.py`: Currency symbol sanitization (`₹`, `,`), negative amount detection, missing program code handling.
  - `clean_outcomes.py`: Numeric parsing, out-of-bounds score detection (`[0.0, 100.0]`), missing baseline score logging.
- **Data Quality Audit Log (`data_quality_issues`):** Cataloged 177 distinct anomalies across ERROR, WARNING, and INFO severities without dropping records.
- **Domain Tables Loaded:** Populated clean business tables with `source_record_id` foreign keys linking back to `source_records(record_id)`.
- **Processed Exports (`data/processed/`):** Clean CSV files exported to disk.
- **Verification:** 14/14 automated unit tests in `tests/test_day2.py` passing. Raw data files confirmed 100% immutable.

---

## 5. Day 3 Implementation (SQL Analytics & KPI Views)

- **SQL Analytical Views (`sql/views.sql`):** 6 production views deployed to PostgreSQL:
  1. `v_program_reach`: Unique beneficiaries served, total attendance records, and total contact hours.
  2. `v_attendance_consistency`: Sessions per beneficiary and average session duration.
  3. `v_cost_per_beneficiary`: Allocated budget, total expenditures, budget utilization percentage, and cost per person.
  4. `v_cost_per_beneficiary_hour`: Cost per attendee-hour delivered.
  5. `v_outcome_improvement`: Baseline vs. exit evaluation averages, absolute score improvement, and percentage improvement.
  6. `v_program_kpis`: Master consolidated 16-metric scorecard per program.
- **Key Architectural Guardrails:**
  - CTE pre-aggregation eliminates Cartesian row multiplication across 1-to-many relationships.
  - `NULLIF(..., 0)` protects against division-by-zero errors.
- **Verification:** 8/8 automated unit tests in `tests/test_day3.py` passing.

---

## 6. Day 4 Implementation (Data Quality Scorecard & Triage)

- **Quality Scorecard Views (`sql/views_quality.sql`):** 5 production views deployed to PostgreSQL:
  1. `v_data_quality_summary`: Overall system metrics (177 issues, 98.72% clean record rate, 84.18% resolution rate).
  2. `v_data_quality_by_file`: Anomaly counts and severity breakdown per source file.
  3. `v_data_quality_by_program`: Anomaly counts per program, explicitly preserving unassigned/org-level issues (17 rows).
  4. `v_data_quality_by_type`: Breakdown across anomaly categories (`MISSING_VALUE`, `INVALID_FORMAT`, `DUPLICATE`, `INVALID_NUMBER`, `UNMATCHED_REFERENCE`).
  5. `v_data_quality_blocking`: Quarantined blocking ERROR records (10 critical items).
- **Triage Service (`src/quality/triage.py`):** Status lifecycle engine (`OPEN`, `RESOLVED`, `ACCEPTED`) and Data Reliability Scoring Index (94.94 / 100).
- **Verification:** 11/11 automated unit tests in `tests/test_day4.py` passing.

---

## 7. Day 5 Implementation (Streamlit Dashboard)

- **Application Architecture (`app.py`, `src/dashboard/`):**
  - `db.py`: Thread-safe connection pooling reusing engine connection logic.
  - `queries.py`: Centralized SQL query layer returning typed dictionaries and structured DataFrames.
  - `formatting.py` & `components.py`: Standardized INR formatting, percentage rounding, and UI cards.
- **Delivered Pages:**
  - **Portal Overview (`app.py`):** System health probe, architectural data flow, platform volumes.
  - **1. Executive Summary (`pages/1_Executive_Summary.py`):** 8 KPI summary cards, 5 visual charts.
  - **2. Program Analysis (`pages/2_Program_Analysis.py`):** Dynamic program selector, 12-metric KPI scorecard, 4-domain tabbed explorer, program-specific DQ log.
  - **3. Data Quality (`pages/3_Data_Quality.py`):** Executive quality overview, breakdowns by file/program/type, interactive multi-select triage table.
- **Zero Fabrication:** 100% of displayed metrics are drawn from PostgreSQL views.
- **Verification:** 11/11 automated unit tests in `tests/test_day5.py` passing.

---

## 8. Day 6 Implementation (Traceability Drilldown UI)

- **Traceability Page (`pages/4_Traceability.py`):**
  - Universal record search by `source_record_id` or quick entity selection across Beneficiaries, Attendance, Expenses, Outcomes, or Data Quality Issues.
  - Interactive 4-step visual lineage flow: KPI ➔ Domain Record ➔ Staging Record (JSONB) ➔ Physical Source CSV.
- **Verification Proof Engine (`src/dashboard/queries.py`):**
  - `get_traceability_record(record_id)`: Fetches staging metadata, discovers parent source file, joins attached domain records, and finds related DQ issues.
  - `get_physical_csv_row(file_name, row_index)`: Directly reads the exact row from `data/raw/<file_name>` at 1-based `row_index` on disk to confirm live CSV matches JSONB verbatim.
  - Quarantined record handling: Validates that uncleaned/duplicate records exist in staging/issues but are omitted from domain tables.
- **Verification:** 9/9 automated unit tests in `tests/test_day6.py` passing.

---

## 9. Current Database Counts

All table row counts verified in live PostgreSQL (`traceimpact`):

| Table Name | Actual Count | Description |
|------------|--------------|-------------|
| `source_files` | **5** | Ingested raw files with SHA-256 hashes |
| `source_records` | **784** | Raw records staged as JSONB |
| `programs` | **5** | Master organization programs |
| `beneficiaries` | **51** | Cleaned, deduplicated community members |
| `attendance` | **612** | Validated session check-in events |
| `expenses` | **67** | Validated operational expenditures |
| `outcomes` | **39** | Validated pre/post outcome evaluations |
| `data_quality_issues` | **177** | Cataloged anomalies and data defects |

---

## 10. Current SQL Views

### Analytical Views (Day 3 — `sql/views.sql`)
1. `v_program_reach` (5 rows)
2. `v_attendance_consistency` (5 rows)
3. `v_cost_per_beneficiary` (5 rows)
4. `v_cost_per_beneficiary_hour` (5 rows)
5. `v_outcome_improvement` (5 rows)
6. `v_program_kpis` (5 rows)

### Data Quality Scorecard Views (Day 4 — `sql/views_quality.sql`)
1. `v_data_quality_summary` (1 row)
2. `v_data_quality_by_file` (4 rows)
3. `v_data_quality_by_program` (6 rows, including `UNASSIGNED`)
4. `v_data_quality_by_type` (5 rows)
5. `v_data_quality_blocking` (10 rows)

---

## 11. Current Data-Quality Metrics

- **Total Cataloged Issues:** 177
- **Severity Distribution:**
  - `ERROR`: 10 (5.65%) — Blocking defects quarantined from domain tables
  - `WARNING`: 12 (6.78%) — Format/completeness warnings (e.g. missing baseline scores)
  - `INFO`: 155 (87.57%) — Minor non-blocking observations (e.g. standardized casing)
- **Status Breakdown:**
  - `OPEN`: 28 (15.82%)
  - `RESOLVED`: 149 (84.18%)
  - `ACCEPTED`: 0 (0.00%)
- **Data Reliability Index (DRI):** 94.94 / 100
- **Clean Record Rate:** 98.72%
- **Issue Resolution Rate:** 84.18%

---

## 12. Current Streamlit Pages

1. `app.py`: Platform overview, live database connectivity health check, platform volume cards.
2. `pages/1_Executive_Summary.py`: Portfolio-level KPI cards and 5 visual analytics charts.
3. `pages/2_Program_Analysis.py`: Program-level dropdown selector, 12-KPI scorecard, budget utilization monitor, 4-domain tabbed explorer, and program anomaly log.
4. `pages/3_Data_Quality.py`: Observability scorecard, file/program/type distributions, and multi-filter interactive triage table.
5. `pages/4_Traceability.py`: 1-to-1 drilldown proof engine connecting dashboard KPIs to domain records, JSONB staging, SHA-256 hashes, and physical disk CSV rows.

---

## 13. Current Traceability Architecture

```
Dashboard KPI / Report
        │
        ▼
PostgreSQL Analytical View (`v_program_reach`, `v_program_kpis`)
        │
        ▼
Domain Table Row (`attendance`, `expenses`, `beneficiaries`, `outcomes`)
        │ [Foreign Key: source_record_id]
        ▼
Raw Staging Table (`source_records`)
        │ [Stores verbatim raw_data as JSONB]
        │ [Stores exact row_index coordinate]
        │ [Foreign Key: file_id]
        ▼
File Provenance Table (`source_files`)
        │ [Stores SHA-256 cryptographic fingerprint]
        │ [Stores ingestion timestamp & total row count]
        ▼
Physical Raw CSV on Local Disk (`data/raw/<filename>`)
        [Exact row index read-only verification]
```

### Verified Concrete Examples:
- **Beneficiaries:** `BEN-001` ➔ `source_record_id: 619` ➔ `source_records.record_id: 619` ➔ `beneficiaries.csv` (Row 1)
- **Attendance:** `ATT-0001` ➔ `source_record_id: 1` ➔ `source_records.record_id: 1` ➔ `attendance.csv` (Row 1)
- **Expenses:** `EXP-0001` ➔ `source_record_id: 671` ➔ `source_records.record_id: 671` ➔ `expenses.csv` (Row 1)
- **Outcomes:** `SURV-0001` ➔ `source_record_id: 740` ➔ `source_records.record_id: 740` ➔ `outcomes.csv` (Row 1)
- **DQ Issue:** `issue_id: 352` ➔ `record_id: 765` ➔ `source_records.record_id: 765` ➔ `outcomes.csv` (Row 26)

---

## 14. Test Suite

Automated execution via `.venv/bin/python -m pytest -v`:

- **Day 1 Tests:** 5 passed (`tests/test_day1.py`)
- **Day 2 Tests:** 14 passed (`tests/test_day2.py`)
- **Day 3 Tests:** 8 passed (`tests/test_day3.py`)
- **Day 4 Tests:** 11 passed (`tests/test_day4.py`)
- **Day 5 Tests:** 11 passed (`tests/test_day5.py`)
- **Day 6 Tests:** 9 passed (`tests/test_day6.py`)
- **Total Tests:** 58
- **Passed:** 58
- **Failed:** 0
- **Skipped:** 0

Execution duration: 0.93 seconds. 100% pass rate.

---

## 15. Raw-File SHA-256 Integrity Status

All 5 raw source CSV files verified byte-for-byte identical to their Day 1 ingestion hashes:

| File Name | Disk SHA-256 Hash | Database `file_hash` | Status |
|-----------|-------------------|----------------------|--------|
| `programs.csv` | `ccdf5dc63cf05eb443c2a114df8af2f0055b2a33b0e0ce6f0cc80e4d634a5342` | `ccdf5dc63cf05eb443c2a114df8af2f0055b2a33b0e0ce6f0cc80e4d634a5342` | **MATCH (Unchanged)** |
| `beneficiaries.csv` | `9f85761c4c83d884bdab7c22c44c8eac588a481e0bb219a63ee10834b1f87166` | `9f85761c4c83d884bdab7c22c44c8eac588a481e0bb219a63ee10834b1f87166` | **MATCH (Unchanged)** |
| `attendance.csv` | `c35bcf948c31d0aa983eec40da2ede332f279022f4ec007534e6802269fe7444` | `c35bcf948c31d0aa983eec40da2ede332f279022f4ec007534e6802269fe7444` | **MATCH (Unchanged)** |
| `expenses.csv` | `a8814ee9b4205b95f6fb635dd4bc3d9d3402c51a601be9c9287343e01f208bfa` | `a8814ee9b4205b95f6fb635dd4bc3d9d3402c51a601be9c9287343e01f208bfa` | **MATCH (Unchanged)** |
| `outcomes.csv` | `bf28a6e69d9071d899b750a574abd5c40c99574ec36796a02f704d5eea540213` | `bf28a6e69d9071d899b750a574abd5c40c99574ec36796a02f704d5eea540213` | **MATCH (Unchanged)** |

---

## 16. Security Status

- **Database Credentials:** Loaded from environment variables via `.env`; no plaintext passwords committed.
- **Git Exposure:** `.env`, `.venv/`, `__pycache__/`, and `.pytest_cache/` are verified untracked and excluded in `.gitignore`.
- **UI Sanitization:** Streamlit UI displays sanitized database connection metadata (host, database, user); passwords and secret keys are never rendered.
- **SQL Injection Prevention:** 100% of database queries in `src/dashboard/queries.py` and `src/quality/triage.py` use parameterized SQLAlchemy `:bind` variables.
- **Beneficiary PII Protection:** Beneficiary names and phone numbers are isolated; public and dashboard records expose only salted SHA-256 `anonymized_code`.

---

## 17. Performance Status

- **Query Execution:** Pre-aggregated SQL views execute in sub-15ms on PostgreSQL.
- **Selective Retrieval:** Single-record lookups and paginated queries (`LIMIT :limit`) prevent full-table in-memory overhead.
- **Connection Management:** Scoped connection pool ensures threads check out and return connections cleanly.
- **Test Suite Speed:** All 58 automated tests complete in under 1 second (0.93s).

---

## 18. Documentation Status

All primary project documentation is verified and synchronized:
- `README.md`: System overview, setup guide, architecture flow, and execution instructions.
- `docs/PROJECT_STATUS.md`: Comprehensive milestone audit through Day 6.
- `docs/POST_DAY_5_6_REVIEW.md`: Complete independent read-only review report.
- `docs/DATA_PIPELINE.md`: Pipeline architecture, cleaning rules, and schema definitions.
- `docs/KPI_DEFINITIONS.md`: Metric formulas, business logic, and lineage catalog.
- `docs/DATA_QUALITY_SCORECARD.md`: Quality views, severity guidelines, and scoring methodology.
- `docs/DASHBOARD.md`: Streamlit dashboard architecture, page guides, and component layers.
- `docs/TRACEABILITY.md`: Cryptographic lineage specifications and audit walkthrough.

---

## 19. Known Observations

1. **Git Staging:** Day 4–6 implementation files (`pages/`, `src/dashboard/`, `src/quality/`, `tests/test_day4.py`, `tests/test_day5.py`, `tests/test_day6.py`, docs) are currently untracked working-tree items and need final staging and commit upon milestone completion.
2. **Day 7 Polish:** Final portfolio packaging, architectural diagrams, and executive demo script remain to be assembled during Day 7.
3. **AI Q&A Assistant:** Natural-language query assistant / SQL explainer remains an optional Day 7 enhancement.

---

## 20. Day 7 Starting Point

With Days 1 through 6 frozen and verified:
- **Baseline Branch:** `main`
- **Starting Command:** `.venv/bin/streamlit run app.py`
- **Scope for Day 7:**
  1. Build optional AI Natural-Language Query Assistant / SQL explainer grounded on existing views.
  2. Assemble comprehensive 3-minute executive demo script.
  3. Create final portfolio architectural diagrams and visual assets.
  4. Perform final git commit of all verified milestone deliverables.
