# TraceImpact — Cryptographic Traceability & Lineage Architecture

**Document Version:** 1.0.0  
**Status:** Production Ready  
**Milestone:** Day 6 Completed  

---

## 1. The Core Problem: Auditability in Impact Reporting

Nonprofits and philanthropic foundations face intense scrutiny regarding fund allocation and reported beneficiary impact. Traditional reporting dashboards present aggregated metrics (e.g. "42 beneficiaries served", "₹130,311 spent") without providing proof of the underlying transactions. When auditors or donors ask:

> **"Where did this specific number come from, and can you prove it wasn't fabricated or distorted?"**

Legacy systems fail because data transformations, deduplications, and cleaning steps discard intermediate data and sever links to original source files.

---

## 2. The 1-to-1 Cryptographic Lineage Chain

**TraceImpact** guarantees complete, bi-directional traceability across every layer of the platform:

```
Dashboard KPI / Report
        │
        ▼
PostgreSQL Analytical View (`v_program_reach`, `v_program_kpis`)
        │
        ▼
Domain Table Row (`attendance`, `expenses`, `beneficiaries`, `outcomes`)
        │ (Foreign Key: source_record_id)
        ▼
Raw Staging Table (`source_records`)
        │ [Stores verbatim raw_data as JSONB]
        │ [Stores exact row_index coordinate]
        │ (Foreign Key: file_id)
        ▼
File Provenance Table (`source_files`)
        │ [Stores SHA-256 cryptographic hash]
        │ [Stores ingestion timestamp & total row count]
        ▼
Physical Raw CSV on Local Disk (`data/raw/<filename>`)
        [Exact row index read-only verification]
```

---

## 3. Concrete End-to-End Lineage Demonstration

### Example A: Trace of Attendance Check-In (Source Record ID #51)

1. **Dashboard KPI**:
   - `PRG-004` (Elderly Healthcare Outreach) reports 128 total check-ins in `v_program_reach`.
2. **Domain Table Record (`attendance`)**:
   - Row ID: `attendance_id = 'ATT-0051'`
   - Participant: `BEN-011`
   - Session Date: `2024-02-04`
   - Session Hours: `2.00`
   - Foreign Anchor: `source_record_id = 51`
3. **JSONB Staging Record (`source_records`)**:
   - `record_id = 51`
   - `file_id = 2`
   - `row_index = 51`
   - `raw_data = {"session_date": "2024-02-04", "attendance_id": "ATT-0051", "program_title": "Elderly Healthcare Outreach", "session_hours": "2 hrs", "participant_id": "BEN-011", "attendance_status": "Present"}`
4. **Source File Provenance (`source_files`)**:
   - `file_id = 2`
   - `file_name = attendance.csv`
   - `file_hash = c35bcf948c31d0aa0dc937eb7df36bbdcfd746d8fc7eef6f0ca2cb637b51e069`
5. **Physical Raw CSV on Disk (`data/raw/attendance.csv`)**:
   - Line 52 (header + row 51):
     `ATT-0051,BEN-011,Elderly Healthcare Outreach,2024-02-04,Present,2 hrs`
   - **Verification**: Byte-for-byte exact match confirmed between disk and database JSONB.
6. **Data Quality Audit Linked (`data_quality_issues`)**:
   - Issue #204: `INCONSISTENT_VALUE` (INFO) — `"Session hours '2 hrs' normalized to numeric 2.00."` Status: `RESOLVED`.

---

## 4. Lineage on Quarantined / Anomaly Records

Traceability is not limited to clean data. When a record is quarantined due to a data quality violation, **its provenance is fully preserved**:

### Example B: Quarantined Negative Expense (Source Record ID #686)
- **Data Quality Anomaly**: Issue #349 (`INVALID_NUMBER`, Severity: `ERROR`)
  - Description: `"Expense 'EXP-0068' has negative amount: -4500.00. Financial rules disallow negative expenditures."`
  - Status: `OPEN`
- **Domain Table Check**: The record does **NOT** exist in `expenses`, proving the quarantine boundary prevented metric distortion.
- **Source Record Lineage**:
  - `record_id = 686`
  - `file_name = expenses.csv` (Row 68)
  - `raw_data = {"expense_ref": "EXP-0068", "amount_spent": "-4500.0", "program_code": "PRG-001", "incurred_date": "2024-03-12", "expense_category": "Refreshments", "receipt_verified": "Yes"}`
  - Proves the entry error occurred in the field spreadsheet, not during pipeline transformation.

---

## 5. Traceability UI Features (`pages/4_Traceability.py`)

1. **Multi-Modal Investigation**:
   - **Pathway A (Program ➔ Domain)**: Select an initiative and domain entity, view live table records, and click to inspect the underlying source record.
   - **Pathway B (Data Quality ➔ Source Record)**: Select an anomaly from the issue log to instantly locate its source row and file coordinates.
   - **Pathway C (Direct ID Lookup)**: Enter any integer `source_record_id` (1 to 784) for instant full-spectrum lineage.
2. **Visual Inspection Components**:
   - Cleaned Business Entity view (`st.json()`).
   - Verbatim Raw JSONB Staging (`st.json()`).
   - Cryptographic SHA-256 Provenance Fingerprint (`st.code()`).
   - Physical Raw CSV File & Line coordinates read directly from disk.
   - Associated Data Quality Anomaly Log.

---

## 6. PII Protection Within Lineage

While raw JSONB records contain field entries, domain tables and analytical views strictly protect individual privacy:
- Beneficiary identities are pseudonymized via salted SHA-256 hashing into `anonymized_code`.
- High-level reports reference only aggregated counts or pseudonymous codes.
- Direct raw names remain strictly isolated within the raw staging partition.

---

## 7. TraceImpact 2.0: Real Public Data & AI Investigation Lineage

TraceImpact 2.0 extends cryptographic lineage to external REST APIs, machine learning anomaly detection, and AI-assisted investigations.

### The 7-Step Source-to-Insight Verification Chain

```
[Step 1] AI Grounded Insight (`ai_insights`)
            │ (insight_id, title, underlying_metrics)
            ▼
[Step 2] AI Investigation (`ai_investigations`)
            │ (finding_summary, structured_evidence, limitations)
            ▼
[Step 3] Machine Learning Anomaly (`world_bank_anomalies`)
            │ (model_name, model_version, anomaly_score, feature_snapshot)
            ▼
[Step 4] Normalized Observation (`world_bank_observations`)
            │ (country_code, indicator_code, year, indicator_value)
            ▼
[Step 5] Raw Bronze API Payload (`api_raw_responses`)
            │ (verbatim JSON array element at raw_record_index)
            ▼
[Step 6] Cryptographic SHA-256 Fingerprint (`api_raw_responses.response_hash`)
            │ (guarantees API response page payload immutability)
            ▼
[Step 7] Ingestion Batch Run Provenance (`api_ingestion_runs`)
            (run_id, source_name, endpoint_url, timestamp, duration)
```

### Verification via SQL View (`v_world_bank_ai_lineage`)

Auditors and users can query the unified view:
```sql
SELECT 
    insight_title,
    anomaly_score,
    indicator_name,
    country_name,
    year,
    indicator_value,
    response_hash,
    run_id
FROM v_world_bank_ai_lineage
WHERE insight_id = 1;
```

This guarantees that an AI insight is never an ungrounded hallucination: it is anchored in an empirical ML anomaly, a verified database observation, and an immutable SHA-256 hashed API payload.
