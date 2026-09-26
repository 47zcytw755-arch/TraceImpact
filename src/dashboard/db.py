"""
Database Connection and Session Management for Streamlit Dashboard.

WHAT:
Manages PostgreSQL connections and sessions for the Streamlit presentation layer.
Reuses the central SQLAlchemy engine from `src.database.connection`.

WHY:
Prevents connection leaks, provides robust error handling, and avoids creating
duplicate database configuration architectures.

HOW:
Provides context-managed database sessions and cached connection verifiers.
"""

from contextlib import contextmanager
from typing import Generator
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from src.database.connection import engine, SessionLocal, test_connection

logger = logging.getLogger(__name__)


def check_db_health() -> bool:
    """Verifies that the database is reachable and active."""
    return test_connection()


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Context manager yielding a thread-safe SQLAlchemy Session.
    Automatically closes the session upon exit.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error("Database query failed: %s", e)
        db.rollback()
        raise
    finally:
        db.close()
