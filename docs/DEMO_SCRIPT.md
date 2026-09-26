# TraceImpact — 3-Minute Executive Demo Script

**Target Audience:** Grant Evaluators, Nonprofit Directors, Data Engineering Interviewers, Donors  
**Total Duration:** 3 Minutes (180 Seconds)  
**Prerequisites:** Database running, Streamlit launched via `.venv/bin/streamlit run app.py`  

---

## Demo Overview & Talking Points Schedule

| Time | Section | Screen / Page | Core Message |
|------|---------|---------------|--------------|
| **0:00 – 0:30** | The Nonprofit Dilemma & Ingestion | Portal (`app.py`) | Dirty spreadsheets destroy auditability; TraceImpact preserves raw data immutability with SHA-256 fingerprints. |
| **0:30 – 1:15** | Executive Analytics & Program Anomaly | `1_Executive_Summary` & `2_Program_Analysis` | Live KPIs without row multiplication; automated discovery of an over-budget initiative (PRG-005). |
| **1:15 – 2:00** | Data Governance & Anomaly Triage | `3_Data_Quality` | We don't drop dirty data; we catalog it. 10 blocking errors quarantined from domain tables. |
| **2:00 – 2:40** | The 1-to-1 Cryptographic Proof Engine | `4_Traceability` | Answering: *"Where did this number come from?"* Full drilldown to the exact physical CSV row on disk. |
| **2:40 – 3:00** | AI Natural-Language Query Assistant | `5_AI_Query_Assistant` | Instant answers for non-technical executives grounded in verified SQL views without hallucination. |

---

## Detailed Step-by-Step Walkthrough

### Part 1: The Nonprofit Dilemma & Ingestion (0:00 – 0:30)
- **Navigate to:** `http://localhost:8501/` (`app.py`)
- **Action:** Point out the live database health monitor and volume counters (5 programs, 51 beneficiaries, 612 attendance check-ins, ₹666,950 expenditures).
- **Spoken Script:**
  > *"Nonprofits and grant foundations manage millions of dollars using messy, disconnected spreadsheets. When donors or auditors ask for proof, traditional dashboards fail because data cleaning silently deletes records or breaks links to the original files.*
  > *TraceImpact takes a fundamentally different engineering approach: every incoming CSV is cryptographically hashed with SHA-256, staged verbatim as immutable JSONB, and assigned an exact row coordinate. Nothing is ever lost or altered."*

### Part 2: Executive Analytics & Over-Budget Discovery (0:30 – 1:15)
- **Navigate to:** `1_Executive_Summary.py` ➔ then `2_Program_Analysis.py`
- **Action:** 
  1. Show the 8 KPI cards and 5 visual charts on Executive Summary. Highlight the clean 84.18% issue resolution rate.
  2. Switch to **Program Analysis**, select **`PRG-005: Community Nutrition Drive`** from the dropdown.
  3. Point out the budget alert badge: **156.75% Budget Utilization (Over Budget)**.
- **Spoken Script:**
  > *"All dashboard figures are drawn directly from PostgreSQL analytical views engineered with pre-aggregated CTEs—meaning zero row multiplication and zero division-by-zero risks.*
  > *When we inspect individual programs, the system automatically flags operational variances. For example, Community Nutrition Drive spent ₹148,913 against an allocated budget of ₹95,000—a 156.75% utilization. Because our domain tables maintain foreign keys to raw staging, leadership can inspect the exact expenses that drove this overrun without leaving the dashboard."*

### Part 3: Data Quality Observability & Issue Triage (1:15 – 2:00)
- **Navigate to:** `3_Data_Quality.py`
- **Action:**
  1. Show the Data Reliability Index: **94.94 / 100** and Clean Record Rate: **98.72%**.
  2. Point out the Severity Distribution: 10 ERRORs, 12 WARNINGs, 155 INFOs.
  3. Filter the interactive triage table by `Severity = ERROR` to reveal the 10 quarantined blocking records.
- **Spoken Script:**
  > *"When dealing with messy operational data, most pipelines silently drop rows that fail validation. TraceImpact treats data quality as a first-class citizen.*
  > *Our cleaning pipeline identified 177 anomalies. 10 critical errors—including duplicate attendance check-ins and negative expenses—were quarantined into `v_data_quality_blocking`. Meanwhile, 149 minor format issues were resolved programmatically, achieving a verified 94.94 Data Reliability Index."*

### Part 4: The 1-to-1 Cryptographic Lineage Proof Engine (2:00 – 2:40)
- **Navigate to:** `4_Traceability.py`
- **Action:**
  1. Select **"Attendance Check-In"** from the Quick Select dropdown (`ATT-0001` or `ATT-0051`).
  2. Click **"Verify End-to-End Lineage"**.
  3. Expand the 4-step lineage sequence:
     - Step 1: Cleaned Domain Record (`ATT-0001`, 2.0 hours)
     - Step 2: Raw Staging JSONB (`source_records` row index 1)
     - Step 3: Source File Provenance (`attendance.csv`, SHA-256 hash)
     - Step 4: Physical Disk Read from `data/raw/attendance.csv` at row 1.
- **Spoken Script:**
  > *"Now for the centerpiece of TraceImpact: the cryptographic proof engine. When an auditor asks: 'Where did this attendance check-in come from?', we don't say 'trust the database'.*
  > *We click through the lineage: the cleaned attendance row points to `source_record_id #1`, which stores the verbatim JSONB as ingested. That links to `source_files` where the SHA-256 hash guarantees the file hasn't been tampered with. Finally, the system opens `data/raw/attendance.csv` on disk and confirms the exact physical row matches character-for-character. This is 1-to-1 provable impact."*

### Part 5: AI Natural-Language Query Assistant (2:40 – 3:00)
- **Navigate to:** `5_AI_Query_Assistant.py`
- **Action:**
  1. Select the curated question: *"Which programs are currently exceeding their allocated budget?"*
  2. Show the immediate executive answer, live data table, executed SQL code block, and technical architectural explanation.
- **Spoken Script:**
  > *"Finally, to empower non-technical executives and grant officers, we built an AI Query Assistant. Unlike generic LLMs that hallucinate SQL, our engine grounds natural-language questions strictly in our audited analytical views.*
  > *It returns the exact answer, live table data, the executed SQL, and an architectural explanation of the underlying CTEs.*
  > *With 69/69 automated tests passing and byte-for-byte immutability across all raw files, TraceImpact delivers enterprise data engineering for the social impact sector."*
