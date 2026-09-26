# AI Data Intelligence & Investigation Architecture — TraceImpact 2.0

## 1. Overview & Architectural Philosophy

TraceImpact 2.0 introduces an **AI-Assisted Investigation Layer** designed to bridge the gap between raw statistical anomaly detection and actionable executive intelligence.

Rather than granting large language models unconstrained access to a production relational database, TraceImpact enforces **Deterministic Grounding**:
1. All mathematical facts, historical trajectories, baseline statistics, and peer comparisons are calculated directly in Python and PostgreSQL.
2. Only verified structured evidence is passed to the AI investigation layer.
3. The AI is strictly constrained to synthesize and explain the supplied facts.
4. Output must systematically distinguish **empirical observations** from **contextual hypotheses (interpretation)**.
5. Every investigation embeds an immutable, non-negotiable **Non-Causality Disclaimer**.

```
+-------------------------------------------------------------------------+
|                        ML ANOMALY DETECTION                             |
|          (Isolation Forest flags statistically unusual row)            |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  STRUCTURED EVIDENCE COMPILER                           |
|  - Queries world_bank_observations for multi-year historical series     |
|  - Computes historical mean, std dev, range, and Z-score deviation      |
|  - Queries co-occurring indicators for the same country and year        |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  AI INVESTIGATION ENGINE                                |
|  - Structured Finding Summary (Direction, Magnitude, YoY Growth)        |
|  - Grounded Facts Synthesis (Segregated from Interpretation)             |
|  - Potential Contextual Hypotheses (Clearly Marked as Non-Causal)       |
|  - Non-Causality Disclaimer & Methodological Limitations                |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                      POSTGRESQL AUDIT REPOSITORY                        |
|  - ai_investigations (1-to-1 link to anomaly_id & observation_id)       |
|  - ai_insights (Actionable insights feed with quantitative metrics)     |
|  - v_world_bank_ai_lineage (Full 7-step source-to-raw SHA-256 lineage)  |
+-------------------------------------------------------------------------+
```

---

## 2. Facts vs. Interpretation Boundary

Every AI investigation strictly enforces the separation of verified facts from speculative hypotheses:

### Example: Central African Republic (Life Expectancy 2019)
- **FACT (Database Metric)**: Value dropped to 31.53 years in 2019, representing a -1.60 Z-score deviation and a -39.71% single-year contraction.
- **EVIDENCE (PostgreSQL Aggregates)**: Multi-year mean is 46.47 years (range: 31.53 - 53.67). Isolation Forest score is -0.1670.
- **INTERPRETATION (Contextual Hypotheses)**: May reflect severe reporting methodology adjustments, civil unrest disruption, or health survey sampling changes.
- **LIMITATIONS & NON-CAUSALITY**: Observational data alone cannot prove causal attribution or specific policy impacts.

---

## 3. Database Schema for AI Layer

The AI Intelligence layer is backed by relational tables in PostgreSQL:

### `ai_investigations`
- `investigation_id`: SERIAL PRIMARY KEY
- `anomaly_id`: INTEGER UNIQUE REFERENCES `world_bank_anomalies(anomaly_id)`
- `observation_id`: INTEGER REFERENCES `world_bank_observations(observation_id)`
- `country_code`: VARCHAR(10)
- `indicator_code`: VARCHAR(50)
- `year`: INTEGER
- `finding_summary`: TEXT
- `structured_evidence`: JSONB (mean, std dev, min, max, z-score, growth rates)
- `historical_comparison`: JSONB (complete multi-year time series)
- `related_indicators`: JSONB (co-occurring indicators for context)
- `ai_explanation`: TEXT (grounded synthesis)
- `possible_interpretation`: TEXT (hypotheses clearly marked as interpretative)
- `limitations`: TEXT (mandatory non-causality notice)
- `created_at`: TIMESTAMPTZ

### `ai_insights`
- `insight_id`: SERIAL PRIMARY KEY
- `investigation_id`: INTEGER REFERENCES `ai_investigations(investigation_id)`
- `observation_id`: INTEGER REFERENCES `world_bank_observations(observation_id)`
- `country_code`: VARCHAR(10)
- `indicator_code`: VARCHAR(50)
- `year`: INTEGER
- `title`: VARCHAR(255)
- `insight_type`: VARCHAR(50) (`VOLATILITY_SURGE`, `HISTORICAL_DEVIATION`, `SHARP_CONTRACTION`)
- `underlying_metrics`: JSONB
- `evidence_text`: TEXT
- `ai_explanation`: TEXT
- `created_at`: TIMESTAMPTZ

---

## 4. End-to-End Lineage Traceability

Every AI Insight can be traced backwards through 7 distinct verification stages via the SQL view `v_world_bank_ai_lineage`:

```
1. AI Insight (`ai_insights`)
       ↓
2. Grounded AI Investigation (`ai_investigations`)
       ↓
3. Machine Learning Anomaly (`world_bank_anomalies`)
       ↓
4. Verified Observation Fact (`world_bank_observations`)
       ↓
5. Staged Raw JSONB Payload (`api_raw_responses`)
       ↓
6. Cryptographic SHA-256 Hash (`api_raw_responses.response_hash`)
       ↓
7. Automated Ingestion Batch Run (`api_ingestion_runs`)
```

Any auditor or user can click on an AI insight in the Streamlit dashboard and immediately inspect the exact raw JSON byte payload received from the World Bank API server along with its SHA-256 fingerprint.

---

## 5. Security & Read-Only Governance

The AI Query Assistant (`src/dashboard/ai_assistant.py`) protects the database against prompt injection, unauthorized data manipulation, and table corruption:

1. **Strict SQL Whitelist**: Only `SELECT` statements referencing audited views and tables in `ALLOWED_OBJECTS` are executed.
2. **Disallowed Keywords**: Statements containing `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`, `EXEC`, or `SHUTDOWN` are rejected before execution.
3. **Anti-Injection Filter**: Multi-statement SQL (semicolons) and comment tokens (`--`, `/*`) are blocked.
4. **Zero Credential Exposure**: Passwords, API tokens, and database connection strings are never exposed to the AI prompt or user interface.
