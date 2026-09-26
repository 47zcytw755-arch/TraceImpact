# TraceImpact — Complete Visual Demo & Evaluation Walkthrough

**Document Version:** 1.0.0  
**Target Audience:** Technical Recruiters, Engineering Interviewers, Grant Evaluators, Nonprofit Directors  
**Application Entry Point:** `app.py`  
**Evaluation Mode:** Interactive Multi-Page Streamlit UI + Automated Pytest Verification  

---

## 1. Quick-Start Launch Instructions

Open a terminal in the project root directory and execute:

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Run automated test suite verification (69/69 passing)
.venv/bin/python -m pytest -v

# 3. Launch the Streamlit Multi-Page Application
.venv/bin/python -m streamlit run app.py
```

Streamlit will launch locally at `http://localhost:8501`.

---

## 2. Interactive Page-by-Page Evaluation Tour

```
TraceImpact Web Application Hierarchy
├── app.py (Portal Overview & System Health)
├── pages/
│   ├── 1_Executive_Summary.py (Portfolio Impact & Visualizations)
│   ├── 2_Program_Analysis.py (Initiative Scorecard & Domain Records)
│   ├── 3_Data_Quality.py (Observability & Anomaly Triage Workspace)
│   ├── 4_Traceability.py (1-to-1 Cryptographic Lineage Proof Engine)
│   └── 5_AI_Query_Assistant.py (Grounded Natural-Language Q&A)
```

---

### Step 1: Portal Overview & Live Health Probe (`app.py`)

- **URL:** `http://localhost:8501/`
- **What to Observe:**
  1. **Live PostgreSQL Health Probe:** Displays a green connection badge showing PostgreSQL host, port, active database (`traceimpact`), and connection pool status.
  2. **Platform Volume Metrics:**
     - Master Programs: **5**
     - Verified Beneficiaries: **51**
     - Attendance Sessions: **612**
     - Total Expenditures: **₹666,950.36**
     - Outcome Evaluations: **39**
     - Cataloged Data Quality Issues: **177**
     - Open Triage Items: **28** (with -149 resolved delta)
     - Issue Resolution Rate: **84.18%**
     - Clean Record Rate: **98.72%**
  3. **Guided Workflow Navigation:** Interactive cards detailing the 5 application modules.

---

### Step 2: Executive Summary & Visual Analytics (`pages/1_Executive_Summary.py`)

- **Navigation:** Click **"1 Executive Summary"** in the left sidebar.
- **What to Observe:**
  1. **8 KPI Summary Cards:** Summarizes organization-wide reach, expenditures, attendance, and data reliability metrics.
  2. **5 Production Visualizations (Directly from SQL Views):**
     - **Program Reach Chart (`v_program_reach`):** Bar chart comparing distinct community members served across all 5 initiatives.
     - **Attendance Consistency Chart (`v_attendance_consistency`):** Dual-axis analysis comparing check-ins per person against cumulative contact hours.
     - **Cost per Beneficiary Chart (`v_cost_per_beneficiary`):** Unit economics ranking initiatives by cost per person served (from ₹2,044.94 to ₹4,346.91).
     - **Outcome Improvement Chart (`v_outcome_improvement`):** Grouped bar chart comparing baseline evaluation scores against exit evaluation scores (gains between +21.75 and +31.40 points).
     - **Data Quality Severity Distribution:** Donut chart showing the proportion of `ERROR` (5.65%), `WARNING` (6.78%), and `INFO` (87.57%) items.

---

### Step 3: Program Analysis & Variance Detection (`pages/2_Program_Analysis.py`)

- **Navigation:** Click **"2 Program Analysis"** in the left sidebar.
- **What to Test:**
  1. **Program Selector Dropdown:** Select each initiative from the dropdown:
     - `PRG-001: Digital Literacy Initiative`
     - `PRG-002: Women Vocational Sewing`
     - `PRG-003: Youth Coding Bootcamp`
     - `PRG-004: Elderly Healthcare Outreach`
     - `PRG-005: Community Nutrition Drive`
  2. **Over-Budget Discovery (`PRG-005`):**
     - Select **`PRG-005: Community Nutrition Drive`**.
     - Notice the automated red alert badge: **"156.75% Budget Utilization (Over Budget)"**.
     - Observe the financial variance: Total Spent: **₹148,913.20** vs. Allocated Budget: **₹95,000.00**.
  3. **12-Metric Scorecard:** Inspect Reach, Economic, and Outcome metrics loaded live from `v_program_kpis`.
  4. **4-Domain Tabbed Record Explorer:**
     - Click through **"Beneficiaries"**, **"Attendance"**, **"Expenses"**, and **"Outcomes"** tabs.
     - Note that beneficiary records show salted SHA-256 `anonymized_code` for PII protection.
  5. **Program Data Quality Log:** Displays anomalies specifically linked to the selected program.

---

### Step 4: Data Quality Observability & Issue Triage (`pages/3_Data_Quality.py`)

- **Navigation:** Click **"3 Data Quality"** in the left sidebar.
- **What to Observe:**
  1. **Systemic Reliability Scorecard:**
     - Data Reliability Index (DRI): **94.94 / 100**
     - Clean Record Rate: **98.72%**
     - Issue Resolution Rate: **84.18%**
  2. **Defect Breakdown Visualizations:**
     - Distribution by Source File (`attendance.csv`: 139, `beneficiaries.csv`: 16, `expenses.csv`: 11, `outcomes.csv`: 11).
     - Distribution by Anomaly Type (`MISSING_VALUE`: 150, `INVALID_FORMAT`: 16, `DUPLICATE`: 7, `INVALID_NUMBER`: 2, `UNMATCHED_REFERENCE`: 2).
  3. **Quarantine Review Container:** Highlights the **10 critical ERROR records** quarantined from domain tables.
  4. **Interactive Multi-Parameter Filter Table:**
     - Filter by **Severity** (`ERROR`, `WARNING`, `INFO`).
     - Filter by **Status** (`OPEN`, `RESOLVED`, `ACCEPTED`).
     - Filter by **Source File** and **Program** (including `UNASSIGNED` org-level issues).
     - Confirm that filtering dynamically updates the underlying DataFrame.

---

### Step 5: The 1-to-1 Cryptographic Lineage Proof Engine (`pages/4_Traceability.py`)

- **Navigation:** Click **"4 Traceability"** in the left sidebar.
- **The Core Audit Scenario:**
  - An auditor asks: *"Prove that attendance record ATT-0001 or beneficiary BEN-001 wasn't fabricated."*
- **What to Test:**
  1. **Quick Select Investigation:**
     - Select **"Attendance Check-In (ATT-0001)"** from the dropdown.
     - Click **"Verify End-to-End Lineage"**.
  2. **The 4-Step Verification Sequence:**
     - **Step 1: Cleaned Domain Record:** Inspect the cleaned `attendance` row (`ATT-0001`, `PRG-001`, 2.0 hours).
     - **Step 2: Staged JSONB Record:** Inspect the verbatim JSONB staged in `source_records(record_id: 1)`.
     - **Step 3: Source File Provenance:** Verify `source_files(file_name: 'attendance.csv')` and its 64-character SHA-256 cryptographic hash.
     - **Step 4: Physical Disk Read:** Observe the live read-only verification from `data/raw/attendance.csv` at row 1, confirming character-for-character agreement between disk, database, and UI.
  3. **Quarantined Record Lineage Test:**
     - Enter Record ID `#613` (a duplicate attendance check-in).
     - Notice the orange callout: *"This record was flagged with an ERROR defect and safely quarantined from domain tables."*

---

### Step 6: AI Natural-Language Query Assistant (`pages/5_AI_Query_Assistant.py`)

- **Navigation:** Click **"5 AI Query Assistant"** in the left sidebar.
- **What to Test:**
  1. **Curated Inquiries Mode:**
     - Select: *"Which programs are currently exceeding their allocated budget?"*
     - View the immediate finding: identifies **PRG-005 (156.75% utilization, ₹53,913 variance)**.
     - Inspect the live tabular DataFrame retrieved from `v_cost_per_beneficiary`.
     - Expand the **SQL & Technical Explanation accordion** to view the executed SQL query and architectural breakdown.
  2. **Custom Natural-Language Prompt:**
     - Switch to **"Custom Natural-Language Question"**.
     - Type: *"Show outcome improvements for Youth Coding Bootcamp"*
     - Observe how the engine extracts `PRG-003`, executes the filtered query against `v_outcome_improvement`, and returns the verified +31.40 point gain.
  3. **Security Test:**
     - The engine rejects any malicious SQL inputs (e.g., `DROP TABLE`, `DELETE`, comment tokens).

---

## 3. Automated Test Suite Verification

Run the complete test suite from terminal:

```bash
.venv/bin/python -m pytest -v
```

### Verification Checklist:
- [x] **Day 1 Tests (`tests/test_day1.py`):** 5/5 PASSED (PostgreSQL connection, file staging, SHA-256 hashes, program seeding).
- [x] **Day 2 Tests (`tests/test_day2.py`):** 14/14 PASSED (Normalizers, validators, PII hashing, domain loading, immutability).
- [x] **Day 3 Tests (`tests/test_day3.py`):** 8/8 PASSED (Analytical views, non-multiplication CTEs, division safety, drilldowns).
- [x] **Day 4 Tests (`tests/test_day4.py`):** 11/11 PASSED (Quality views, severity reconciliation, status totals, triage lifecycle).
- [x] **Day 5 Tests (`tests/test_day5.py`):** 11/11 PASSED (Dashboard modules, KPI accuracy, program selectors, filtering).
- [x] **Day 6 Tests (`tests/test_day6.py`):** 9/9 PASSED (1-to-1 lineage, JSONB staging match, physical CSV read, quarantine omission).
- [x] **Day 7 Tests (`tests/test_day7.py`):** 11/11 PASSED (AI engine presets, execution, intent mapping, SQL injection safety, UI load).

**Total:** **69 / 69 PASSED in 0.95 seconds.**
