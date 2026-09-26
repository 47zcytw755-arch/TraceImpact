"""
Unit and Integration Tests for Day 1 Foundation.
"""

import pytest
from src.database.connection import test_connection as check_db_connection, SessionLocal
from src.database.models import SourceFile, SourceRecord, Program
from src.config import DATA_RAW_DIR
from src.ingestion.ingest_raw import compute_file_hash


def test_database_connection():
    """Verify PostgreSQL connectivity."""
    assert check_db_connection() is True


def test_raw_files_exist():
    """Verify all 5 raw CSV datasets exist in data/raw/."""
    expected_files = ["programs.csv", "beneficiaries.csv", "attendance.csv", "expenses.csv", "outcomes.csv"]
    for fname in expected_files:
        fpath = DATA_RAW_DIR / fname
        assert fpath.exists(), f"File {fname} is missing"
        assert fpath.stat().st_size > 0, f"File {fname} is empty"


def test_source_files_staged():
    """Verify source_files table has entries with matching hashes."""
    db = SessionLocal()
    try:
        source_files = db.query(SourceFile).all()
        assert len(source_files) == 5
        for sf in source_files:
            fpath = DATA_RAW_DIR / sf.file_name
            assert fpath.exists()
            assert sf.file_hash == compute_file_hash(fpath)
            assert sf.total_rows > 0
    finally:
        db.close()


def test_source_records_staged_and_traceable():
    """Verify source_records contains rows and lineage links back to source_file."""
    db = SessionLocal()
    try:
        count = db.query(SourceRecord).count()
        assert count > 0

        # Sample record test
        rec = db.query(SourceRecord).first()
        assert rec is not None
        assert rec.source_file is not None
        assert rec.row_index >= 1
        assert isinstance(rec.raw_data, dict)
    finally:
        db.close()


def test_master_programs_seeded():
    """Verify master programs catalog has seeded baseline rows."""
    db = SessionLocal()
    try:
        programs = db.query(Program).all()
        assert len(programs) >= 5
    finally:
        db.close()
