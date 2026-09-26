# TraceImpact — Senior Data Engineering Portfolio Brief

**Candidate Project:** TraceImpact — Traceable Impact Reporting & Data Quality Platform  
**Target Roles:** Senior Data Engineer, Analytics Engineer, Lead Data Platform Engineer  
**Core Technologies:** Python 3.14+, PostgreSQL 16+, SQLAlchemy 2.0, Pandas, Streamlit, Pytest, Docker-ready  
**Verification Status:** 69 / 69 Automated Tests Passing • 100% Raw Data Immutability • Production Ready  

---

## 1. Executive Summary & Problem Space

Small-to-medium nonprofit organizations and grant-making foundations manage hundreds of millions of dollars in philanthropic capital using disconnected, unstructured operational spreadsheets. 

### The Core Industry Failure
When donors or regulatory auditors demand verification of reported outcomes (e.g. *"Prove you served 42 beneficiaries and spent ₹130,311"*), traditional business intelligence pipelines fail:
1. **Silent Data Loss:** Dirty records (invalid dates, duplicate check-ins, negative amounts) are dropped silently by ETL scripts to avoid pipeline crashes, creating uncataloged data leaks.
2. **Severed Data Lineage:** Transformations and deduplications sever links between dashboard KPIs and the original raw source files.
3. **Cartesian Multiplication:** Flawed relational queries joining multiple 1-to-many fact tables (e.g. attendance and expenses) multiply rows, artificially inflating expenditures and attendance counts.
4. **Beneficiary PII Vulnerability:** Operational spreadsheets often expose sensitive personal information of vulnerable individuals.

### The TraceImpact Solution
TraceImpact is an enterprise-grade data platform engineered to solve these exact systemic failures:
- **Verbatim Staging & SHA-256 Fingerprinting:** Ingests raw CSV files untouched into PostgreSQL JSONB staging while cryptographic hashes guarantee zero data tampering.
- **Defensible Data Quality Observability:** Identifies and catalogs 177 distinct anomalies across 3 severity tiers, isolating 10 blocking errors into a quarantine view without dropping data.
- **Pre-Aggregated SQL Views:** Eliminates Cartesian row explosion and division-by-zero errors through CTE pre-aggregation and `NULLIF` guards.
- **1-to-1 Cryptographic Lineage Engine:** Enables bidirectional click-through drilldown from any dashboard metric to the exact physical CSV row on local disk.
- **Safe AI Natural-Language Querying:** Grounds non-technical executive inquiries strictly in vetted analytical views with zero SQL injection or hallucination risks.

---

## 2. Technical Competencies Demonstrated

| Competency | Implementation in TraceImpact |
|------------|-------------------------------|
| **Data Ingestion & Provenance** | Immutable staging of raw CSV rows into PostgreSQL `JSONB` with 1-based physical `row_index` and SHA-256 cryptographic file tracking. |
| **Data Quality Engineering** | Multi-tier anomaly detection (`ERROR`, `WARNING`, `INFO`), programmatic triage lifecycle service (`OPEN`, `RESOLVED`, `ACCEPTED`), and Data Reliability Index (DRI: 94.94/100). |
| **Advanced SQL Modeling** | 6 analytical views + 5 quality views utilizing Common Table Expressions (CTEs), window functions, conditional aggregates, and `NULLIF` division guards. |
| **Privacy Engineering (PII)** | One-way salted SHA-256 pseudonymization (`anonymized_code`) to protect community members' personal identities in compliance with data privacy regulations. |
| **Full-Stack Dashboarding** | High-performance, multi-page Streamlit application (5 pages) with centralized data access layer and thread-safe connection pooling. |
| **AI Intent Mapping & Safety** | Natural-language query translation engine with strict keyword validation, multi-statement injection blocking, and plain-English architectural explainers. |
| **Automated Testing & CI Readiness** | 69 comprehensive Pytest test cases covering end-to-end lineage, data immutability, SQL view safety, and UI integration executing in 0.95s. |

---

## 3. Architecture & Key Engineering Trade-Offs

### A. Medallion-Style Data Architecture
```
Raw Source Datasets (data/raw/) [Untouched Disk Files]
        │ (SHA-256 Checksum Computation)
        ▼
Bronze Layer: Immutable Staging (`source_files`, `source_records` JSONB)
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
Silver Layer: Normalized Domain Tables   Data Quality Audit Log
(`programs`, `beneficiaries`,            (`data_quality_issues`)
 `attendance`, `expenses`, `outcomes`)   (177 cataloged defects)
        │                                      │
        ▼                                      ▼
Gold Layer: Analytical Views             Quality Scorecard Views
(`v_program_reach`, `v_program_kpis`)   (`v_data_quality_summary`, etc.)
        │                                      │
        └──────────────────┬───────────────────┘
                           ▼
Presentation: Streamlit Multi-Page UI + Traceability Engine + AI Assistant
```

### B. Engineering Trade-Offs & Decisions
1. **JSONB Staging vs. Flat Staging Tables:**  
   *Decision:* Stored raw rows as JSONB in `source_records`.  
   *Rationale:* Accommodates shifting upstream spreadsheet schemas without breaking database DDL, while preserving the raw input string values for audit review.
2. **CTE Pre-Aggregation vs. Direct Joins in Views:**  
   *Decision:* Pre-aggregated fact tables in isolated CTEs before joining on `program_id`.  
   *Rationale:* Direct relational joins between `programs`, `attendance` (612 rows), and `expenses` (67 rows) create a Cartesian product of over 40,000 intermediate rows, severely inflating SUM aggregations. CTE pre-aggregation guarantees strict 1-to-1 joins.
3. **Quarantine vs. Hard Rejection:**  
   *Decision:* Dirty records with critical errors are staged in JSONB and logged to `data_quality_issues`, but omitted from domain tables.  
   *Rationale:* Ensures 100% data visibility for auditability while guaranteeing downstream financial and outcome calculations are not corrupted by duplicate or negative numbers.

---

## 4. Quantitative Engineering Achievements

- **Automated Tests:** **69 / 69 passing (100%)** across 7 test suites in **0.95 seconds**.
- **Raw Data Immutability:** **100% byte-for-byte identical** verified via SHA-256 hashes across all 5 source CSVs.
- **Data Quality Observability:** **177 anomalies detected**, 149 resolved programmatically, 10 blocking errors quarantined.
- **Data Reliability Index (DRI):** **94.94 / 100** with a **98.72% clean record rate**.
- **SQL Execution Performance:** Analytical views execute in **< 15ms** on PostgreSQL with indexed foreign keys.
- **Lineage Integrity:** **100% of domain records and quality issues** maintain valid foreign keys to raw staging coordinates.

---

## 5. Interview Discussion Questions & Answers

### Q1: How did you ensure financial metrics weren't distorted by 1-to-many joins?
> *"In PostgreSQL, joining `programs` to `attendance` (612 rows) and `expenses` (67 rows) simultaneously produces a Cartesian product where expenses are duplicated for every attendance record. To solve this, our Day 3 views (`sql/views.sql`) compute expenditures and attendance counts inside separate CTEs (`exp_agg`, `att_agg`, `outc_agg`) before performing 1-to-1 joins on `program_id`. We also enforce `NULLIF(count, 0)` across all division operations to prevent divide-by-zero crashes."*

### Q2: How does TraceImpact prove a dashboard number wasn't fabricated?
> *"Every row in our domain tables (`beneficiaries`, `attendance`, `expenses`, `outcomes`) contains a `source_record_id` foreign key pointing to `source_records.record_id`. That staging table stores the verbatim raw JSONB alongside its 1-based physical row index and foreign key to `source_files`. The `source_files` table records the SHA-256 checksum of the original file. In the UI (`pages/4_Traceability.py`), the system dynamically re-reads the physical CSV from disk at the recorded line index, confirming character-for-character agreement."*

### Q3: How did you design the AI Query Assistant to prevent hallucinated numbers and SQL injection?
> *"Unlike naive LLM wrappers that pass raw natural language to text-to-SQL prompts and run arbitrary SQL, our `AIAssistantEngine` maps user intent strictly to vetted, pre-approved analytical views. It enforces a strict whitelist allowing only `SELECT` and `WITH` statements, rejects all DDL/DML tokens, blocks multi-statement semicolons and comment characters, and parameterizes program filters. It returns the live DataFrame along with an architectural explanation of the underlying CTEs."*

---

## 6. Project Tour & Key Code References

- **Relational DDL & Lineage Schema:** [`sql/schema.sql`](file:///Users/shashwat/Desktop/project1/sql/schema.sql)
- **Analytical KPI Views:** [`sql/views.sql`](file:///Users/shashwat/Desktop/project1/sql/views.sql)
- **Data Quality Scorecard Views:** [`sql/views_quality.sql`](file:///Users/shashwat/Desktop/project1/sql/views_quality.sql)
- **Cleaning & Validation Engine:** [`src/cleaning/`](file:///Users/shashwat/Desktop/project1/src/cleaning/)
- **Data Access & Query Abstractions:** [`src/dashboard/queries.py`](file:///Users/shashwat/Desktop/project1/src/dashboard/queries.py)
- **Traceability Proof Engine UI:** [`pages/4_Traceability.py`](file:///Users/shashwat/Desktop/project1/pages/4_Traceability.py)
- **AI Query Assistant Engine:** [`src/dashboard/ai_assistant.py`](file:///Users/shashwat/Desktop/project1/src/dashboard/ai_assistant.py)
- **Automated Test Suites:** [`tests/`](file:///Users/shashwat/Desktop/project1/tests/)
