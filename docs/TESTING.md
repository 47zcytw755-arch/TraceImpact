# TraceImpact 2.0 — Testing Strategy & Quality Assurance Framework

> **Document Version:** 2.0.0  
> **Status:** 100% PASSING (94/94 Automated Tests + 100K Benchmark Suite)  
> **Test Framework:** Pytest 8.0+ / Python 3.10+  
> **Execution Duration:** ~2.0 seconds for complete test suite  

---

## 1. Testing Philosophy & Core Invariants

The TraceImpact testing philosophy is rooted in **Empirical Defensibility**:
1. **Tests Must Assert Actual Implementation:** Tests must execute real SQL against active PostgreSQL views and run real Python pipelines; no mock-only testing that masks integration failures.
2. **Never Weaken Tests to Pass:** Under no circumstances should test assertions, thresholds, or validation checks be lowered to force tests to pass.
3. **Multi-Layered Verification:** Every feature is tested across Unit, Integration, Database, Security, Lineage, and ML/AI boundaries.
4. **Idempotency Guarantee:** Re-running pipelines multiple times must produce identical record counts, metrics, and primary keys.

---

## 2. Test Pyramid & Suite Architecture

```
                       / \
                      /   \
                     / UI  \        Streamlit Page Import & Health Tests (test_day5)
                    /-------\
                   /  ML/AI  \      Isolation Forest & Grounded AI Tests (test_ml_and_ai)
                  /-----------\
                 / API/Pipeline\    World Bank Client, Scheduler & Ingestion (test_world_bank)
                /---------------\
               / Security/Lineage\  SQL Injection, Whitelist & Lineage (test_day6, test_day7)
              /-------------------\
             /  Database & Quality \ Relational FKs, Views, Triage & Math (test_day3, test_day4)
            /-----------------------\
           /   Unit & Normalization  \ Header Maps, Date/Currency Parsing (test_day1, test_day2)
          /---------------------------\
```

---

## 3. Automated Test Suite Inventory (94 Tests)

| Test Module | Domain / Subsystem | Test Count | Key Invariants Verified |
| :--- | :--- | :--- | :--- |
| [`tests/test_day1.py`](file:///Users/shashwat/Desktop/project1/tests/test_day1.py) | **Bronze Staging & Hashing** | 5 | Database connectivity, raw CSV existence, SHA-256 fingerprinting, JSONB staging in `source_records`. |
| [`tests/test_day2.py`](file:///Users/shashwat/Desktop/project1/tests/test_day2.py) | **Cleaning, PII & Validation** | 14 | Column normalization, multi-format date parsing, currency sanitization, duplicate detection, PII pseudonymization, domain loading. |
| [`tests/test_day3.py`](file:///Users/shashwat/Desktop/project1/tests/test_day3.py) | **SQL Analytical Views** | 8 | View existence, row uniqueness, Cartesian product elimination, `NULLIF` division safety, financial KPI accuracy. |
| [`tests/test_day4.py`](file:///Users/shashwat/Desktop/project1/tests/test_day4.py) | **Data Quality Triage Engine**| 11 | Severity classification (`ERROR`, `WARNING`, `INFO`), issue reconciliation, blocking error filtering, raw data immutability. |
| [`tests/test_day5.py`](file:///Users/shashwat/Desktop/project1/tests/test_day5.py) | **Dashboard Queries & UI** | 11 | Module imports, database health checks, executive scorecard accuracy, filter queries, empty-state formatting. |
| [`tests/test_day6.py`](file:///Users/shashwat/Desktop/project1/tests/test_day6.py) | **1-to-1 Cryptographic Lineage**| 9 | Bidirectional lineage (Metric ➔ Domain ➔ `source_records` ➔ `source_files` ➔ Physical CSV line coordinate). |
| [`tests/test_day7.py`](file:///Users/shashwat/Desktop/project1/tests/test_day7.py) | **AI Query Security & Safety**| 11 | Preset queries, natural language intent routing, SQL validator rejecting DDL/DML, anti-injection filter. |
| [`tests/test_world_bank.py`](file:///Users/shashwat/Desktop/project1/tests/test_world_bank.py)| **World Bank API Ingestion** | 15 | HTTP client, retries, exponential backoff, pagination, Bronze JSON staging, schema validation, scheduler CI mode. |
| [`tests/test_ml_and_ai.py`](file:///Users/shashwat/Desktop/project1/tests/test_ml_and_ai.py) | **ML Anomaly & AI Intelligence**| 10 | Feature extraction, Isolation Forest training, anomaly score schema, evidence grounding, 7-step lineage view. |
| **Total Automated Tests** | **Full System Regression** | **94** | **100% PASS (0 Failures, 0 Skipped, 0 Errors)** |

---

## 4. Specialized Testing Domains

### 4.1 Machine Learning (ML) Testing
- **Deterministic Behavior**: Model trained with fixed `random_state=42` guarantees identical decision scores across runs.
- **Input Feature Vector**: Asserts that `WorldBankFeatureExtractor` produces an $(N, 4)$ numpy matrix with no NaN values.
- **Score Output Schema**: Verifies that `anomaly_score` is a float within $[-0.50, +0.50]$ and `is_anomaly` is a boolean.
- **Edge Case Robustness**: Tests handle countries with single-year data or zero standard deviation without division-by-zero errors (using $\epsilon = 10^{-6}$).

### 4.2 AI & Natural-Language Security Testing
- **Read-Only Token Enforcement**: Asserts that queries starting with `SELECT` or `WITH` execute successfully.
- **Destructive Query Rejection**: Tests explicitly verify that statements containing `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `TRUNCATE`, `GRANT`, or `EXEC` are blocked immediately with `SecurityViolationError`.
- **SQL Injection Prevention**: Tests verify that multi-statement semicolons (`;`) and comment characters (`--`, `/*`) are blocked.
- **Approved View Whitelist**: Confirms queries targeting unapproved raw tables or staging rows are rejected.
- **Evidence Grounding**: Asserts that AI investigation reports strictly separate verified facts from hypotheses and include the Non-Causality Disclaimer.

### 4.3 Ingestion, Resilience & Scheduler Testing
- **Pagination Safety**: Validates that page counters correctly traverse multi-page API responses.
- **Retry & Backoff**: Simulates network timeouts and HTTP 429 errors, asserting up to 3 retries with 1.5x exponential backoff.
- **Malformed JSON Handling**: Ensures corrupted JSON payloads are logged with `status = 'FAILED'` without corrupting valid database observations.
- **Scheduler CI Mode**: Verifies that `python -m src.ingestion.scheduler --once` executes exactly one scheduled pass and exits cleanly with return code 0.

### 4.4 1-to-1 Cryptographic Lineage Testing
- Asserts that every domain record in `beneficiaries`, `attendance`, `expenses`, and `outcomes` possesses a valid `source_record_id`.
- Asserts that `source_records` matches the exact physical line in the CSV file on disk.
- Asserts that `v_world_bank_ai_lineage` resolves unbroken 7-step pointers from `ai_insights.insight_id` back to `api_raw_responses.response_hash`.

---

## 5. Performance & 100K Scale Stress Testing

### Stress Test Harness (`tests/stress_test_suite.py`)
TraceImpact includes a dedicated scale and stress testing harness designed to evaluate ingestion throughput, pipeline latency, and memory consumption under large workloads:

| Workload Tier | Record Count | Processing Duration | Throughput (RPS) | Peak RAM Usage | Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Small)** | 1,000 Obs | 0.045 seconds | 22,215.4 RPS | 303.61 MB | ✅ PASS |
| **Tier 2 (Medium)** | 5,000 Obs | 0.255 seconds | 19,637.7 RPS | 303.61 MB | ✅ PASS |
| **Tier 3 (Large)** | 10,000 Obs | 0.523 seconds | 19,115.9 RPS | 303.61 MB | ✅ PASS |
| **Tier 4 (Stress)** | 25,000 Obs | 1.525 seconds | 16,391.9 RPS | 303.61 MB | ✅ PASS |
| **Tier 5 (Maximum)** | 100,000 Obs | 5.230 seconds | 19,120.5 RPS | 416.64 MB | ✅ PASS |

---

## 6. Power BI Automated Metric Validation

The automated validator [`src/power_bi_validator.py`](file:///Users/shashwat/Desktop/project1/src/power_bi_validator.py) connects directly to PostgreSQL and verifies 100% parity between Power BI DAX measure formulas and live database views:

```bash
python -m src.power_bi_validator
```

### Validation Output Matrix:
```
=== TRACEIMPACT 2.0 POWER BI MEASURE VALIDATOR ===
  [PASS] Total Programs: SQL Value = 5
  [PASS] Distinct Beneficiaries: SQL Value = 51
  [PASS] Attendance Records: SQL Value = 612
  [PASS] Total Session Hours: SQL Value = 1183.0
  [PASS] Total Expenses: SQL Value = 666950.36
  [PASS] Total Budget Allocated: SQL Value = 765000.0
  [PASS] Avg Score Improvement: SQL Value = 26.18
  [PASS] Avg Outcome Improvement %: SQL Value = 79.52
  [PASS] Synthetic Total Records: SQL Value = 784
  [PASS] Synthetic Clean Record Rate %: SQL Value = 98.72
  [PASS] Synthetic Total DQ Issues: SQL Value = 177
  [PASS] Synthetic Resolved DQ Issues: SQL Value = 149
  [PASS] Synthetic Resolution Rate %: SQL Value = 84.18
  [PASS] World Bank Observations Stored: SQL Value = 5588
  [PASS] World Bank Clean Rate %: SQL Value = 100.0
  [PASS] World Bank ML Flagged Anomalies: SQL Value = 783
  [PASS] World Bank AI Investigations: SQL Value = 6
  [PASS] World Bank AI Insights: SQL Value = 33
  [PASS] API Ingestion Runs: SQL Value = 67
  [PASS] Lineage Records: SQL Value = 5839

OVERALL VALIDATION VERDICT: PASS (100% Match)
```

---

## 7. Execution Commands for Quality Assurance

```bash
# 1. Execute complete 94-test regression suite
source .venv/bin/activate && python -m pytest tests/ -v

# 2. Execute with concise short traceback
python -m pytest tests/ --tb=short

# 3. Execute individual domain test suites
python -m pytest tests/test_day2.py -v       # Cleaning & Validation
python -m pytest tests/test_day3.py -v       # SQL KPI Views
python -m pytest tests/test_day6.py -v       # Cryptographic Lineage
python -m pytest tests/test_day7.py -v       # AI Query Security
python -m pytest tests/test_world_bank.py -v # World Bank Ingestion
python -m pytest tests/test_ml_and_ai.py -v  # ML & Grounded AI

# 4. Execute Power BI SQL Parity Validator
python -m src.power_bi_validator
```
