# TraceImpact — Data Quality Scorecard & Observability Architecture

**Document Version:** 1.0.0  
**Status:** Production Ready  
**Milestone:** Day 4 Completed  

---

## 1. Overview & Business Rationale

Small and mid-size nonprofits rely heavily on fragmented spreadsheets for tracking field activities, attendance, donor expenditures, and client evaluations. In reality, operational data is inherently imperfect—manual typos, double-entry, missing fields, and mismatched formats are ubiquitous.

Traditional reporting tools suffer from two dangerous extremes:
1. **Silent Dropping**: Discarding imperfect rows hides real operational reach and distorts impact.
2. **Blind Ingestion**: Accepting invalid data (e.g. negative costs, scores > 100, phantom IDs) skews donor reports and breaches fiduciary compliance.

**TraceImpact** adopts **Data Observability & Non-Destructive Validation**:
- Every raw row is immutable and cryptographically staged in JSONB (`source_records`).
- Anomalies are systematically cataloged in `data_quality_issues` with exact coordinates (`file_id`, `row_number`, `column_name`, `record_id`).
- Blocking defects (`ERROR`) are quarantined from business reporting tables.
- Benign formatting issues (`INFO`) are auto-sanitized and marked `RESOLVED`.
- Ambiguous items (`WARNING`) are flagged `OPEN` for administrative triage.

---

## 2. Issue Severity Classification

| Severity | Definition | Operational Action | Database Count | % of Total |
| :--- | :--- | :--- | :---: | :---: |
| **`ERROR`** | Critical violation of entity constraints, negative financials, duplicate primary keys, or orphan foreign keys. | **Quarantined from domain tables.** Prevents metric skew. | 10 | 5.65% |
| **`WARNING`** | Missing optional demographic data, suspicious values, or soft duplicate signatures. | **Loaded with caution.** Flagged `OPEN` for administrative review. | 12 | 6.78% |
| **`INFO`** | Syntactic, casing, or currency formatting variations successfully cleaned by normalizers. | **Sanitized & Loaded.** Status set to `RESOLVED` at ingestion. | 155 | 87.57% |
| **Total** | | | **177** | **100.0%** |

---

## 3. Issue Lifecycle Management

Every detected anomaly transitions through a controlled lifecycle:

```
[ Anomaly Detected ] ──► OPEN (Awaiting Review / Quarantined)
                             │
                             ├─────► RESOLVED (Sanitized by normalizer or fixed by admin)
                             │
                             └─────► ACCEPTED (Reviewed & acknowledged as valid domain variance)
```

- **`OPEN`**: Default state for unverified anomalies. All 10 `ERROR`, 12 `WARNING`, and 6 `INFO` (missing phone) remain `OPEN` for human triage.
- **`RESOLVED`**: Issue resolved automatically by pipeline normalizers (149 `INFO` records) or manually corrected. Includes `resolved_at` timestamp.
- **`ACCEPTED`**: Administrator formally acknowledges the data defect as acceptable domain variance (e.g. participant without recorded age).

---

## 4. Production SQL Views

### 1. `v_data_quality_summary`
- **Grain**: 1-row executive summary.
- **Key Columns**:
  - `total_issues`: Total cataloged anomalies (177).
  - `error_count`, `warning_count`, `info_count`: Severity breakdown.
  - `open_count`, `resolved_count`, `accepted_count`: Lifecycle breakdown.
  - `resolution_percentage`: `((resolved + accepted) / total_issues) * 100` (84.18%).
  - `clean_record_rate`: `((total_records - errors) / total_records) * 100` (98.72%).

### 2. `v_data_quality_by_file`
- **Grain**: Source CSV file (`sf.file_id`, `sf.file_name`).
- **Key Columns**: `source_file_id`, `filename`, `total_issues`, `error_count`, `warning_count`, `info_count`, `open_count`, `resolved_count`.
- **Finding**: `attendance.csv` contains the highest volume of formatting normalizations (133 INFO, 6 ERROR); `programs.csv` has 0 defects.

### 3. `v_data_quality_by_program`
- **Grain**: Program (`p.program_id`, `p.program_name`) + `UNASSIGNED`.
- **Safe Handling**: Organization-wide intake records (from `beneficiaries.csv`) and blank program codes are explicitly preserved under `UNASSIGNED` (17 issues) rather than silently dropped.

### 4. `v_data_quality_by_type`
- **Grain**: Anomaly type (`issue_type`).
- **Distribution**:
  - `INCONSISTENT_VALUE`: 133
  - `MISSING_VALUE`: 17
  - `INVALID_FORMAT`: 16
  - `DUPLICATE`: 7
  - `INVALID_NUMBER`: 2
  - `UNMATCHED_REFERENCE`: 2

### 5. `v_data_quality_blocking`
- **Grain**: Individual active blocking defect.
- **Filter**: `severity = 'ERROR' AND status = 'OPEN'`.
- **Purpose**: Feeds the quarantine review list for nonprofit operations. Exactly 10 records.

---

## 5. Data Reliability Scoring Methodology

Rather than arbitrary deductions (e.g. `100 - errors * 10`), TraceImpact implements transparent, defensible metrics:

1. **Clean Record Rate (CRR):**
   $$\text{CRR} = \frac{\text{Total Source Records} - \text{Quarantined Error Records}}{\text{Total Source Records}} \times 100 = \frac{784 - 10}{784} \times 100 = 98.72\%$$
   *Interpretation*: 98.72% of all ingested raw records satisfy integrity constraints and are admitted into analytics.

2. **Resolution Rate (RR):**
   $$\text{RR} = \frac{\text{Resolved Issues} + \text{Accepted Issues}}{\text{Total Cataloged Issues}} \times 100 = \frac{149 + 0}{177} \times 100 = 84.18\%$$
   *Interpretation*: 84.18% of all identified anomalies have been systematically resolved.

3. **Data Reliability Index (DRI - Composite Metric):**
   $$\text{DRI} = (0.60 \times \text{CRR}) + (0.20 \times \text{RR}) + (0.20 \times (100 - \text{Error Rate}))$$
   $$\text{DRI} = (0.60 \times 98.72) + (0.20 \times 84.18) + (0.20 \times 94.35) = 94.94 / 100$$
   *Interpretation*: A balanced 0–100 index weighted towards business data admissibility (60%), automated triage throughput (20%), and error containment (20%).
