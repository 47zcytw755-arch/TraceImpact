import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

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

# Build SQLAlchemy PostgreSQL connection URL
DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME,
)

# Directory Paths
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
SQL_DIR = BASE_DIR / "sql"

# TraceImpact 2.0 Automated Pipeline Scheduler
PIPELINE_SCHEDULE_INTERVAL_HOURS = float(
    os.getenv("PIPELINE_SCHEDULE_INTERVAL_HOURS", "24")
)

PIPELINE_RUN_ON_STARTUP = os.getenv(
    "PIPELINE_RUN_ON_STARTUP", "true"
).lower() in ("true", "1", "yes")

PIPELINE_LOOKBACK_YEARS = int(
    os.getenv("PIPELINE_LOOKBACK_YEARS", "3")
)
