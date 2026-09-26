"""
Script to apply SQL Analytics & Quality Views to PostgreSQL.

WHAT:
Reads and executes:
1. `sql/views.sql` (Day 3 Analytical Views):
   - v_program_reach
   - v_attendance_consistency
   - v_cost_per_beneficiary
   - v_cost_per_beneficiary_hour
   - v_outcome_improvement
   - v_program_kpis
2. `sql/views_quality.sql` (Day 4 Data Quality Scorecard Views):
   - v_data_quality_summary
   - v_data_quality_by_file
   - v_data_quality_by_program
   - v_data_quality_by_type
   - v_data_quality_blocking

WHY:
Enables reproducible, idempotent execution of database views across Day 3 and Day 4.

HOW:
Executes the SQL DDL scripts using raw connection to support multi-statement PostgreSQL DDL.
"""

import logging
from src.database.connection import engine
from src.config import SQL_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def apply_analytics_views():
    """Applies Day 3 analytics views defined in sql/views.sql."""
    views_path = SQL_DIR / "views.sql"
    if not views_path.exists():
        raise FileNotFoundError(f"Analytics views file not found at: {views_path}")

    logger.info("Reading Day 3 analytics views from %s...", views_path)
    with open(views_path, "r", encoding="utf-8") as f:
        views_sql = f.read()

    with engine.raw_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(views_sql)
        conn.commit()

    logger.info("Successfully created/updated all Day 3 SQL analytics views!")


def apply_quality_views():
    """Applies Day 4 data quality scorecard views defined in sql/views_quality.sql."""
    views_path = SQL_DIR / "views_quality.sql"
    if not views_path.exists():
        raise FileNotFoundError(f"Quality views file not found at: {views_path}")

    logger.info("Ensuring Day 4 schema columns exist in data_quality_issues...")
    with engine.raw_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            ALTER TABLE data_quality_issues ADD COLUMN IF NOT EXISTS program_id VARCHAR(50) REFERENCES programs(program_id) ON DELETE SET NULL;
            ALTER TABLE data_quality_issues ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;
            ALTER TABLE data_quality_issues ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(100);
            ALTER TABLE data_quality_issues ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
            CREATE INDEX IF NOT EXISTS idx_dq_issues_program ON data_quality_issues(program_id);
            CREATE INDEX IF NOT EXISTS idx_dq_issues_severity ON data_quality_issues(severity);
        """)
        conn.commit()

    logger.info("Reading Day 4 quality views from %s...", views_path)
    with open(views_path, "r", encoding="utf-8") as f:
        views_sql = f.read()

    with engine.raw_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(views_sql)
        conn.commit()

    logger.info("Successfully created/updated all Day 4 SQL data quality views!")


def apply_world_bank_views():
    """Applies World Bank public data views defined in sql/views_world_bank.sql."""
    views_path = SQL_DIR / "views_world_bank.sql"
    if not views_path.exists():
        logger.warning("World Bank views file not found at: %s. Skipping.", views_path)
        return

    logger.info("Reading World Bank views from %s...", views_path)
    with open(views_path, "r", encoding="utf-8") as f:
        views_sql = f.read()

    with engine.raw_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(views_sql)
        conn.commit()

    logger.info("Successfully created/updated all World Bank SQL analytics views!")


def apply_views():
    """Applies all views (Day 3 analytics + Day 4 quality scorecard + World Bank)."""
    apply_analytics_views()
    apply_quality_views()
    apply_world_bank_views()
    logger.info("All TraceImpact views successfully verified and up to date.")


if __name__ == "__main__":
    apply_views()

