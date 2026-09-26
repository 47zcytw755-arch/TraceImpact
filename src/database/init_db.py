"""
Database Initialization Script for TraceImpact.

Reads `sql/schema.sql` and executes the DDL statements against the PostgreSQL database
to create all tables, indexes, and constraints.
"""

import logging
from sqlalchemy import text
from src.database.connection import engine
from src.config import SQL_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def init_database():
    """Initializes all PostgreSQL tables from sql/schema.sql."""
    schema_path = SQL_DIR / "schema.sql"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")

    logger.info("Reading schema DDL from %s...", schema_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    logger.info("Executing DDL statements on PostgreSQL...")
    with engine.begin() as conn:
        conn.execute(text(schema_sql))

    logger.info("Database schema initialized successfully! All tables ready.")


if __name__ == "__main__":
    init_database()
