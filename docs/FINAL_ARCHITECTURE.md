# TraceImpact 2.0 — Final Architecture Reference

## System Overview

TraceImpact is a Medallion-architecture data platform for nonprofit impact reporting,
with three progressively refined data layers (Bronze → Silver → Gold), machine learning
anomaly detection, AI-assisted investigation, and a multi-channel presentation tier.

---

## Architecture Layers

### 1. Bronze Layer (Immutable Ingestion)

**Purpose:** Ingest and preserve raw data with zero modification.

| Component | Technology | Description |
|---|---|---|
| CSV Ingestion | `src/ingestion/ingest_raw.py` | SHA-256 file hashing, verbatim JSONB row staging |
| API Ingestion | `src/ingestion/world_bank.py` | Paginated REST API retrieval with raw response archival |
| Provenance | `source_files` table | File hash, name, row count, timestamp |
| Raw Staging | `source_records` table | JSONB row data with 1-based line coordinates |
| API Archive | `api_raw_responses` table | Full JSON response with SHA-256 digest |

**Key Guarantee:** Raw files on disk are NEVER modified. Every transformation is tracked.

### 2. Silver Layer (Cleaning, Validation & Domain)

**Purpose:** Normalize, validate, and load structured domain entities.

| Component | Technology | Description |
|---|---|---|
| Column Mapping | `src/cleaning/column_maps.py` | Header normalization rules |
| Normalizers | `src/cleaning/normalizers.py` | Date, currency, text, location standardization |
| Validators | `src/cleaning/validators.py` | Duplicate, range, reference, format checks |
| Transformers | `src/cleaning/transformers.py` | Entity resolution, PII pseudonymization |
| Quality Log | `data_quality_issues` table | Cataloged anomalies (not silently dropped) |
| Domain Tables | `programs`, `beneficiaries`, `attendance`, `expenses`, `outcomes` | Normalized relational entities |
| WB Validation | `src/quality/world_bank_quality.py` | World Bank observation validation |

**Key Guarantee:** Dirty records are cataloged, not deleted. Every domain row carries `source_record_id` lineage.

### 3. Gold Layer (SQL Analytics & Views)

**Purpose:** Pre-aggregated, mathematically sound analytical computations.

| View Category | Files | Views |
|---|---|---|
| KPI Analytics | `sql/views.sql` | `v_program_reach`, `v_attendance_consistency`, `v_cost_per_beneficiary`, `v_cost_per_beneficiary_hour`, `v_outcome_improvement`, `v_program_kpis` |
| Quality Governance | `sql/views_quality.sql` | `v_data_quality_summary`, `v_data_quality_by_file`, `v_data_quality_by_program`, `v_data_quality_by_type`, `v_data_quality_blocking` |
| Power BI Executive | `sql/views_power_bi.sql` | 9 executive intelligence views |
| World Bank Analytics | `sql/views_world_bank.sql` | `v_world_bank_country_trends`, `v_world_bank_latest_indicators`, `v_world_bank_indicator_summary`, `v_world_bank_ai_lineage` |

**Key Guarantee:** All views use CTE pre-aggregation and `NULLIF` safe division. Zero Cartesian multiplication.

### 4. ML & AI Layer

**Purpose:** Statistical anomaly detection and grounded investigation.

| Component | Technology | Description |
|---|---|---|
| Feature Extraction | `src/ml/feature_extractor.py` | Z-scores, YoY growth, peer deviation, temporal features |
| Anomaly Detection | `src/ml/anomaly_detector.py` | Scikit-learn Isolation Forest (contamination=0.04) |
| AI Investigation | `src/ai/investigator.py` | Grounded findings with historical baselines and peer context |
| Model Persistence | `models/*.joblib` | Serialized trained models |
| Results Storage | `world_bank_anomalies`, `ai_investigations`, `ai_insights` tables | Persisted ML/AI outputs |

**Key Guarantee:** All findings carry mandatory non-causality disclaimers. No ungrounded causal claims.

### 5. Presentation Layer

**Purpose:** Multi-channel delivery to stakeholders.

| Channel | Technology | Description |
|---|---|---|
| Streamlit Dashboard | `app.py` + `pages/` (6 pages) | Interactive web application |
| AI Query Assistant | `src/dashboard/ai_assistant.py` | Natural language → safe SQL |
| Power BI Layer | `sql/views_power_bi.sql` | Executive intelligence views for Power BI |
| Live Pipeline Demo | `demo/` (7 files) | Control room visualization (port 8888) |

---

## Security Architecture

### SQL Injection Prevention
- **AI Assistant:** `validate_sql()` enforces SELECT-only, rejects DML/DDL keywords, comment injection, tautology patterns
- **Parameterized Queries:** All dynamic queries use SQLAlchemy `text()` with parameter binding
- **Read-Only Views:** Dashboard queries target pre-defined analytical views only

### PII Protection
- **Pseudonymization:** Salted SHA-256 hashing of beneficiary identifiers
- **No Raw PII Exposure:** Dashboard never displays raw personal data

### Credential Security
- **Environment Variables:** All credentials loaded from `.env` via `python-dotenv`
- **Gitignored:** `.env` excluded from version control
- **No Hardcoded Secrets:** Zero hardcoded credentials in codebase

---

## Data Flow Diagram

```
Raw CSV Files (data/raw/)
        │
        ▼
   SHA-256 Hash ──► source_files (provenance)
        │
        ▼
   JSONB Staging ──► source_records (immutable bronze)
        │
        ▼
   Cleaning Pipeline (normalizers → validators → transformers)
        │                    │
        ▼                    ▼
   Domain Tables         data_quality_issues (cataloged anomalies)
   (Silver Layer)
        │
        ▼
   SQL Analytical Views (Gold Layer — CTE pre-aggregated)
        │
   ┌────┼────────────────────┐
   ▼    ▼                    ▼
Streamlit  Power BI      AI Assistant
Dashboard   Views        (NL → SQL)
```

```
World Bank API (api.worldbank.org/v2)
        │
        ▼
   API Client (retry + backoff)
        │
        ▼
   api_raw_responses (SHA-256 bronze)
        │
        ▼
   DQ Validation ──► world_bank_data_quality_issues
        │
        ▼
   world_bank_observations (silver)
        │
        ▼
   Isolation Forest ML ──► world_bank_anomalies
        │
        ▼
   AI Investigator ──► ai_investigations + ai_insights
        │
        ▼
   World Bank SQL Views (gold)
        │
        ▼
   Page 6: Public Data Explorer
```

---

## Database Schema Summary

### Core Schema (8 tables)
1. `source_files` — File provenance with SHA-256
2. `source_records` — Immutable JSONB raw staging
3. `data_quality_issues` — Anomaly catalog
4. `programs` — Master program entities
5. `beneficiaries` — PII-pseudonymized community members
6. `attendance` — Session attendance facts
7. `expenses` — Financial transaction facts
8. `outcomes` — Pre/post survey evaluations

### World Bank Extension (7 tables)
9. `world_bank_countries` — Country dimension
10. `world_bank_indicators` — Indicator dimension
11. `world_bank_observations` — Observation facts
12. `world_bank_data_quality_issues` — WB validation log
13. `api_raw_responses` — Bronze API response archive
14. `world_bank_anomalies` — ML anomaly results
15. `ai_investigations` + `ai_insights` — AI findings

### ML/AI Extension (4 tables)
16. `ml_model_registry` — Model version tracking
17. `world_bank_anomalies` — Anomaly detection results
18. `ai_investigations` — Investigation reports
19. `ai_insights` — Grounded insight summaries

---

## Test Coverage

| Suite | Tests | Coverage |
|---|---|---|
| Day 1 (Ingestion) | 5 | Source file hashing, JSONB staging, program seeding |
| Day 2 (Cleaning) | 13 | Normalization, validation, duplicate detection |
| Day 3 (Analytics) | 8 | View correctness, Cartesian prevention, lineage |
| Day 4 (Quality) | 11 | Severity reconciliation, triage lifecycle |
| Day 5 (Dashboard) | 11 | Query accuracy, formatting, empty state handling |
| Day 6 (Traceability) | 9 | End-to-end lineage, PII protection, CSV verification |
| Day 7 (AI Assistant) | 10 | Preset queries, NL parsing, SQL injection prevention |
| ML/AI | 9 | Feature extraction, model training, investigation |
| World Bank | 18 | API client, validation, pipeline, scheduler |
| **Total** | **94** | **All passing** |
