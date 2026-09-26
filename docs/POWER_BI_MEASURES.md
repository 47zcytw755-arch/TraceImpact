# TraceImpact 2.0 — Power BI DAX Measure Library & Formula Reference

> **Overview**: This document provides the complete, production-grade DAX (Data Analysis Expressions) formula reference for all calculated KPIs and metrics in the TraceImpact 2.0 Power BI model. Every DAX formula includes explicit data provenance tags (`[REAL]`, `[MEASURED]`, `[SIMULATED]`, `[PROJECTED]`) and exact PostgreSQL verification SQL.

---

## Folder Structure in `_Measures` Table

All DAX measures are centralized in the `_Measures` table and structured into 9 domain display folders:

```
_Measures
├── 01_Executive
├── 02_BeforeAfter
├── 03_DataQuality
├── 04_PublicData
├── 05_MLAnomalies
├── 06_AIInvestigations
├── 07_Ingestion
├── 08_StressTest
└── 09_Lineage
```

---

## 1. Executive Overview Measures (`01_Executive`)

### 1.1 Total Synthetic Records `[SIMULATED]`

```dax
Total Synthetic Records = 
-- Description: Counts total source CSV records processed in the synthetic nonprofit pipeline.
-- Data Provenance: [SIMULATED]
CALCULATE(
    COUNTROWS(Fact_ExecKPIs),
    Fact_ExecKPIs[pipeline_name] = "Synthetic Nonprofit Pipeline"
)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM source_records; -- Result: 784
  ```

### 1.2 Synthetic Clean Record Rate % `[MEASURED]`

```dax
Synthetic Clean Record Rate % = 
-- Description: Calculates percentage of synthetic source records free of blocking quality errors.
-- Formula: (Total Records - Blocking Errors) / Total Records
-- Data Provenance: [MEASURED]
VAR TotalRec = [Total Synthetic Records]
VAR Errors = CALCULATE(
    COUNTROWS(Fact_DataQuality),
    Fact_DataQuality[source_pipeline] = "Synthetic",
    Fact_DataQuality[severity] = "ERROR",
    Fact_DataQuality[status] = "OPEN"
)
RETURN
DIVIDE(TotalRec - COALESCE(Errors, 0), TotalRec, 0) * 100
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT clean_record_rate FROM v_data_quality_summary; -- Result: 98.72%
  ```

### 1.3 Total World Bank Observations `[REAL]`

```dax
Total World Bank Observations = 
-- Description: Total clean public development indicator observations stored in PostgreSQL.
-- Data Provenance: [REAL]
COUNTROWS(Fact_PublicExplorer)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM world_bank_observations; -- Result: 5,588
  ```

### 1.4 Overall Data Quality Score `[MEASURED]`

```dax
Overall Data Quality Score = 
-- Description: Composite weighted data quality score across all active pipeline datasets.
-- Data Provenance: [MEASURED]
AVERAGE(Fact_ExecKPIs[dq_score_pct])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT AVG(dq_score_pct) FROM v_pbi_executive_kpis; -- Result: 99.36%
  ```

---

## 2. Before vs After Measures (`02_BeforeAfter`)

### 2.1 Raw Issues Count `[MEASURED]`

```dax
Raw Issues Count = 
-- Description: Total raw data quality issues detected in uncleaned incoming data.
-- Data Provenance: [MEASURED]
SUM(Fact_BeforeAfter[raw_issues_count])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT SUM(raw_issues_count) FROM v_pbi_before_after; -- Result: 899 (177 synthetic + 722 WB)
  ```

### 2.2 Resolved Issues Count `[MEASURED]`

```dax
Resolved Issues Count = 
-- Description: Total data quality issues resolved or gracefully logged by automated rules.
-- Data Provenance: [MEASURED]
SUM(Fact_BeforeAfter[processed_resolved_issues])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT SUM(processed_resolved_issues) FROM v_pbi_before_after; -- Result: 871 (149 synthetic + 722 WB)
  ```

### 2.3 Overall Resolution Rate % `[MEASURED]`

```dax
Overall Resolution Rate % = 
-- Description: Percentage of total data quality issues successfully resolved by the pipeline.
-- Data Provenance: [MEASURED]
DIVIDE([Resolved Issues Count], [Raw Issues Count], 0) * 100
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT (SUM(processed_resolved_issues)::numeric / SUM(raw_issues_count)) * 100 FROM v_pbi_before_after; -- Result: 96.89%
  ```

---

## 3. Data Quality Intelligence Measures (`03_DataQuality`)

### 3.1 Total DQ Issues `[MEASURED]`

```dax
Total DQ Issues = 
-- Description: Count of all logged data quality issues across synthetic and public data.
-- Data Provenance: [MEASURED]
COUNTROWS(Fact_DataQuality)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM v_pbi_data_quality_fact; -- Result: 899
  ```

### 3.2 Error Count `[MEASURED]`

```dax
Error Count = 
-- Description: Count of critical, blocking data quality errors requiring quarantine.
-- Data Provenance: [MEASURED]
CALCULATE(
    [Total DQ Issues],
    Fact_DataQuality[severity] = "ERROR"
)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM v_pbi_data_quality_fact WHERE severity = 'ERROR'; -- Result: 10
  ```

### 3.3 Warning Count `[MEASURED]`

```dax
Warning Count = 
-- Description: Count of non-blocking data quality warnings requiring review.
-- Data Provenance: [MEASURED]
CALCULATE(
    [Total DQ Issues],
    Fact_DataQuality[severity] = "WARNING"
)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM v_pbi_data_quality_fact WHERE severity = 'WARNING'; -- Result: 12
  ```

### 3.4 Info Count `[MEASURED]`

```dax
Info Count = 
-- Description: Count of informational notices (e.g. missing historical values logged gracefully).
-- Data Provenance: [MEASURED]
CALCULATE(
    [Total DQ Issues],
    Fact_DataQuality[severity] = "INFO"
)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM v_pbi_data_quality_fact WHERE severity = 'INFO'; -- Result: 877 (155 synthetic + 722 WB)
  ```

---

## 4. Public Data Explorer Measures (`04_PublicData`)

### 4.1 Countries Reporting `[REAL]`

```dax
Countries Reporting = 
-- Description: Count of unique sovereign countries reporting indicator data.
-- Data Provenance: [REAL]
DISTINCTCOUNT(Fact_PublicExplorer[country_code])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(DISTINCT country_code) FROM v_pbi_public_data_explorer; -- Result: 264
  ```

### 4.2 Indicator Average Value `[REAL]`

```dax
Indicator Average Value = 
-- Description: Average indicator value across selected countries and years.
-- Data Provenance: [REAL]
AVERAGE(Fact_PublicExplorer[indicator_value])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT AVG(indicator_value) FROM v_pbi_public_data_explorer;
  ```

### 4.3 Year-over-Year Growth % `[REAL]`

```dax
Year-over-Year Growth % = 
-- Description: Average annual YoY percentage change for public development indicators.
-- Data Provenance: [REAL]
AVERAGE(Fact_PublicExplorer[yoy_growth_pct])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT AVG(yoy_growth_pct) FROM v_pbi_public_data_explorer WHERE yoy_growth_pct IS NOT NULL;
  ```

---

## 5. ML Anomaly Intelligence Measures (`05_MLAnomalies`)

### 5.1 ML Flagged Anomaly Count `[MEASURED]`

```dax
ML Flagged Anomaly Count = 
-- Description: Number of public data observations flagged as anomalies by Isolation Forest.
-- Data Provenance: [MEASURED]
CALCULATE(
    COUNTROWS(Fact_MLAnomalies),
    Fact_MLAnomalies[is_anomaly] = TRUE
)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM world_bank_anomalies WHERE is_anomaly = True; -- Result: 783
  ```

### 5.2 Anomaly Rate % `[MEASURED]`

```dax
Anomaly Rate % = 
-- Description: Percentage of total evaluated observations flagged as statistical anomalies.
-- Data Provenance: [MEASURED]
DIVIDE([ML Flagged Anomaly Count], [Total World Bank Observations], 0) * 100
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT (COUNT(CASE WHEN is_anomaly THEN 1 END)::numeric / COUNT(*)) * 100 FROM world_bank_anomalies; -- Result: 14.01%
  ```

### 5.3 Average Anomaly Score `[MEASURED]`

```dax
Average Anomaly Score = 
-- Description: Mean anomaly score assigned by Isolation Forest (higher = more anomalous).
-- Data Provenance: [MEASURED]
AVERAGE(Fact_MLAnomalies[anomaly_score])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT AVG(anomaly_score) FROM world_bank_anomalies;
  ```

---

## 6. AI Investigation Measures (`06_AIInvestigations`)

### 6.1 Total AI Investigations `[MEASURED]`

```dax
Total AI Investigations = 
-- Description: Total number of ML anomalies investigated by the LLM AI Engine.
-- Data Provenance: [MEASURED]
COUNTROWS(Fact_AIInvestigations)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM ai_investigations; -- Result: 6
  ```

### 6.2 AI Insights Generated `[MEASURED]`

```dax
AI Insights Generated = 
-- Description: Total structured AI insights produced from evidence-backed investigations.
-- Data Provenance: [MEASURED]
CALCULATE(
    DISTINCTCOUNT(Fact_AIInvestigations[insight_id]),
    NOT(ISBLANK(Fact_AIInvestigations[insight_id]))
)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM ai_insights; -- Result: 17
  ```

---

## 7. Pipeline & Ingestion Monitor Measures (`07_Ingestion`)

### 7.1 Total Ingestion Runs `[MEASURED]`

```dax
Total Ingestion Runs = 
-- Description: Total automated REST API ingestion runs executed by the scheduler.
-- Data Provenance: [MEASURED]
COUNTROWS(Fact_IngestionMonitor)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM api_ingestion_runs; -- Result: 43
  ```

### 7.2 Successful Ingestion Runs `[MEASURED]`

```dax
Successful Ingestion Runs = 
-- Description: Number of ingestion runs completed with COMPLETED status.
-- Data Provenance: [MEASURED]
CALCULATE(
    [Total Ingestion Runs],
    Fact_IngestionMonitor[run_status] = "COMPLETED"
)
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT COUNT(*) FROM api_ingestion_runs WHERE status = 'COMPLETED'; -- Result: 43
  ```

### 7.3 Average Ingestion Run Duration (s) `[MEASURED]`

```dax
Average Ingestion Run Duration (s) = 
-- Description: Mean wall-clock time in seconds for World Bank API ingestion runs.
-- Data Provenance: [MEASURED]
AVERAGE(Fact_IngestionMonitor[duration_seconds])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT AVG(COALESCE(duration_seconds, EXTRACT(EPOCH FROM (completed_at - started_at)))) FROM api_ingestion_runs;
  ```

---

## 8. Scale & Stress Test Measures (`08_StressTest`)

### 8.1 Measured Throughput RPS `[MEASURED]`

```dax
Measured Throughput RPS = 
-- Description: Records processed per second recorded during the 100,000 stress test harness run.
-- Data Provenance: [MEASURED]
MAX(Fact_StressTest[throughput_rps])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT MAX(throughput_rps) FROM v_pbi_stress_test_benchmarks; -- Result: 22,215.4 RPS
  ```

### 8.2 Measured Peak Memory MB `[MEASURED]`

```dax
Measured Peak Memory MB = 
-- Description: Peak RAM consumption in megabytes recorded during full system validation.
-- Data Provenance: [MEASURED]
MAX(Fact_StressTest[peak_ram_mb])
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT MAX(peak_ram_mb) FROM v_pbi_stress_test_benchmarks; -- Result: 416.64 MB
  ```

---

## 9. Lineage & Traceability Measures (`09_Lineage`)

### 9.1 Lineage Success Rate % `[MEASURED]`

```dax
Lineage Success Rate % = 
-- Description: Percentage of observations with unbroken 7-step lineage from API to AI insight.
-- Data Provenance: [MEASURED]
VAR TotalLineageRecs = COUNTROWS(Fact_Lineage)
VAR ValidLineageRecs = CALCULATE(
    COUNTROWS(Fact_Lineage),
    NOT(ISBLANK(Fact_Lineage[response_hash]))
)
RETURN
DIVIDE(ValidLineageRecs, TotalLineageRecs, 0) * 100
```
- **PostgreSQL Verification SQL**:
  ```sql
  SELECT (COUNT(response_hash)::numeric / COUNT(*)) * 100 FROM v_pbi_end_to_end_lineage; -- Result: 100.0%
  ```
