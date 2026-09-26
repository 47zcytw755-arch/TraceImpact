"""
Configuration Module for TraceImpact.

Loads database and application parameters from environment variables (.env file).
In professional software engineering, credentials and environment-specific settings
must NEVER be hardcoded into codebase files.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Locate base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present
load_dotenv(BASE_DIR / ".env")

# Database connection credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "traceimpact")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Build standard PostgreSQL connection URI for SQLAlchemy
# Format: postgresql+psycopg2://username:password@host:port/database_name
if DB_PASSWORD:
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Directory Paths
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
SQL_DIR = BASE_DIR / "sql"

# TraceImpact 2.0 Automated Scheduler Configuration
# Interval in hours between scheduled runs (default: 24 for daily schedule)
PIPELINE_SCHEDULE_INTERVAL_HOURS = float(os.getenv("PIPELINE_SCHEDULE_INTERVAL_HOURS", "24"))
# Whether the scheduler executes an immediate ingestion run when started (default: True)
PIPELINE_RUN_ON_STARTUP = os.getenv("PIPELINE_RUN_ON_STARTUP", "true").lower() in ("true", "1", "yes")
# Historical lookback years for incremental/scheduled ingestion (default: 3 years)
PIPELINE_LOOKBACK_YEARS = int(os.getenv("PIPELINE_LOOKBACK_YEARS", "3"))

