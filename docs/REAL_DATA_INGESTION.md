# Real Public Data Ingestion — TraceImpact 2.0

**Document Version:** 2.0.0  
**Data Domain:** Global Macroeconomic & Social Indicators  
**Data Provider:** World Bank Indicators API (`api.worldbank.org/v2`)  
**Authentication:** Public / No API Key Required  

---

## 1. Why Real Public Data Was Added

TraceImpact Day 1–7 demonstrated an end-to-end data engineering platform using a controlled synthetic nonprofit dataset for deterministic auditing and portfolio demonstration.

To prove that TraceImpact is a reusable, generalizable data platform—and not merely a hardcoded dashboard—**TraceImpact 2.0** introduces a second, real-world data ingestion pipeline. This pipeline ingests real public indicators directly from the World Bank API, applying the same rigor:
1. **Bronze Layer:** Verbatim raw API response staging in PostgreSQL as JSONB alongside SHA-256 cryptographic fingerprints.
2. **Silver Layer:** Schema validation, missing-value handling, anomaly quarantine, and normalized relational dimensions.
3. **Gold Layer:** Production-quality analytical SQL views for multi-year trends, latest values, and regional comparisons.
4. **End-to-End Lineage:** 1-to-1 traceability from dashboard metrics back to raw API page payloads and request metadata.

> [!NOTE]
> **Data Domain Separation:** The nonprofit impact dataset in TraceImpact remains synthetic and is used for deterministic testing and demonstration. The Public Data Explorer uses real public data retrieved from the World Bank API. World Bank data is maintained in dedicated tables and is not mixed with nonprofit operations.

---

## 2. API Source & Endpoint Specifications

- **Base URL:** `http://api.worldbank.org/v2`
- **Indicator Endpoint:** `/country/all/indicator/{indicator_code}`
- **Response Format:** JSON (`format=json`)
- **Query Parameters:**
  - `date`: Chronological year range (e.g., `2018:2021`)
  - `per_page`: Number of records per page (default: `500`, max allowed: `1000`)
  - `page`: 1-based page index

### Curated Development Indicators:
1. **`NY.GDP.PCAP.CD`**: GDP per capita (current US$)
2. **`SP.POP.TOTL`**: Population, total
3. **`SP.DYN.LE00.IN`**: Life expectancy at birth, total (years)
4. **`SH.H2O.BASW.ZS`**: People using at least basic drinking water services (% of population)

---

## 3. Resilient Ingestion Architecture

### Module Structure
```
src/
├── ingestion/
│   ├── api_client.py          # Resilient HTTP client (timeout, retry, backoff, SHA-256)
│   ├── ingestion_metadata.py  # Run tracking & raw bronze response persistence
│   └── world_bank.py          # Orchestration, pagination & database upsert pipeline
├── quality/
│   └── world_bank_quality.py  # Schema validation & DQ issue persistence
└── dashboard/
    └── queries.py             # Query layer for analytical views & lineage
```

### Ingestion Flow:
```
World Bank REST API
       ↓ HTTP GET (per_page=500, with exponential backoff)
APIClient (Status 200, SHA-256 calculation)
       ↓
api_raw_responses (Bronze Layer: raw_payload JSONB + response_hash)
       ↓
WorldBankValidator (Rule-based schema & range checks)
       ├─ Clean records ➔ world_bank_observations (Silver Layer UPSERT)
       └─ Anomalies     ➔ world_bank_data_quality_issues (Audit Log)
       ↓
SQL Analytical Views (Gold Layer: v_world_bank_*)
       ↓
Streamlit Page 6 (Public Data Explorer)
```

---

## 4. Pagination & Bronze Storage

The World Bank API splits responses into two top-level JSON elements:
- `response[0]`: Pagination metadata (`page`, `pages`, `per_page`, `total`)
- `response[1]`: Array of observation objects

The pipeline reads `pages` and iterates until all pages are retrieved. Each page response is persisted in `api_raw_responses` before any cleaning occurs:
- `run_id`: Foreign key to `api_ingestion_runs`
- `page_number`: 1-based page coordinate
- `response_hash`: 64-character SHA-256 hex digest of the raw response payload
- `raw_payload`: Complete JSON array preserved verbatim as PostgreSQL JSONB

---

## 5. Cleaning & Data Quality Validation

Observations undergo automated validation via `WorldBankValidator`:
- **Country Code:** Validates existence of ISO2/ISO3 country identifiers.
- **Indicator Code:** Validates presence of standard indicator symbol.
- **Year Bounds:** Validates integer format and expected historical bounds (1960–2030).
- **Metric Value:** Validates float/numeric format.
  - Non-numeric strings are flagged with `INVALID_NUMERIC` (`ERROR` severity) and quarantined.
  - Missing/null values are cataloged with `MISSING_VALUE` (`INFO` severity). Null observations are omitted from the active observations table to prevent metric skew.

---

## 6. PostgreSQL Relational Model

### Tables Created:
1. `api_ingestion_runs`: Execution logs (run ID, endpoint, params, status, counts, timestamps).
2. `api_raw_responses`: Bronze layer immutable raw payloads.
3. `world_bank_countries`: Country dimension (country code, name, ISO3 code, region).
4. `world_bank_indicators`: Indicator dimension (indicator code, name, topic, unit of measure).
5. `world_bank_observations`: Cleaned silver observations with foreign keys to dimensions and `api_raw_responses`.
   - **Unique Constraint:** `(country_code, indicator_code, year)` ensures idempotent loading.
6. `world_bank_data_quality_issues`: Audit trail of detected public data anomalies.

---

## 7. Gold Layer SQL Analytical Views

Created in `sql/views_world_bank.sql`:
1. **`v_world_bank_latest_indicators`**: Most recent reported observation per country using PostgreSQL `DISTINCT ON`.
2. **`v_world_bank_country_trends`**: Multi-year trends with YoY absolute change and % growth using window function `LAG()`.
3. **`v_world_bank_indicator_summary`**: Global descriptive statistics (mean, min, max, stddev, country count) per year.
4. **`v_world_bank_regional_comparison`**: Regional benchmarks comparing average indicator performance across continents.
5. **`v_world_bank_data_quality_summary`**: Ingestion health scorecard, issue counts, and clean record percentage.

---

## 8. Traceability & Lineage

The system provides complete 1-to-1 lineage for any public indicator observation:
```
Dashboard Observation
       ↓ (observation_id)
world_bank_observations
       ↓ (raw_response_id, raw_record_index)
api_raw_responses (raw_payload JSONB array at index offset)
       ↓ (run_id, response_hash)
api_ingestion_runs (endpoint, query parameters, ingestion timestamp)
```

Users can select a country, indicator, and year on the **Public Data Explorer** page (`pages/6_Public_Data_Explorer.py`) to inspect the cleaned observation, view the verbatim JSON payload from the bronze staging table, and verify the cryptographic SHA-256 fingerprint.

---

## 9. Automated Scheduler & Execution Operations

### Scheduler Architecture
TraceImpact 2.0 incorporates a lightweight, pure-Python background scheduler (`src/ingestion/scheduler.py`). It avoids heavy infrastructure dependencies like Apache Airflow, Kafka, or Celery while delivering enterprise-grade operational controls:
- **Configurable Cadence:** Configured via `PIPELINE_SCHEDULE_INTERVAL_HOURS` (defaults to `24.0` hours for daily batch execution).
- **Graceful Signal Handling:** Intercepts `SIGINT` and `SIGTERM` for clean shutdown without corrupting database transactions.
- **Safe Development Mode:** Includes a `--once` flag to execute a single scheduled pass and exit immediately, preventing runaway background loops during local testing or CI/CD pipelines.
- **Dynamic Year Horizon:** Computes historical lookback window (`PIPELINE_LOOKBACK_YEARS`, default 3) dynamically relative to system time.

### Configuration Parameters (.env)
```ini
# Cadence between automated scheduled runs (in hours; default: 24 for daily)
PIPELINE_SCHEDULE_INTERVAL_HOURS=24

# Whether scheduler immediately runs an initial ingestion on startup (default: true)
PIPELINE_RUN_ON_STARTUP=true

# Historical reporting span to fetch per indicator (in years; default: 3)
PIPELINE_LOOKBACK_YEARS=3
```

### Execution Commands

```bash
# 1. Start continuous automated scheduler (runs every 24 hours in background)
.venv/bin/python -m src.ingestion.scheduler

# 2. Start scheduler with custom 12-hour cadence
.venv/bin/python -m src.ingestion.scheduler --interval-hours 12.0

# 3. Safe Development / CI Mode: Execute exactly one scheduled run and exit immediately
.venv/bin/python -m src.ingestion.scheduler --once

# 4. Manual on-demand execution for specific indicator and custom year range
.venv/bin/python -m src.ingestion.world_bank --indicators NY.GDP.PCAP.CD --start-year 2018 --end-year 2021

# 5. Execute full regression test suite (85 tests passing)
.venv/bin/python -m pytest -v
```

---

## 10. Ingestion Monitoring & Failure Troubleshooting

### Inspecting Ingestion History
All automated and manual executions are recorded in the PostgreSQL audit table `api_ingestion_runs`:
```sql
SELECT run_id, source_name, run_type, status, records_inserted, records_updated, records_quarantined, duration_seconds, started_at, completed_at, error_message
FROM api_ingestion_runs
ORDER BY run_id DESC
LIMIT 10;
```
This data is also rendered interactively in **Page 6: Public Data Explorer** in the *Pipeline Automation & Ingestion Execution History* section.

### Failure Handling & Isolation
1. **Network Timeouts / HTTP 429:** `APIClient` automatically retries requests up to 3 times with exponential backoff (`backoff_factor=1.5`).
2. **Fatal API Failure:** If an indicator run fails after maximum retries, the run is marked as `FAILED` with the exact error message preserved in `error_message`. Existing valid records in `world_bank_observations` remain completely untouched (no partial overwrites or rollbacks of prior successful runs).
3. **Data Quality Anomalies:** Individual malformed records (e.g. invalid date formats, non-numeric values) are quarantined in `world_bank_data_quality_issues` without halting the ingestion of valid rows.

