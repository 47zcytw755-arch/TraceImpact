# TraceImpact 2.0 — Long-Term Technical Memory & Repository Facts

> **Document Version:** 2.0.0  
> **Status:** ACTIVE REPOSITORY REFERENCE  
> **Security Notice:** Contains stable architectural facts, schemas, and design constraints. Contains ZERO passwords, API keys, or private credentials.

---

## 1. Project Identity & Purpose

- **Project Name:** TraceImpact (Version 2.0.0)
- **Repository Path:** `/Users/shashwat/Desktop/project1`
- **Core Purpose:** A defensible, portfolio-scale data engineering and intelligence platform combining non-destructive CSV ingestion, live World Bank public data pipelines, unsupervised machine learning anomaly detection, grounded AI investigations, and 1-to-1 cryptographic lineage.
- **Key Philosophy:** "A reported number must have an explainable, unbroken data provenance path back to the physical record that produced it."

---

## 2. Current Architecture & Technologies

- **Language:** Python 3.10+
- **Database Backend:** PostgreSQL 14+ (`localhost:5432`, dbname: `traceimpact`, user: `postgres`)
- **Data Engineering Libraries:** Pandas 2.2+, SQLAlchemy 2.0+, Psycopg2-binary 2.9+, Requests 2.31+
- **Machine Learning:** Scikit-Learn 1.4+ (`IsolationForest`), Joblib 1.3+
- **Interactive UI:** Streamlit 1.32+ (Multi-page app on port 8501)
- **BI Layer:** Power BI Desktop & Web (Direct PostgreSQL M scripts, DAX library, 9-page semantic model)
- **Testing:** Pytest 8.0+ (94 passing automated tests)

---

## 3. Database Schema & Object Catalog

### Staging & Provenance Tables (Bronze)
- `source_files`: File metadata (`file_id`, `file_name`, `file_hash` SHA-256, `total_rows`, `ingested_at`).
- `source_records`: Verbatim CSV row staging (`record_id`, `file_id`, `row_index`, `raw_data` JSONB).
- `api_ingestion_runs`: Execution logs (`run_id`, `source_name`, `endpoint_url`, `status`, `duration_seconds`).
- `api_raw_responses`: Verbatim API page staging (`response_id`, `run_id`, `page_number`, `response_hash` SHA-256, `raw_payload` JSONB).

### Normalized Domain Tables (Silver)
- `programs`: Master program registry (`program_id` `PRG-001`–`PRG-005`, `program_name`, `target_category`, `budget_allocated`).
- `beneficiaries`: Participant records (`beneficiary_id`, `source_record_id` FK, `anonymized_code`, `city_location`, `registration_date`).
- `attendance`: Session check-ins (`attendance_id`, `source_record_id` FK, `beneficiary_id` FK, `program_id` FK, `session_hours`).
- `expenses`: Expense vouchers (`expense_id`, `source_record_id` FK, `program_id` FK, `amount`, `receipt_verified`).
- `outcomes`: Pre/post survey evaluations (`outcome_id`, `source_record_id` FK, `beneficiary_id` FK, `program_id` FK, `baseline_score`, `exit_score`).
- `world_bank_countries`: Sovereign country dimension (`country_code`, `iso3_code`, `country_name`, `region`, `income_level`).
- `world_bank_indicators`: Indicator catalog (`indicator_code`, `indicator_name`, `topic`, `unit_of_measure`).
- `world_bank_observations`: Clean public time-series (`observation_id`, `country_code`, `indicator_code`, `year`, `indicator_value`).

### Data Quality & Intelligence Tables
- `data_quality_issues`: Audit trail of synthetic data anomalies (177 issues, 10 `ERROR`, 12 `WARNING`, 155 `INFO`).
- `world_bank_data_quality_issues`: Audit trail of public data notices (722 missing historical values logged `INFO`).
- `ml_anomaly_models`: Model registry (`model_id`, `model_name`, `model_version`, `hyperparameters`, `metrics_summary`).
- `world_bank_anomalies`: Anomaly scores & feature snapshots (783 flagged anomalies, continuous score -0.50 to +0.50).
- `ai_investigations`: Grounded investigation reports (6 investigations with structured evidence JSONB).
- `ai_insights`: Actionable insight bulletins (33 structured insight entries).

### Core PostgreSQL Analytical Views (Gold)
- `v_program_reach`: Unique participants and attendance session hours per program.
- `v_attendance_consistency`: Session density and average hours per participant.
- `v_cost_per_beneficiary`: Cost efficiency ratios per program.
- `v_outcome_improvement`: Baseline vs exit survey scores and percentage improvement.
- `v_program_kpis`: Master 16-metric rollup per program.
- `v_data_quality_summary`: Quality scorecard and clean record percentages.
- `v_data_quality_blocking`: Quarantined blocking errors (`severity = 'ERROR'`).
- `v_world_bank_latest_indicators`: Most recent indicator value per country via `DISTINCT ON`.
- `v_world_bank_country_trends`: Multi-year trends with YoY change via `LAG()`.
- `v_world_bank_regional_comparison`: Regional indicator averages across continents.
- `v_world_bank_ai_lineage`: 7-step cryptographic lineage view from AI insight to API raw hash.
- `v_pbi_*` (9 Views): Dedicated views optimized for Power BI reporting.

---

## 4. Key Performance & Volume Statistics

- **Synthetic Records Staged:** 784 rows across 5 CSV files.
- **Synthetic Clean Record Rate:** 98.72% (774 clean / 10 quarantined errors).
- **World Bank Observations Stored:** 5,588 country-year records across 264 countries (1960–2024).
- **World Bank Clean Observation Rate:** 100.0% (Missing historical values logged gracefully as `INFO`).
- **Isolation Forest Anomalies Flagged:** 783 anomalies (14.01% anomaly rate).
- **AI Investigations & Insights:** 6 Grounded Investigations, 33 Published Insights.
- **Automated Ingestion Executions:** 67 API Runs with 100% success rate.
- **100K Stress Test Throughput:** 100,000 records processed in 5.23s at 19,120 RPS (Peak RAM: 416.64 MB).
- **Automated Test Suite:** 94/94 Passing Tests (Execution time: ~2.0 seconds).

---

## 5. Important Design Decisions & Invariants

1. **Raw Staging Immutability:** Raw CSV files in `data/raw/` are NEVER altered. All staging happens in `source_records`.
2. **PII Pseudonymization:** Community member full names and phone numbers are never exposed in domain tables or dashboards; they are hashed into `anonymized_code` using salted SHA-256.
3. **Cartesian Product Elimination:** Analytical views pre-aggregate child tables in CTEs before joining on `program_id`.
4. **Division Safety:** All ratios use `NULLIF(denominator, 0)`.
5. **Read-Only AI SQL:** The AI query assistant enforces a strict token filter (`SELECT` / `WITH` only) and an approved Gold view whitelist.
6. **Strict Non-Causality Boundary:** Isolation Forest anomaly scores and AI insights describe statistical divergence; they NEVER claim to prove real-world causality.

---

## 6. Known Limitations & Technical Boundaries

1. **Single-Node Database:** Current implementation uses a single PostgreSQL instance; does not use distributed partitioning.
2. **Unsupervised ML Scope:** Isolation Forest detects statistical divergence from historical peer baselines; it cannot differentiate between real-world policy shifts and reporting methodology revisions without human review.
3. **AI Grounding Boundary:** The AI investigation engine is strictly constrained to pre-computed database evidence; it cannot provide context for external geopolitical events not captured in the database.
4. **Lineage Scope:** Lineage traces digital provenance (SHA-256 hashes and database foreign keys); it does not prove physical ground truth.

---

## 7. Essential Commands for Future Agents

```bash
# Activate virtual environment
source .venv/bin/activate

# Execute complete 94-test regression suite
python -m pytest tests/ -v

# Run synthetic data cleaning pipeline
python -m src.cleaning.run_pipeline

# Run single scheduled World Bank ingestion pass
python -m src.ingestion.scheduler --once

# Train Isolation Forest & detect ML anomalies
python -m src.ml.anomaly_detector

# Execute AI investigation engine
python -m src.ai.investigator

# Validate all Power BI measures against PostgreSQL
python -m src.power_bi_validator

# Launch Streamlit portal
streamlit run app.py --server.port 8501
```
