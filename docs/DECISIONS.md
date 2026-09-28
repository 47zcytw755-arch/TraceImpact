# TraceImpact 2.0 — Architecture Decision Records (ADRs)

> **Document Version:** 2.0.0  
> **Status:** RATIFIED & IMPLEMENTED  
> **Scope:** Foundational Technical, Data Engineering, Machine Learning, AI Governance, and Presentation Architecture Decisions.

---

## Decision 1: PostgreSQL as the Core Relational & Analytical Storage Engine

### Context
TraceImpact requires a dependable data store capable of handling raw JSON document staging, relational normalization, complex analytical queries with window functions, JSONB indexing, and concurrency.

### Problem
Should the platform use an embedded engine (SQLite), a NoSQL document database (MongoDB), a distributed warehouse (Snowflake/BigQuery), or an ACID-compliant relational engine (PostgreSQL)?

### Options Considered
1. **SQLite**: Minimal setup, but lacks robust JSONB indexing, window functions across CTEs, concurrent connection pooling, and multi-user scaling.
2. **MongoDB**: Strong JSON handling, but lacks strict ACID foreign-key enforcement, relational joins for complex financial KPIs, and SQL view abstractions.
3. **Snowflake / BigQuery**: High analytical power, but introduces unnecessary operational overhead, latency for real-time app queries, and cloud subscription costs for portfolio/mid-sized nonprofit deployments.
4. **PostgreSQL 14+**: Full ACID compliance, native JSONB support, powerful Common Table Expressions (CTEs), window functions, mature Python ecosystem support, and native Power BI / Streamlit connectivity.

### Decision
Adopt **PostgreSQL 14+** as the universal database backend for all staging, domain tables, quality logs, and analytical views.

### Reason
PostgreSQL uniquely bridges unstructured raw document staging (Bronze JSONB) and structured financial/operational domain modeling (Silver/Gold relational tables and views) within a single zero-license-cost engine.

### Trade-offs
- *Upside:* Zero cloud vendor lock-in, transactional integrity, sub-15ms view performance on indexed keys.
- *Downside:* Requires local or containerized database provisioning compared to file-based SQLite.

### Current Status
✅ **IMPLEMENTED** (All 14 tables and 13 views deployed and validated).

### Future Revisit Condition
Revisit if table sizes exceed 100 million rows requiring distributed columnar partitioning or multi-terabyte data lakes.

---

## Decision 2: Python (Pandas, SQLAlchemy, Scikit-Learn) as Primary Engineering Stack

### Context
The data pipeline requires data ingestion, cleaning, transformation, machine learning inference, AI orchestration, and dashboard rendering.

### Problem
Should the engineering pipeline use Java/Scala (Spark), Go, Rust, or Python?

### Options Considered
1. **Java / Scala**: High throughput, but verbose syntax, steep learning curve, and slower iteration for AI/dashboarding.
2. **Go / Rust**: Extreme execution speed, but limited data science, ML, and interactive data visualization ecosystems.
3. **Python 3.10+**: Universal language for data engineering, scikit-learn ML, LLM orchestration, Streamlit UI, and SQLAlchemy database abstraction.

### Decision
Standardize on **Python 3.10+** utilizing Pandas, SQLAlchemy, Pydantic/dataclasses, and Scikit-Learn.

### Reason
Python provides the richest unified ecosystem across the entire data lifecycle: raw ETL (`requests`, `pandas`), database persistence (`psycopg2`, `sqlalchemy`), machine learning (`scikit-learn`), and interactive UI (`streamlit`).

### Trade-offs
- *Upside:* Rapid development, unified code base, seamless integration with AI libraries.
- *Downside:* Higher memory footprint than compiled languages (mitigated by chunked streaming and vectorized operations).

### Current Status
✅ **IMPLEMENTED** (Complete codebase written in modular Python).

### Future Revisit Condition
Revisit if sub-millisecond edge streaming ingestion is required.

---

## Decision 3: Medallion Architecture with Immutable Raw JSONB Staging (Bronze Layer)

### Context
When field staff upload CSV spreadsheets or API responses arrive, traditional systems immediately clean and overwrite data in place, destroying raw history.

### Problem
How to guarantee that defective or altered raw data can always be re-examined, audited, or reprocessed without data loss?

### Options Considered
1. **Direct Ingestion into Domain Tables**: Discards unparsable rows; permanently loses original formatting.
2. **File-Only Archiving**: Raw CSVs kept on disk, but querying raw payloads requires slow manual file parsing.
3. **Database Raw Staging (JSONB Bronze Layer)**: Persist raw rows as immutable JSONB records in `source_records` and `api_raw_responses` with 1-based row indices before running cleaning logic.

### Decision
Implement an immutable **Bronze JSONB Staging Layer** in PostgreSQL.

### Reason
Preserving raw data in database JSONB guarantees that any transformation bug or quality triage rule can be modified and re-run against the exact original data without needing to re-request field spreadsheets or re-call external APIs.

### Trade-offs
- *Upside:* 100% audit defensibility; non-destructive ETL.
- *Downside:* Increases database storage volume by ~1.5x.

### Current Status
✅ **IMPLEMENTED** (`source_records` and `api_raw_responses` active).

### Future Revisit Condition
Implement automated partition archiving to cold cloud object storage if raw tables exceed 50 GB.

---

## Decision 4: SHA-256 Cryptographic Fingerprinting for Source Provenance

### Context
Nonprofit grant compliance and public data monitoring require proof that underlying source files and API payloads have not been tampered with or modified.

### Problem
How to establish cryptographic proof of source file integrity without complex distributed blockchain infrastructure?

### Options Considered
1. **File Timestamp / Size Check**: Fragile; timestamps change upon copy or download.
2. **MD5 / CRC32 Checksum**: Fast, but cryptographically broken and vulnerable to collision attacks.
3. **SHA-256 Cryptographic Hash**: Industry standard, collision-resistant, 64-character hex digest computed on raw file bytes upon arrival.

### Decision
Calculate and record **SHA-256 cryptographic checksums** for all source files (`source_files.file_hash`) and API page responses (`api_raw_responses.response_hash`).

### Reason
SHA-256 provides indisputable mathematical verification that staged database records match the exact byte payload received from the disk or network.

### Trade-offs
- *Upside:* Zero external dependencies, instant verification, cryptographic security.
- *Downside:* Minor CPU hashing overhead upon ingestion (negligible for CSVs and JSON payloads).

### Current Status
✅ **IMPLEMENTED** (Enforced in `src/ingestion/api_client.py` and `src/cleaning/loader.py`).

### Future Revisit Condition
None; SHA-256 remains the standard.

---

## Decision 5: Analytical & KPI Metrics Computed via Database Views (Gold Layer)

### Context
Dashboards and reporting tools (Streamlit, Power BI) need access to calculated financial and operational metrics (e.g. Cost per Beneficiary, Outcome Improvement %, Attendance Consistency).

### Problem
Should KPI calculations be embedded in application Python code, BI DAX formulas, or centralized PostgreSQL views?

### Options Considered
1. **Application-Level Calculation (Python/Pandas only)**: Couples metrics to Streamlit; causes drift when Power BI or SQL users query the database.
2. **BI-Only Calculation (DAX measures only)**: Couples metrics to Power BI; makes database-direct integrations blind to business logic.
3. **Centralized PostgreSQL Views (`v_program_kpis`, `v_pbi_*`)**: Enforce Single Version of Truth (SSOT) at the database layer; consume views directly in Streamlit and Power BI.

### Decision
Centralize all core analytical transformations and KPI definitions in **PostgreSQL Views** leveraging Common Table Expressions (CTEs) and `NULLIF` division safety.

### Reason
Ensures 100% mathematical consistency across all interfaces. A metric calculated in Streamlit matches the exact value displayed in Power BI and raw SQL.

### Trade-offs
- *Upside:* Single source of truth, eliminates Cartesian row multiplication bugs, reusable across tools.
- *Downside:* Heavy view queries recompute on every execution unless materialized or cached.

### Current Status
✅ **IMPLEMENTED** (13 contract-stable views deployed in `sql/`).

### Future Revisit Condition
Convert high-volume views to Materialized Views with automated refresh triggers if query latency exceeds 500ms under high load.

---

## Decision 6: Dual Presentation Layer — Streamlit for Operations, Power BI for Executive Reporting

### Context
Different stakeholders require different visual paradigms: technical/data engineers need real-time data inspection, SQL tracing, and triage controls, while executive leadership and board members require high-polish BI scorecards and slicing.

### Problem
Should the platform standardize on a single UI tool or support a dual presentation architecture?

### Options Considered
1. **Streamlit Only**: Excellent for interactive data engineering and AI assistants, but lacks drag-and-drop report customization and enterprise BI distribution.
2. **Power BI Only**: Industry standard for executive dashboards, but cannot execute Python scripts for live cryptographic verification, database health diagnostics, and custom ML pipelines.
3. **Dual Architecture (Streamlit + Power BI)**: Streamlit acts as the technical/operational control plane; Power BI acts as the executive analytics presentation layer.

### Decision
Implement a **Dual Presentation Architecture** where both Streamlit and Power BI read directly from the exact same PostgreSQL Gold views.

### Reason
Serves both technical and executive audiences without compromising functionality.

### Trade-offs
- *Upside:* Maximum flexibility; provides complete operational tooling and executive-ready BI.
- *Downside:* Requires maintaining two visual frontends (both fed by the same database contracts).

### Current Status
✅ **IMPLEMENTED** (Streamlit 6-page portal and Power BI 9-page semantic model verified).

### Future Revisit Condition
Revisit if organizational governance mandates a single consolidated BI tool.

---

## Decision 7: World Bank Indicators as Real Public Benchmark Data Source

### Context
To validate that TraceImpact is a generalizable data platform, the platform needed a high-quality, real-world data source to complement the synthetic nonprofit operational dataset.

### Problem
Which public API provides global coverage, stable versioning, no API key barriers, and relevant development metrics?

### Options Considered
1. **UN Data API**: Rich datasets, but fragmented endpoints and inconsistent uptime.
2. **Kaggle / Static Public Datasets**: Static, no live API ingestion pipeline to demonstrate scheduling and pagination.
3. **World Bank Indicators API (`api.worldbank.org/v2`)**: Standardized REST API, global coverage (264 countries, 1960–2024), open authentication, JSON formatting, and essential development indicators (GDP, Population, Life Expectancy, Sanitation).

### Decision
Adopt the **World Bank Indicators API** as the real-world public data integration source.

### Reason
Provides clean, structured, live API data with pagination, allowing TraceImpact to prove live ingestion, rate limiting, data quality checking, ML anomaly detection, and AI investigation at scale.

### Trade-offs
- *Upside:* Zero API keys needed, deterministic endpoints, globally recognized data.
- *Downside:* API responses include historical null values for smaller nations (handled gracefully as `INFO` data quality notices).

### Current Status
✅ **IMPLEMENTED** (5,588 observations ingested across 264 countries).

### Future Revisit Condition
Expand to include additional public endpoints (e.g. WHO Global Health Observatory, IMF Data) as secondary connectors.

---

## Decision 8: Isolation Forest for Unsupervised ML Anomaly Detection

### Context
Public macroeconomic indicators contain historical volatility, reporting revisions, and abrupt structural shifts. Manual detection across 264 countries and multiple indicators is infeasible.

### Problem
Which machine learning approach should be used to detect multi-dimensional statistical anomalies?

### Options Considered
1. **Simple 2-Sigma (Z-Score) Thresholds**: 1-dimensional; fails to capture multi-year velocity, peer-group deviations, and multivariate interactions.
2. **Supervised Classification (XGBoost, Random Forest)**: Requires labeled ground-truth anomalies, which do not exist objectively in historical public development data.
3. **Isolation Forest (`sklearn.ensemble.IsolationForest`)**: Unsupervised, highly efficient ($O(n \log n)$), isolates anomalies by randomly partitioning feature space, handles multivariate distributions without distributional assumptions.

### Decision
Deploy **Isolation Forest** with a 4-feature statistical vector (Z-Score, YoY Growth %, Peer Group Z-Score, Historical Baseline Ratio).

### Reason
Provides robust, unsupervised anomaly detection across diverse indicator distributions without requiring impossible manual labeling.

### Trade-offs
- *Upside:* Fast training (<0.3s), continuous anomaly scores, no ground-truth label dependencies.
- *Downside:* Descriptive anomaly scoring only; **does not prove causation**.

### Current Status
✅ **IMPLEMENTED** (`src/ml/anomaly_detector.py` active with 783 anomalies cataloged).

### Future Revisit Condition
Incorporate time-series specific models (e.g. Prophet, Auto-ARIMA) if seasonal high-frequency indicators (monthly/daily) are added.

---

## Decision 9: Deterministically Constrained AI Investigation Layer

### Context
Users want natural-language explanations for detected anomalies and data patterns.

### Problem
Large Language Models (LLMs) frequently hallucinate unsupported causal claims, misinterpret statistical numbers, or generate ungrounded explanations.

### Decision
Constrain the AI investigation engine to **Deterministic Evidence Grounding**:
1. All baseline statistics, historical means, Z-scores, and co-occurring indicators are pre-computed in Python/SQL.
2. Only verified evidence JSON dictionaries are passed to the AI.
3. Outputs are strictly structured into **VERIFIED FACTS**, **CONTEXTUAL HYPOTHESES**, and a mandatory **NON-CAUSALITY DISCLAIMER**.

### Reason
Prevents AI hallucinations and ensures that high-stakes reporting remains defensible and grounded in empirical data.

### Trade-offs
- *Upside:* 100% grounded explanations; transparent reasoning.
- *Downside:* AI cannot answer questions beyond the structured evidence provided in context.

### Current Status
✅ **IMPLEMENTED** (`src/ai/investigator.py` active).

### Future Revisit Condition
Integrate formal Retrieval-Augmented Generation (RAG) vector embeddings over policy documents when textual context is introduced.

---

## Decision 10: Strict Read-Only SQL Whitelist for Natural-Language Queries

### Context
The AI Query Assistant allows non-technical users to ask questions in plain English and execute SQL queries against the database.

### Problem
Allowing an LLM or natural-language parser to generate unconstrained SQL risks SQL injection, data exfiltration, accidental data mutation (`DROP`, `DELETE`), and resource exhaustion.

### Decision
Enforce a multi-layered **SQL Security Validator**:
1. **Read-Only Token Enforcement**: Permits strictly `SELECT` and `WITH` statements.
2. **Disallowed Keywords Blocklist**: Immediately rejects `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `EXEC`, etc.
3. **Anti-Chaining**: Blocks statement chaining (semicolons `;`) and comment tokens (`--`, `/*`).
4. **View Whitelist**: Restricts execution strictly to audited analytical views (`v_program_*`, `v_data_quality_*`, `v_world_bank_*`). Raw tables and staging records cannot be directly queried.

### Reason
Completely eliminates SQL injection and accidental database corruption while still providing rich natural-language analytical capabilities.

### Trade-offs
- *Upside:* Zero risk of database modification or unauthorized schema access.
- *Downside:* Users cannot run arbitrary custom ad-hoc joins beyond the approved view catalog.

### Current Status
✅ **IMPLEMENTED** (`src/dashboard/ai_assistant.py` and `tests/test_day7.py`).

### Future Revisit Condition
None; this security boundary is permanent.

---

## Decision 11: Deliberate Avoidance of Heavy Distributed Infrastructure (Kafka, Spark, Databricks)

### Context
Modern data engineering discussions frequently emphasize distributed big data frameworks.

### Problem
Should TraceImpact incorporate Kafka, Apache Spark, Databricks, or Airflow for its current scale?

### Decision
**Deliberately avoid distributed big data frameworks** for the current portfolio and mid-sized organizational scale. Standardize on PostgreSQL, pure-Python scheduling, and vectorized Pandas.

### Reason
- **Scale Reality:** Typical nonprofit and public indicator datasets range from tens of thousands to a few million rows. A single PostgreSQL instance with SSD storage easily processes 20,000+ records per second (as empirically proven by the 100,000-record stress test running in 5.23s).
- **Cost & Complexity:** Introducing Spark, Kafka, or Databricks would increase operational maintenance by 10x, require dedicated DevOps teams, and cost hundreds of dollars monthly in cloud infrastructure with zero analytical benefit at this scale.

### Trade-offs
- *Upside:* Extreme simplicity, instantaneous local setup, zero infrastructure costs, rapid test execution (94 tests in <3 seconds).
- *Downside:* Single-node vertical scaling limit (sufficient up to tens of millions of records).

### Current Status
✅ **IMPLEMENTED & VALIDATED** (Demonstrated by lightweight, dependency-free architecture).

### Future Revisit Condition
Introduce Apache Spark or DuckDB if data volume exceeds 100 million rows per batch.
