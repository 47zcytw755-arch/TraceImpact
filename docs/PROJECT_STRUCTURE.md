# TraceImpact — Project Structure

```
project1/
├── .env                              # Local environment variables (gitignored)
├── .env.example                      # Template for environment configuration
├── .gitignore                        # Git exclusion rules
├── README.md                         # Primary project documentation
├── app.py                            # Streamlit application entry point
├── pytest.ini                        # Pytest configuration
├── requirements.txt                  # Python dependency manifest
├── project_status.md                 # Project progress tracker
│
├── data/
│   ├── raw/                          # IMMUTABLE source CSV datasets
│   │   ├── attendance.csv            # 612 session attendance records
│   │   ├── beneficiaries.csv         # 51 community member records
│   │   ├── expenses.csv              # 67 financial transaction records
│   │   ├── outcomes.csv              # 30 pre/post survey evaluations
│   │   └── programs.csv              # 5 master program definitions
│   └── processed/                    # Cleaned pipeline output (gitignored, regenerable)
│       ├── attendance.csv
│       ├── beneficiaries.csv
│       ├── expenses.csv
│       └── outcomes.csv
│
├── sql/
│   ├── schema.sql                    # Core 8-table relational DDL
│   ├── schema_ml_intelligence.sql    # ML/AI extension tables DDL
│   ├── schema_world_bank.sql         # World Bank pipeline tables DDL
│   ├── views.sql                     # 6 analytical KPI views (Gold layer)
│   ├── views_quality.sql             # 5 data quality governance views
│   ├── views_power_bi.sql            # 9 Power BI executive views
│   ├── views_world_bank.sql          # 4 World Bank analytical views
│   └── analytics_examples.sql        # Example analytical queries
│
├── src/
│   ├── __init__.py
│   ├── config.py                     # Environment & path configuration
│   ├── verify_day1.py                # Day 1 ingestion verification script
│   ├── power_bi_export.py            # Power BI data export utilities
│   ├── power_bi_validator.py         # Power BI view validation suite
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py             # SQLAlchemy engine & session factory
│   │   ├── init_db.py                # Database initialization
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   └── apply_views.py            # SQL view deployment script
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── ingest_raw.py             # CSV → JSONB bronze ingestion
│   │   ├── api_client.py             # HTTP client with retry/backoff
│   │   ├── ingestion_metadata.py     # Run tracking & raw response storage
│   │   ├── world_bank.py             # World Bank API pipeline
│   │   └── scheduler.py              # Automated daily scheduler
│   │
│   ├── cleaning/
│   │   ├── __init__.py
│   │   ├── column_maps.py            # Column name mapping rules
│   │   ├── normalizers.py            # Date, currency, text normalizers
│   │   ├── validators.py             # Data quality validation rules
│   │   ├── transformers.py           # Entity resolution & PII hashing
│   │   ├── loader.py                 # Domain table bulk loader
│   │   └── run_pipeline.py           # Orchestrated cleaning pipeline
│   │
│   ├── quality/
│   │   ├── __init__.py
│   │   ├── triage.py                 # Issue lifecycle management
│   │   └── world_bank_quality.py     # World Bank data validation
│   │
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── feature_extractor.py      # Statistical feature engineering
│   │   └── anomaly_detector.py       # Isolation Forest ML model
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   └── investigator.py           # Grounded AI investigation engine
│   │
│   ├── dashboard/
│   │   ├── __init__.py
│   │   ├── db.py                     # Dashboard DB session helper
│   │   ├── queries.py                # All dashboard SQL queries
│   │   ├── components.py             # Reusable Streamlit UI components
│   │   ├── formatting.py             # Number/currency/% formatters
│   │   └── ai_assistant.py           # NL→SQL query assistant engine
│   │
│   └── generator/
│       ├── __init__.py
│       └── generate_data.py          # Synthetic data generator (Faker)
│
├── pages/                            # Streamlit multi-page app
│   ├── 1_Executive_Summary.py        # Portfolio KPIs & charts
│   ├── 2_Program_Analysis.py         # Per-program deep-dive
│   ├── 3_Data_Quality.py             # Quality scorecard & triage
│   ├── 4_Traceability.py             # 1-to-1 lineage proof engine
│   ├── 5_AI_Query_Assistant.py       # Natural language SQL assistant
│   └── 6_Public_Data_Explorer.py     # World Bank data explorer
│
├── tests/
│   ├── test_day1.py                  # Ingestion & provenance tests (5)
│   ├── test_day2.py                  # Cleaning & validation tests (13)
│   ├── test_day3.py                  # Analytics views tests (8)
│   ├── test_day4.py                  # Quality scorecard tests (11)
│   ├── test_day5.py                  # Dashboard query tests (11)
│   ├── test_day6.py                  # Traceability proof tests (9)
│   ├── test_day7.py                  # AI assistant tests (10)
│   ├── test_ml_and_ai.py             # ML/AI pipeline tests (9)
│   ├── test_world_bank.py            # World Bank integration tests (18)
│   └── stress_test_suite.py          # Performance stress test suite
│
├── demo/                             # Live Pipeline Control Room
│   ├── index.html                    # Control room UI
│   ├── styles.css                    # Design system & animations
│   ├── app.js                        # Simulation controller
│   ├── pipeline.js                   # Network visualization engine
│   ├── particles.js                  # Canvas particle system
│   ├── data.js                       # Measured benchmarks & scenarios
│   └── serve.py                      # HTTP dev server
│
├── models/                           # ML model artifacts (gitignored)
│   ├── IsolationForest_WorldBank_v1.0.0.joblib
│   └── IsolationForest_WorldBank_v_test_suite.joblib
│
└── docs/                             # 25 documentation files
    ├── ARCHITECTURE.md
    ├── AI_DATA_INTELLIGENCE.md
    ├── DASHBOARD.md
    ├── DATA_PIPELINE.md
    ├── DATA_QUALITY_SCORECARD.md
    ├── DAY_1_6_FINAL_BASELINE.md
    ├── DAY_7_FINAL_REVIEW.md
    ├── DEMO_SCRIPT.md
    ├── DEMO_WALKTHROUGH.md
    ├── KPI_DEFINITIONS.md
    ├── ML_ANOMALY_DETECTION.md
    ├── PORTFOLIO.md
    ├── POST_DAY_5_6_REVIEW.md
    ├── POWER_BI_ARCHITECTURE.md
    ├── POWER_BI_DASHBOARD_GUIDE.md
    ├── POWER_BI_DATA_MODEL.md
    ├── POWER_BI_MEASURES.md
    ├── POWER_BI_REFRESH.md
    ├── POWER_BI_VALIDATION.md
    ├── PROJECT_STATUS.md
    ├── REAL_DATA_INGESTION.md
    ├── STRESS_TEST_SUMMARY.md
    ├── TRACEABILITY.md
    ├── power_bi_model_schema.json
    ├── TRACEIMPACT_2_0_FULL_SYSTEM_TEST_REPORT.pdf
    └── test_results/
```

## File Count Summary

| Category | Count |
|---|---|
| Python source modules | 28 |
| SQL schema & view files | 8 |
| Streamlit pages | 6 |
| Test modules | 10 |
| Demo files | 7 |
| Documentation files | 25 |
| Configuration files | 5 |
| Raw data files | 5 |
| **Total tracked files** | **~94** |

## Module Dependency Graph

```
src/config.py
  └── src/database/connection.py
       ├── src/database/models.py
       ├── src/ingestion/ingest_raw.py
       ├── src/cleaning/run_pipeline.py
       │    ├── src/cleaning/column_maps.py
       │    ├── src/cleaning/normalizers.py
       │    ├── src/cleaning/validators.py
       │    ├── src/cleaning/transformers.py
       │    └── src/cleaning/loader.py
       ├── src/quality/triage.py
       ├── src/ingestion/world_bank.py
       │    ├── src/ingestion/api_client.py
       │    ├── src/ingestion/ingestion_metadata.py
       │    └── src/quality/world_bank_quality.py
       ├── src/ml/anomaly_detector.py
       │    └── src/ml/feature_extractor.py
       ├── src/ai/investigator.py
       └── src/dashboard/
            ├── src/dashboard/db.py
            ├── src/dashboard/queries.py
            ├── src/dashboard/ai_assistant.py
            ├── src/dashboard/components.py
            └── src/dashboard/formatting.py
```
