# TraceImpact Data Pipeline & Quality Framework (Day 2)

## 1. End-to-End Pipeline Architecture

TraceImpact implements a **non-destructive, traceable data pipeline**. Raw input files are never overwritten or altered; instead, raw records are staged as JSONB in PostgreSQL, cleansed via declarative functional transformers, verified against data quality rules, exported to a clean data lake staging directory (`data/processed/`), and loaded into normalized domain relational tables.

```
+-------------------------------------------------------------------------------+
|                             RAW CSV DATA LAKE                                 |
| data/raw/{programs, beneficiaries, attendance, expenses, outcomes}.csv         |
+-------------------------------------------------------------------------------+
                                      |
                                      v (SHA-256 Provenance & JSONB Staging)
+-------------------------------------------------------------------------------+
|                       IMMUTABLE STAGING TABLES (Day 1)                        |
|   source_files (hash, total_rows) <---> source_records (record_id, raw JSONB)  |
+-------------------------------------------------------------------------------+
                                      |
                                      v (python -m src.cleaning.run_pipeline)
+-------------------------------------------------------------------------------+
|                         DATA CLEANING & VALIDATION                            |
| 1. Column Name Normalization (explicit canonical maps)                        |
| 2. Categorical & Entity Resolution (program aliases, city locations, gender)  |
| 3. Type Coercion & Sanitization (dates: ISO/UK/US, currency: ₹/$, units: hrs)  |
| 4. Anomaly & Rule Validation (duplicates, negative values, orphan refs)       |
+-------------------------------------------------------------------------------+
                 |                                              |
                 v (Cleaned Datasets)                           v (Quarantine / Audit)
+---------------------------------------+   +-----------------------------------+
|      PROCESSED STORAGE ARTIFACTS      |   |        DATA QUALITY AUDIT         |
| data/processed/*.csv                  |   | data_quality_issues table         |
| - beneficiaries.csv                   |   | - Issue types: DUPLICATE,         |
| - attendance.csv                      |   |   MISSING_VALUE, INVALID_NUMBER,  |
| - expenses.csv                        |   |   UNMATCHED_REFERENCE, etc.       |
| - outcomes.csv                        |   | - Severities: ERROR, WARNING, INFO|
+---------------------------------------+   +-----------------------------------+
                 |                                              ^
                 v (Foreign-Key Enforced Relational Load)       |
+---------------------------------------------------------------+---------------+
|                           POSTGRESQL DOMAIN TABLES                            |
| programs (master catalog)                                                     |
| beneficiaries  (source_record_id FK ---> source_records.record_id)            |
| attendance     (source_record_id FK, beneficiary_id FK, program_id FK)        |
| expenses       (source_record_id FK, program_id FK)                           |
| outcomes       (source_record_id FK, beneficiary_id FK, program_id FK)        |
+-------------------------------------------------------------------------------+
```

---

## 2. Column Name Normalization

Field staff, regional offices, and mobile forms use different header names for the same conceptual fields. Column normalization translates these variations into canonical attributes using explicit declarative mappings configured in `src/cleaning/column_maps.py`:

| Dataset | Source Header Variants | Canonical Field |
| :--- | :--- | :--- |
| **beneficiaries** | `beneficiaryId`, `participant_id`, `participant_code` | `beneficiary_id` |
| | `fullname`, `name` | `full_name` |
| | `location`, `city` | `city_location` |
| | `signup_date`, `registrationdate` | `registration_date` |
| | `phone`, `mobile` | `contact_phone` |
| **attendance** | `participant_id`, `participantId` | `beneficiary_id` |
| | `program_title`, `program`, `programName` | `program_name` |
| | `status` | `attendance_status` |
| | `hours` | `session_hours` |
| **expenses** | `expense_ref`, `expenseref` | `expense_id` |
| | `program_code`, `programid` | `program_id` |
| | `amount_spent`, `cost` | `amount` |
| | `expense_date`, `date` | `incurred_date` |
| | `verified` | `receipt_verified` |
| **outcomes** | `survey_id`, `surveyid` | `outcome_id` |
| | `client_identifier`, `participant_id` | `beneficiary_id` |
| | `metric_name`, `indicator` | `indicator_name` |
| | `survey_date`, `date` | `evaluation_date` |

---

## 3. Data Cleaning Rules

### A. Date Normalization
- **Challenge**: Raw files mix `YYYY-MM-DD` (ISO), `DD/MM/YYYY` (Indian/UK standard), and `MM/DD/YYYY` (US).
- **Transformation**: Sequential format matching parses string dates into canonical Python `datetime.date` objects (`YYYY-MM-DD`).
- **Rule**: Impossible dates (e.g. `2024-13-45`) fail parsing and produce an `INVALID_DATE` error issue. They are never coerced into epoch or dummy timestamps.

### B. Numeric & Currency Sanitization
- **Expenses**: Values formatted as `₹11,271.75` or `$9,116.77` have currency symbols, commas, and whitespace stripped using regular expressions, converting cleanly to `float` / SQL `NUMERIC(12, 2)`.
- **Attendance Hours**: Strings like `"2 hrs"` or `"2.5 hours"` have word units stripped to yield float numbers. Missing hours default to `0.0` with a logged notice.

### C. Program Title Resolution
- Free-text program names logged by field staff (e.g., `Digi-Literacy`, `digital literacy`, `Youth-Coding`, `Health Outreach`) are mapped via a controlled lookup table to official master program IDs (`PRG-001` through `PRG-005`).
- Unrecognized program names produce `UNMATCHED_REFERENCE` issues and are quarantined from domain tables.

### D. Geographic Location Normalization
- City variants such as `new delhi`, `Delhi`, `N. Delhi`, and `Delhi NCR` resolve to `"New Delhi"`.
- `Gurgaon` and `GURGAON` resolve to `"Gurugram"`.
- Standard title casing and whitespace trimming ensure uniform reporting without discarding valid unmapped cities (e.g., `"Bhubaneswar"`).

### E. Beneficiary Privacy & Anonymization
- In accordance with data protection best practices, personal full names and phone numbers are not published into public domain tables.
- A salted cryptographic hash (`SHA-256`) generates a deterministic `anonymized_code` for each participant, allowing longitudinal tracking across programs without exposing PII.

---

## 4. Validation Rules & Data Quality Issue Types

Every record is evaluated against business constraints. Issues are cataloged in `data_quality_issues`:

```
+---------------------------------------------------------------------------------+
| issue_id | file_id | record_id | row_num | column_name | issue_type | severity  |
+---------------------------------------------------------------------------------+
```

### Issue Types:
- `DUPLICATE`: Multiple records representing the same entity, identifier, or session check-in.
- `MISSING_VALUE`: Null or empty value in a required or optional field.
- `INVALID_DATE`: Date string that fails calendar parsing.
- `INVALID_NUMBER`: Impossible or out-of-range numeric value (e.g. negative costs, scores > 100).
- `UNMATCHED_REFERENCE`: Foreign key target not found in master catalog (e.g. orphan participant).
- `INCONSISTENT_VALUE`: Format variance successfully corrected (e.g. `"2 hrs"` -> `2.0`).
- `INVALID_FORMAT`: Complex formatted string sanitized (e.g. `"₹11,271.75"` -> `11271.75`).

### Severity Classification:
- **`ERROR`**: Blocking defect that violates domain integrity or relational constraints. **Record is quarantined from domain tables.** (e.g., negative expense, duplicate primary key, orphan participant, out-of-bounds score).
- **`WARNING`**: Non-blocking defect where data is missing or suspicious but usable. (e.g., missing participant age, missing phone, missing baseline score).
- **`INFO`**: Automated transformation notice indicating formatting sanitization occurred.

---

## 5. Duplicate Detection Rules

1. **Beneficiary Primary Key Duplication**:
   - Two rows sharing the exact same `beneficiary_id`.
   - Action: The first instance is retained; the duplicate is flagged with `DUPLICATE / ERROR` and excluded from `beneficiaries`.
2. **Beneficiary Identity Duplication (Same Person, Different ID)**:
   - A row with a different ID but identical normalized full name and phone number as an existing beneficiary.
   - Action: Flagged with `DUPLICATE / WARNING`. The record is loaded with a warning so field staff can merge identities later.
3. **Attendance Double-Logging**:
   - Multiple check-in rows for the same `beneficiary_id`, `program_id`, and `session_date`.
   - Action: First check-in kept; subsequent duplicate check-ins flagged with `DUPLICATE / ERROR` and quarantined.

---

## 6. Traceability Architecture

Every record in the relational domain tables maintains an unbroken link back to the exact physical CSV row:

```
[ attendance.csv (Raw row 1) ]
              |
              v (Ingestion)
[ source_records (record_id: 1, row_index: 1, raw_data JSONB) ]
              |
              v (Cleaning Pipeline)
[ attendance (attendance_id: "ATT-0001", source_record_id: 1) ]
              |
              v (SQL Analytics / Metric)
[ Total Hours: 2.0 hrs for Program PRG-001 ]
```

When an auditor inspects an analytical metric or a flagged anomaly:
1. From `attendance.source_record_id` -> Look up `source_records.record_id`.
2. `source_records` provides the exact raw JSON row as originally submitted.
3. `source_records.file_id` -> Look up `source_files` to verify the original file name and SHA-256 hash.

---

## 7. How to Run the Pipeline

Ensure your virtual environment is active and PostgreSQL is running:

```bash
# Execute Day 2 data cleaning, validation, and domain loading
.venv/bin/python -m src.cleaning.run_pipeline

# Execute comprehensive test suite (Day 1 + Day 2)
.venv/bin/python -m pytest tests/
```
