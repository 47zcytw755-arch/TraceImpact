# TraceImpact 2.0 — Engineering Rules & Inviolable Governance Principles

> **Document Version:** 2.0.0  
> **Status:** MANDATORY & ENFORCED  
> **Scope:** Engineering Governance, Coding Standards, Data Quality, ML/AI Boundaries, Security Protocols, and Testing Integrity.

---

## 1. General Engineering Rules

1. **Rule 1.1 — Inspect Before Writing**: Never modify code, schemas, or documentation without first inspecting the existing implementation, active dependencies, and database contracts.
2. **Rule 1.2 — Preserve Working Functionality**: Never break working pipelines, tests, or analytical views to implement a new feature.
3. **Rule 1.3 — No Marketing Hype or Unverified Claims**: Never use terms such as "enterprise-grade", "production-ready", "zero hallucinations", or "guaranteed accuracy" unless concrete test artifacts in the repository prove the claim.
4. **Rule 1.4 — Explicit Status Labeling**: All features, components, and documentation must clearly distinguish:
   - `IMPLEMENTED`
   - `PARTIALLY IMPLEMENTED`
   - `PLANNED`
   - `EXPERIMENTAL`
   - `DEPRECATED`
   - `UNVERIFIED`

---

## 2. Data & Provenance Rules

1. **Rule 2.1 — Never Fabricate or Invent Data**: Never invent dummy database rows, artificial survey responses, or fabricated API observations in production or gold reporting tables.
2. **Rule 2.2 — Never Overwrite Raw Source Data**: Raw spreadsheets in `data/raw/` and staged raw payloads in `source_records` / `api_raw_responses` are immutable.
3. **Rule 2.3 — Mandatory Provenance Classification**: All metrics, visual charts, and documentation must carry clear data provenance tags:
   - `[REAL]`: Empirical data from verified external institutions (e.g. World Bank).
   - `[MEASURED]`: Computed pipeline or system benchmark performance metrics.
   - `[SIMULATED]`: Deterministic synthetic operational data for audit and demonstration.
   - `[PROJECTED]`: Forward-looking statistical estimates or modeled scenarios.
4. **Rule 2.4 — 1-to-1 Lineage Preservation**: Every domain record must maintain an unbroken pointer (`source_record_id` or `raw_response_id`) connecting it back to its staged raw source.

---

## 3. Database & SQL Rules

1. **Rule 3.1 — 100% Parameterized Queries**: Dynamic SQL statements in Python must use parameterized SQLAlchemy binds (`:param_name`). String concatenation or format interpolation into SQL strings is strictly forbidden.
2. **Rule 3.2 — Division Safety Guarantee**: All ratio, percentage, and cost calculations must use `NULLIF(denominator, 0)` to guarantee division-by-zero runtime safety.
3. **Rule 3.3 — Elimination of Cartesian Row Multiplication**: In analytical queries joining multiple 1-to-many child tables (`attendance`, `expenses`, `outcomes`), child tables must be pre-aggregated within dedicated Common Table Expressions (CTEs) before joining on `program_id`.
4. **Rule 3.4 — Strict Type Coercion**: Financial figures must use `NUMERIC(12, 2)` or `NUMERIC(14, 2)`; dates must use standard `DATE` (`YYYY-MM-DD`). Never store dates as unparsed text strings in Silver or Gold layers.
5. **Rule 3.5 — Idempotent Ingestion Operations**: All insert pipelines must use `ON CONFLICT (...) DO UPDATE` or pre-validation to ensure that re-executing an ingestion run does not duplicate records.

---

## 4. Python & Application Rules

1. **Rule 4.1 — Explicit Typing & Docstrings**: All new functions and methods must include Python 3.10+ type annotations and clear docstrings explaining Purpose, Args, and Returns.
2. **Rule 4.2 — Centralized Configuration**: Database connection parameters, API timeouts, and environment flags must be loaded through `src.config.Config`. Hardcoding configurations inside business modules is forbidden.
3. **Rule 4.3 — Specific Exception Handling**: Catch specific exceptions (`psycopg2.Error`, `requests.RequestException`, `ValueError`); never use bare `except: pass`.
4. **Rule 4.4 — Minimal Dependency Footprint**: Avoid importing heavy, unvetted external dependencies when standard library or existing dependencies (`pandas`, `sqlalchemy`, `scikit-learn`) suffice.

---

## 5. API & Ingestion Rules

1. **Rule 5.1 — Resilient HTTP Operations**: All external HTTP requests must specify explicit connect and read timeouts (default: 10s) and handle retries with exponential backoff.
2. **Rule 5.2 — Bronze Payload Preservation**: Before parsing or cleaning an API response, the verbatim JSON byte payload and its SHA-256 hash must be staged in `api_raw_responses`.
3. **Rule 5.3 — Pagination Safety**: API pagination loops must validate total pages reported by the API to prevent infinite loops.
4. **Rule 5.4 — Non-Blocking Scheduler**: Background schedulers must support clean signal handling (`SIGINT`, `SIGTERM`) and include a `--once` flag for safe CI/CD execution.

---

## 6. Data Quality & Triage Rules

1. **Rule 6.1 — Non-Destructive Quality Logging**: Anomalous records must be cataloged into `data_quality_issues` or `world_bank_data_quality_issues` with explicit column names, raw values, issue types, and severities.
2. **Rule 6.2 — Severity Classification Invariant**:
   - `ERROR`: Critical violation of relational constraints or financial logic (e.g. duplicate PK, negative expense, score > 100). **Must be quarantined from domain tables.**
   - `WARNING`: Non-blocking defect with missing optional data (e.g. missing phone number, missing baseline survey). Stored with notice.
   - `INFO`: Automated transformation notice (e.g. whitespace trimmed, casing standardized, historical null API value logged).
3. **Rule 6.3 — Immutability of Quarantined Records**: Quarantined records remain in Bronze staging and quality logs; they are never permanently deleted from database history.

---

## 7. Machine Learning Rules

1. **Rule 7.1 — Strict Non-Causality Principle**: Machine learning anomaly detection is descriptive, not causal. Anomaly scores describe statistical divergence from historical peer baselines; they do not prove why an event occurred.
2. **Rule 7.2 — Anomalies Are Not Automatic Errors**: An anomaly is a statistically unusual data point; it must not be labeled as an error, fraud, or data corruption without human domain verification.
3. **Rule 7.3 — Model Versioning & Artifact Persistence**: Every trained model must be registered in `ml_anomaly_models` with version string, hyperparameters, and evaluation metrics, and saved to `models/*.joblib`.
4. **Rule 7.4 — Deterministic Random State**: Unsupervised models must specify a fixed `random_state` (e.g. `42`) to guarantee reproducible inference across pipeline runs.

---

## 8. AI & Natural-Language Security Rules

1. **Rule 8.1 — Deterministic Evidence Grounding**: The AI investigation engine must only synthesize pre-computed empirical facts (means, std devs, Z-scores, YoY changes) passed in structured JSON dictionaries.
2. **Rule 8.2 — Segregation of Facts and Hypotheses**: All AI-generated text must explicitly segregate **VERIFIED FACTS** from **CONTEXTUAL HYPOTHESES (INTERPRETATION)**.
3. **Rule 8.3 — Mandatory Non-Causality Disclaimer**: Every AI investigation output must append the official Non-Causality Disclaimer.
4. **Rule 8.4 — Read-Only SQL Whitelist**: The AI Query Assistant permits strictly `SELECT` and `WITH` statements against approved Gold analytical views (`ALLOWED_OBJECTS`).
5. **Rule 8.5 — Rejection of Unsafe & Destructive Tokens**: Any query containing `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, semicolons (`;`), or comment tokens (`--`, `/*`) must be rejected immediately before database execution.

---

## 9. Security & Privacy Rules

1. **Rule 9.1 — Zero Hardcoded Secrets**: Passwords, database connection strings, and private keys must never exist in committed code or documentation.
2. **Rule 9.2 — PII Pseudonymization**: Community member full names and phone numbers must never be written to domain reporting tables or rendered on executive dashboards; they must be pseudonymized via salted SHA-256 (`anonymized_code`).
3. **Rule 9.3 — UI Sanitization**: Health check displays must expose only hostname, database name, and user; passwords and salt keys must never be rendered.
4. **Rule 9.4 — Git Tracking Protection**: `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, and local temporary files must be verified untracked via `.gitignore`.

---

## 10. Testing & Validation Rules

1. **Rule 10.1 — Tests Must Reflect Implementation**: Unit, integration, and security tests must assert actual behavior against live code and database views.
2. **Rule 10.2 — Never Weaken Tests to Pass**: Never modify test assertions, lower thresholds, or delete assertions to mask a regression.
3. **Rule 10.3 — 100% Pass Requirement**: The complete 94-test automated regression suite (`tests/`) must pass with 100% success before any release commit.
4. **Rule 10.4 — Power BI Measure Reconciled Against PostgreSQL**: Every Power BI DAX measure must be empirically verified against its corresponding PostgreSQL view using `src/power_bi_validator.py`.
