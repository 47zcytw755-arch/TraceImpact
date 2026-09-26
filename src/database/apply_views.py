"""
Script to apply SQL Analytics Views (sql/views.sql) to PostgreSQL.

WHAT:
Reads and executes `sql/views.sql` to install or replace analytical views in PostgreSQL:
- v_program_reach
- v_attendance_consistency
- v_cost_per_beneficiary
- v_cost_per_beneficiary_hour
- v_outcome_improvement
- v_program_kpis

WHY:
Enables reproducible execution of Day 3 analytics DDL.

HOW:
Executes the SQL DDL script within an atomic SQLAlchemy transaction.
"""

import logging
from sqlalchemy import text
from src.database.connection import engine
from src.config import SQL_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def apply_views():
    """Applies all views defined in sql/views.sql to the database."""
    views_path = SQL_DIR / "views.sql"
    if not views_path.exists():
        raise FileNotFoundError(f"Views file not found at: {views_path}")

    logger.info("Reading views SQL from %s...", views_path)
    with open(views_path, "r", encoding="utf-8") as f:
        views_sql = f.read()

    logger.info("Applying analytics views to PostgreSQL...")
    with engine.begin() as conn:
        conn.execute(text(views_sql))

    logger.info("Successfully created/updated all SQL analytics views!")


if __name__ == "__main__":
    apply_views()
