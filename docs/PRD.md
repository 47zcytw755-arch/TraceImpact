# TraceImpact 2.0 — Product Requirements Document (PRD)

> **Document Version:** 2.0.0  
> **Product Name:** TraceImpact — Traceable Impact Reporting & Data Intelligence Platform  
> **Status:** RELEASE VALIDATED  

---

## 1. Product Vision

**TraceImpact** is a portfolio-scale, defensible data intelligence platform engineered for mission-driven organizations, philanthropic grant-makers, and public policy analysts. It eliminates "black-box" reporting by establishing an unbroken, cryptographic chain of custody from raw input spreadsheets and live public REST APIs to executive dashboards, machine learning anomaly detectors, and grounded AI investigations.

---

## 2. Problem Statement

Nonprofit and social sector organizations manage millions of dollars in philanthropic funding and serve vulnerable populations, yet their reporting systems rely on fragile, fragmented spreadsheets. When data is transformed for executive decks or donor audits:
1. Dirty or malformed records are silently dropped or overwritten without an audit trail.
2. Inconsistent date, currency, and location formats introduce calculation errors.
3. Personal Identifiable Information (PII) of community members is routinely exposed across unencrypted files.
4. Reported KPIs (e.g., Cost per Beneficiary, Outcome Improvement) cannot be linked back to the physical source rows that produced them.
5. Statistical anomalies and abrupt shifts in public development indicators are caught too late or explained with unverified speculation.

---

## 3. Target Users & Stakeholders

| User Persona | Role / Context | Primary Goals in TraceImpact |
| :--- | :--- | :--- |
| **Program Managers** | Field program directors overseeing education, healthcare, and livelihood operations. | Monitor participant attendance, tracking budget utilization, reviewing outcome improvements. |
| **Data Quality & Operations Teams** | Operations staff responsible for cleaning and merging field spreadsheets. | Identify defective rows (duplicates, invalid numbers, orphan IDs), review triage status, reprocess records. |
| **Finance & Grant Officers** | Financial compliance officers and grant auditors. | Reconcile expenses against allocated budgets, verify cost-per-beneficiary ratios, audit source vouchers. |
| **Executive Leadership & Board** | Executive Directors, trustees, and institutional donors. | Review executive summaries, evaluate program impact across domains, explore macro public trends. |
| **Data Engineers & Analysts** | Technical data specialists building downstream analytics and ML pipelines. | Query normalized PostgreSQL views, execute ML anomaly detection, maintain automated ingestion schedules. |

---

## 4. User Problems & Pain Points

1. **Fragmented Data**: Data arrives across scattered CSVs with inconsistent column headers (`participant_id` vs `client_identifier`).
2. **Silent Data Loss**: Traditional scripts drop invalid rows; auditors cannot determine how many records were originally submitted.
3. **Lack of Provenance**: Inability to drill down from a high-level metric (e.g., "$130,311.93 spent") to exact underlying receipt records.
4. **PII Vulnerability**: Storing participant names and phone numbers in cleartext violates privacy standards.
5. **Division-by-Zero Crashes**: Unsafe SQL/BI calculations fail when programs have zero attendance or zero budget.
6. **Hallucinated Explanations**: Generic AI tools invent unsupported causal reasons for data anomalies without checking database baselines.

---

## 5. Product Goals & Non-Goals

### Product Goals
- **100% Non-Destructive Ingestion**: Preserve raw source files and API payloads verbatim in PostgreSQL JSONB with SHA-256 hashes.
- **Auditable Quality Triage**: Catalog every defect with severity (`ERROR`, `WARNING`, `INFO`) and resolution status (`OPEN`, `RESOLVED`, `QUARANTINED`).
- **Cryptographic 1-to-1 Lineage**: Enable bidirectional drilldown from any metric to the physical raw row on disk or raw API payload.
- **Single Source of Truth**: Centralize KPI calculations in PostgreSQL views shared identically by Streamlit and Power BI.
- **Unsupervised Anomaly Detection**: Automatically flag statistically extreme country-year indicator shifts using Isolation Forest.
- **Grounded AI Investigations**: Generate AI explanations strictly bounded by pre-computed empirical database facts.
- **Zero Hardcoded Secrets**: Protect all credentials via environment variables and enforce read-only SQL security.

### Non-Goals
- **Not a Transactional ERP / CRM**: TraceImpact is an analytics, quality, and intelligence platform; it is not a direct participant registration portal or accounting software.
- **No Causal Proof Claims**: Machine learning anomaly scores and AI insights describe statistical divergence; they do not claim to prove real-world causality.
- **No Heavy Distributed Cluster**: Deliberately avoids Apache Spark, Hadoop, or Kafka clusters for mid-sized organizational scale.

---

## 6. Core User Journeys

1. **Ingest Operational CSV Data**: User places raw spreadsheets in `data/raw/`; pipeline calculates SHA-256 hashes, stages raw JSONB, normalizes headers/dates/currencies, anonymizes PII, catalogs anomalies, and loads clean domain tables.
2. **Ingest Public World Bank Data**: Automated scheduler or CLI pulls live development indicators via REST API with retries, stores raw JSON payloads, validates bounds, and updates time-series tables idempotently.
3. **Inspect Executive Scorecard**: Executive opens Streamlit Page 1 or Power BI Page 1 to review high-level KPIs (Programs, Beneficiaries, Expenses, Clean Record Rate).
4. **Triage Data Quality Issues**: Data quality analyst opens Page 3, filters by severity (`ERROR`, `WARNING`, `INFO`) or status, and views exact raw values and column names.
5. **Trace KPI Back to Source**: Auditor clicks on a metric on Page 4 (Traceability), views the domain record, the raw JSON staging entry, the file SHA-256 hash, and verifies the exact line in the physical CSV file.
6. **Explore Global Public Trends**: Analyst navigates to Page 6, selects countries and indicators, and reviews historical trends (1960–2024), YoY changes, and regional benchmarks.
7. **Evaluate ML Anomalies**: Data scientist inspects Isolation Forest anomaly scores, reviewing features snapshots (Z-Score, YoY Growth, Peer Deviation).
8. **Review Grounded AI Insights**: Executive reads an AI investigation bulletin on Page 6, reviewing the structured empirical evidence alongside non-causal hypotheses.
9. **Ask Natural-Language Questions**: Non-technical user types a query in Page 5 (AI Query Assistant), receiving safe SQL, an architectural explanation, and an instant data table.
10. **Monitor Pipeline Ingestion History**: Operations engineer checks API ingestion run logs, durations, record counts, and failure statuses on Page 7.

---

## 7. Functional Requirements Matrix

| ID | Requirement Description | Priority | Current Status | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **FR-01** | **Raw CSV Ingestion & SHA-256 Staging** | P0 (Critical) | ✅ IMPLEMENTED | Computes SHA-256 hash, stages verbatim rows into `source_records` JSONB without altering disk files. |
| **FR-02** | **Header & Data Normalization Engine** | P0 (Critical) | ✅ IMPLEMENTED | Maps column aliases, standardizes dates to `YYYY-MM-DD`, cleans currency strings to numeric. |
| **FR-03** | **PII Pseudonymization** | P0 (Critical) | ✅ IMPLEMENTED | Generates salted SHA-256 `anonymized_code` for community participants; excludes names/phones from domain tables. |
| **FR-04** | **Data Quality Triage & Quarantine** | P0 (Critical) | ✅ IMPLEMENTED | Flags anomalies across `ERROR`, `WARNING`, `INFO`; quarantines blocking errors from domain tables. |
| **FR-05** | **Relational Domain Storage** | P0 (Critical) | ✅ IMPLEMENTED | Loads normalized data into `programs`, `beneficiaries`, `attendance`, `expenses`, `outcomes` with FKs. |
| **FR-06** | **SQL KPI & Analytical View Layer** | P0 (Critical) | ✅ IMPLEMENTED | Materializes 13 views with CTE aggregations and `NULLIF` division safety, eliminating row multiplication. |
| **FR-07** | **1-to-1 Bidirectional Lineage** | P0 (Critical) | ✅ IMPLEMENTED | Connects any domain metric back to `source_record_id` and physical CSV file row coordinate. |
| **FR-08** | **World Bank REST API Ingestion** | P1 (High) | ✅ IMPLEMENTED | Fetches 4 indicators across 264 countries with pagination, retries, and raw bronze JSON staging. |
| **FR-09** | **Automated Pipeline Scheduler** | P1 (High) | ✅ IMPLEMENTED | Pure-Python background scheduler executing configurable periodic runs with `--once` CI mode. |
| **FR-10** | **Isolation Forest ML Anomaly Detection** | P1 (High) | ✅ IMPLEMENTED | Scikit-learn model scoring observations across 4 statistical features; persists scores in database. |
| **FR-11** | **Grounded AI Investigation Engine** | P1 (High) | ✅ IMPLEMENTED | Synthesizes pre-computed evidence into structured reports separating facts from hypotheses. |
| **FR-12** | **Safe AI Natural-Language Query Engine** | P1 (High) | ✅ IMPLEMENTED | Translates questions to SQL with strict read-only token and approved view whitelist enforcement. |
| **FR-13** | **Streamlit 6-Page Interactive Portal** | P1 (High) | ✅ IMPLEMENTED | Renders real-time health diagnostics, scorecards, triage grids, and lineage verification. |
| **FR-14** | **Power BI 9-Page Analytics Semantic Model**| P1 (High) | ✅ IMPLEMENTED | Full star-schema model with 32 DAX measures, M scripts, dark theme, and 100% PostgreSQL parity. |
| **FR-15** | **100,000-Record Stress Test Harness** | P2 (Medium) | ✅ IMPLEMENTED | Validates pipeline scalability, processing 100K records in 5.23s at 19,120 RPS under 417 MB RAM. |
| **FR-16** | **Cloud Data Lakehouse Export (ADLS/S3)** | P3 (Low) | 📋 PLANNED | Automated export of parquet partitions to cloud object storage. |

---

## 8. Non-Functional Requirements (NFRs)

- **Reliability & Defensibility**: 100% of pipeline runs must be reproducible. Raw data must never be modified or destroyed.
- **Performance**:
  - Sub-15ms query latency for all analytical views on indexed keys.
  - Sub-second ML inference across 5,588 observations.
  - Ingestion throughput exceeding 15,000 records per second for bulk operations.
- **Security & Privacy**:
  - Zero hardcoded passwords or API keys in source code.
  - Salted cryptographic hashing for all community member PII.
  - 100% parameterized SQL queries preventing SQL injection.
- **Scalability**: Single-node architecture verified up to 100,000 records per batch with memory consumption below 500 MB.
- **Maintainability**: Pure-Python modular architecture with zero heavy infrastructure dependencies (Spark/Kafka).
- **Testability**: Automated test suite executing 94 tests in under 3.0 seconds with 100% pass rate.

---

## 9. Product Evolution Milestones

### Phase 1: MVP (Days 1–4) — Foundation & Quality
- Staged raw CSV ingestion with SHA-256 hashing.
- Declarative cleaning pipeline and PII pseudonymization.
- Multi-tier data quality triage log (`data_quality_issues`).
- Normalized relational domain tables and core SQL views.

### Phase 2: V1 (Days 5–7) — Analytics, Traceability & Streamlit
- Streamlit multi-page dashboard (`app.py` + 5 pages).
- 1-to-1 cryptographic lineage proof engine.
- Natural-language AI query assistant with read-only SQL whitelist.
- Comprehensive 94-test regression test harness.

### Phase 3: V2 (TraceImpact 2.0 — Current Release) — Public Data, ML, AI & Power BI
- Live World Bank REST API ingestion with automated background scheduler.
- Public Data Explorer with 5,588 observations across 264 countries (1960–2024).
- Isolation Forest unsupervised ML anomaly detector.
- Evidence-grounded AI investigation engine and insights feed.
- Power BI 9-page semantic model and automated measure validator.
- 100,000-record scale and stress testing benchmarks.

### Phase 4: Future Roadmap (Planned)
- Cloud storage connector (AWS S3 / Azure Data Lake Storage Gen2).
- Continuous multi-source REST connectors (WHO, UNESCO, IMF).
- Vector RAG engine indexing public policy whitepapers.
- Automated email/Slack alert webhooks for high-severity data quality errors.
