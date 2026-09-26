# TraceImpact — Traceable Impact Reporting & Data Quality Platform

TraceImpact is a data engineering and data quality platform tailored for small nonprofit organizations. It imports fragmented, messy operational datasets (spreadsheets, attendance sheets, financial logs, surveys), catalogs data quality issues, maintains strict data immutability and lineage, and enables transparent, traceable impact reporting.

---

## 1. Architecture & Data Flow (Medallion-Style)

```
Raw CSV Datasets (data/raw/) [Immutable]
         │
         ▼
Raw Ingestion Engine (Day 1: Pandas + SHA-256 Hashing)
         │
         ▼
PostgreSQL Staging (`source_files`, `source_records` JSONB)
         │
         ├─────────────────────────────────────────┐
         ▼                                         ▼
Data Quality Audit (Day 2)                Data Cleaning & Normalization (Day 2)
(`data_quality_issues`)                   (`beneficiaries`, `attendance`, `expenses`, `outcomes`)
                                                   │
                                                   ▼
                                        SQL Analytics & KPI Views (Day 3)
                                        (`v_program_reach`, `v_cost_per_beneficiary`, `v_program_kpis`)
                                                   │
                                                   ▼
                                        Streamlit Impact Dashboard (Day 5)
```

---

## 2. Technology Stack

- **Language:** Python 3.14+
- **Data Manipulation:** Pandas
- **Database:** PostgreSQL (Relational schema + JSONB staging)
- **Database ORM & Driver:** SQLAlchemy 2.0, Psycopg2-binary
- **Configuration:** Python-Dotenv
- **Synthetic Data & Testing:** Faker, Pytest

---

## 3. Database Schema Overview

The database uses an 8-table design split into **Lineage & Audit Metadata** and **Normalized Core Entities**:

### A. Lineage & Audit Metadata
1. **`source_files`**: Tracks file metadata, ingestion timestamps, and SHA-256 hashes to guarantee raw data provenance and immutability.
2. **`source_records`**: Immutable raw staging table storing JSONB records linked to `source_files(file_id)` and original `row_index`.
3. **`data_quality_issues`**: Audit log recording anomalies (`issue_type`, `severity`, `raw_value`, `description`, `status`).

### B. Normalized Domain Entities
4. **`programs`**: Master organization programs and budget allocations.
5. **`beneficiaries`**: Community members served, including `anonymized_code` for PII protection.
6. **`attendance`**: Fact table recording session attendances, linking beneficiaries to programs.
7. **`expenses`**: Fact table tracking operational expenditures by category and program.
8. **`outcomes`**: Fact table evaluating pre- and post-intervention scores.

---

## 4. Synthetic Datasets & Intentional Flaws

Located in `data/raw/` (treated as strictly immutable):

| Dataset | Row Count | Intentional Real-World Flaws Included |
|---|---|---|
| `programs.csv` | 5 | Master baseline program data. |
| `beneficiaries.csv` | 52 | Duplicate beneficiaries (same person with slight name/casing variation), inconsistent date formats (`YYYY-MM-DD` vs `DD/MM/YYYY`), missing signup dates, dirty locations (`"New Delhi"`, `"delhi"`, `"N. Delhi"`). |
| `attendance.csv` | 618 | Inconsistent program names (`"Digital Literacy"` vs `"Digi-Literacy"` vs `"digital literacy"`), duplicate attendance check-ins, non-numeric session hours (`"2 hrs"`), orphan records with non-existent participant IDs (`"BEN-999"`). |
| `expenses.csv` | 69 | Currency-formatted strings (`"₹12,500.00"`), negative expense values (`-4500.00`), blank program codes, missing cost categories. |
| `outcomes.csv` | 40 | Out-of-range exit scores (`145.0` on a 0-100 scale), missing baseline scores. |

---

## 5. Folder Structure

```
traceimpact/
├── data/
│   ├── raw/                  # Immutable synthetic raw CSV files
│   └── processed/            # Cleaned, standardized CSV exports (Day 2)
├── docs/
│   ├── PROJECT_STATUS.md     # Project audit documentation
│   ├── DATA_PIPELINE.md      # Data cleaning & validation specifications (Day 2)
│   └── KPI_DEFINITIONS.md    # Nonprofit KPI formulas & lineage catalog (Day 3)
├── sql/
│   ├── schema.sql            # PostgreSQL table definitions (DDL)
│   ├── views.sql             # SQL Analytics & KPI Views layer (Day 3)
│   └── analytics_examples.sql# Interview-friendly analytics & lineage queries (Day 3)
├── src/
│   ├── config.py             # Environment configuration (.env loader)
│   ├── cleaning/             # Day 2 data cleaning & validation pipeline
│   │   ├── __init__.py
│   │   ├── column_maps.py    # Declarative column & categorical mappings
│   │   ├── normalizers.py    # Pure normalization functions (dates, text, numbers)
│   │   ├── validators.py     # Anomaly detection & quality issue collectors
│   │   ├── transformers.py   # Dataset transformers (beneficiaries, attendance, etc.)
│   │   ├── loader.py         # Relational database & processed CSV loader
│   │   └── run_pipeline.py   # Day 2 pipeline orchestrator
│   ├── database/             # SQLAlchemy engine, session & ORM models
│   │   ├── connection.py
│   │   ├── models.py
│   │   ├── init_db.py
│   │   └── apply_views.py    # Day 3 SQL views executor
│   ├── generator/            # Synthetic data generation engine
│   │   └── generate_data.py
│   ├── ingestion/            # Raw file ingestion & JSONB staging
│   │   └── ingest_raw.py
│   └── verify_day1.py        # End-to-end health check script
├── tests/
│   ├── test_day1.py          # Day 1 foundation tests
│   ├── test_day2.py          # Day 2 cleaning & validation tests
│   └── test_day3.py          # Day 3 SQL analytics & KPI tests
├── .env.example              # Sample environment variables
├── requirements.txt          # Project dependencies
├── pytest.ini                # Pytest configuration
└── README.md                 # Project documentation
```

---

## 6. How to Run

### Prerequisites
- Python 3.10+
- PostgreSQL server running locally

### Running Day 1 (Raw Ingestion)
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run raw ingestion pipeline
python -m src.ingestion.ingest_raw

# 3. Run Day 1 verification & test suite
python -m src.verify_day1
pytest tests/test_day1.py -v
```

### Running Day 2 (Cleaning, Validation & Domain Loading)
```bash
# 1. Run Day 2 data pipeline
python -m src.cleaning.run_pipeline

# 2. Run complete test suite (Day 1 + Day 2)
pytest tests/test_day1.py tests/test_day2.py -v
```

### Running Day 3 (SQL Analytics & KPI Layer)
```bash
# 1. Initialize schema (if setting up fresh)
python -m src.database.init_db

# 2. Run Day 2 cleaning pipeline (if setting up fresh)
python -m src.cleaning.run_pipeline

# 3. Apply SQL analytics views to PostgreSQL
python -m src.database.apply_views

# 4. Run full test suite across all 3 days
pytest -v
```
