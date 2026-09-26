"""
Database Connection and Engine Management.

Concepts:
- Engine: The starting point for any SQLAlchemy application. It maintains a connection pool
  and dialect to translate Python/SQLAlchemy instructions into raw PostgreSQL wire-protocol commands.
- Connection: An active session/checkout from the connection pool.
- Session: An ORM workspace for executing queries and managing transactions (commit/rollback).
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from src.config import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
# pool_pre_ping=True tests connection liveness before using it from the pool
engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)

# Session factory for transactional operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base class for ORM Models
Base = declarative_base()


def get_db():
    """
    Context manager / generator for database sessions.
    Ensures connection is closed properly even if exceptions occur.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> bool:
    """
    Executes a simple 'SELECT 1' query to verify PostgreSQL connectivity.
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
            logger.info("Successfully connected to PostgreSQL database!")
            logger.info("Server version: %s", result)
            return True
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL: %s", str(e))
        return False
