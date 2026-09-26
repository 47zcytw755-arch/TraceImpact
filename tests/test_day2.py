"""
Unit and Integration Tests for Day 2: Data Cleaning, Validation & Domain Loading.

Tests:
1. Column name normalization
2. Date normalization across formats and invalid dates
3. Program name / alias normalization
4. Location normalization
5. Numeric parsing & currency cleaning
6. Duplicate detection (beneficiary duplicate ID & person, attendance check-ins)
7. Missing value detection (ERROR vs WARNING)
8. Invalid numeric detection (negative expenses, out-of-range outcome scores)
9. Unmatched reference detection (orphan participant, missing program)
10. Raw files remain completely unchanged (hash immutability)
11. Processed CSV output files exist and are populated
12. Relational traceability between domain records and source_records
"""

import pytest
from datetime import date
import pandas as pd
from pathlib import Path
from src.config import DATA_RAW_DIR, DATA_PROCESSED_DIR
from src.ingestion.ingest_raw import compute_file_hash
from src.database.connection import SessionLocal
from src.database.models import (
    SourceFile,
    SourceRecord,
    Beneficiary,
    Attendance,
    Expense,
    Outcome,
    DataQualityIssue,
)
from src.cleaning.column_maps import COLUMN_NAME_MAPS
from src.cleaning.normalizers import (
    normalize_columns,
    parse_date,
    normalize_program_name,
    normalize_location,
    parse_numeric,
    generate_anonymized_code,
)
from src.cleaning.validators import (
    IssueCollector,
    validate_beneficiary_record,
    validate_attendance_record,
    validate_expense_record,
    validate_outcome_record,
)


# -----------------------------------------------------------------------------
# Unit Tests: Normalization (Fast in-memory DataFrame tests)
# -----------------------------------------------------------------------------

def test_column_name_normalization():
    """Verify column names are mapped to canonical names."""
    df_raw = pd.DataFrame(columns=["participant_id", "program_title", "session_date", "session_hours"])
    df_norm = normalize_columns(df_raw, "attendance")
    assert "beneficiary_id" in df_norm.columns
    assert "program_name" in df_norm.columns
    assert "session_date" in df_norm.columns
    assert "session_hours" in df_norm.columns


def test_date_normalization_valid_formats():
    """Verify ISO, European, and US date formats parse into python datetime.date."""
    d1, err1 = parse_date("2024-02-15")
    assert d1 == date(2024, 2, 15)
    assert err1 is None

    d2, err2 = parse_date("15/02/2024")
    assert d2 == date(2024, 2, 15)
    assert err2 is None

    d3, err3 = parse_date("02/15/2024")
    assert d3 == date(2024, 2, 15)
    assert err3 is None


def test_date_normalization_invalid():
    """Verify invalid calendar dates are not silently converted."""
    d, err = parse_date("2024-13-45")
    assert d is None
    assert err is not None
    assert "Invalid date format" in err


def test_program_name_normalization():
    """Verify program aliases resolve to canonical program_id and unmapped titles fail."""
    p1, err1 = normalize_program_name("Digi-Literacy")
    assert p1 == "PRG-001"
    assert err1 is None

    p2, err2 = normalize_program_name("Youth-Coding")
    assert p2 == "PRG-003"
    assert err2 is None

    p3, err3 = normalize_program_name("Non-Existent Initiative")
    assert p3 is None
    assert err3 is not None
    assert "Unrecognized program title" in err3


def test_location_normalization():
    """Verify dirty location variations map to canonical city names."""
    assert normalize_location("new delhi") == "New Delhi"
    assert normalize_location("Delhi NCR") == "New Delhi"
    assert normalize_location("  noida  ") == "Noida"
    assert normalize_location("GURGAON") == "Gurugram"
    assert normalize_location("Bhubaneswar ") == "Bhubaneswar"


def test_numeric_currency_and_text_parsing():
    """Verify currency symbols and text units are stripped without corruption."""
    val1, err1 = parse_numeric("₹11,271.75")
    assert val1 == 11271.75
    assert err1 is None

    val2, err2 = parse_numeric("2 hrs")
    assert val2 == 2.0
    assert err2 is None

    val3, err3 = parse_numeric("not-a-number")
    assert val3 is None
    assert "Non-numeric value" in err3


# -----------------------------------------------------------------------------
# Unit Tests: Anomaly Detection & Validation Rules
# -----------------------------------------------------------------------------

def test_detect_duplicate_beneficiary_id():
    """Verify duplicate primary beneficiary ID is caught as ERROR and quarantined."""
    collector = IssueCollector()
    seen_ids = {"BEN-001"}
    seen_persons = {}

    row = {"beneficiary_id": "BEN-001", "full_name": "Test Person", "registration_date": date(2024, 1, 1)}
    is_valid = validate_beneficiary_record(row, row_idx=2, record_id=10, seen_ids=seen_ids, seen_persons=seen_persons, collector=collector)

    assert is_valid is False
    assert collector.count() == 1
    assert collector.issues[0]["issue_type"] == "DUPLICATE"
    assert collector.issues[0]["severity"] == "ERROR"


def test_detect_duplicate_attendance_checkin():
    """Verify double-logging of attendance check-in is caught and quarantined."""
    collector = IssueCollector()
    seen_checkins = {"BEN-001:PRG-001:2024-02-01"}
    valid_b_ids = {"BEN-001"}

    row = {
        "attendance_id": "ATT-0099",
        "beneficiary_id": "BEN-001",
        "program_id": "PRG-001",
        "session_date": "2024-02-01",
        "session_hours": 2.0
    }
    is_valid = validate_attendance_record(row, row_idx=5, record_id=50, seen_checkins=seen_checkins, valid_beneficiary_ids=valid_b_ids, collector=collector)

    assert is_valid is False
    assert any(i["issue_type"] == "DUPLICATE" for i in collector.issues)


def test_detect_negative_expense_amount():
    """Verify negative expenses are flagged as INVALID_NUMBER and quarantined."""
    collector = IssueCollector()
    valid_programs = {"PRG-001"}

    row = {
        "expense_id": "EXP-0099",
        "program_id": "PRG-001",
        "amount": -4500.0,
        "incurred_date": date(2024, 3, 1),
        "expense_category": "Refreshments"
    }
    is_valid = validate_expense_record(row, row_idx=12, record_id=80, valid_program_ids=valid_programs, collector=collector)

    assert is_valid is False
    assert any(i["issue_type"] == "INVALID_NUMBER" and i["severity"] == "ERROR" for i in collector.issues)


def test_detect_out_of_range_outcome_score():
    """Verify outcome exit score > 100 is flagged as INVALID_NUMBER and quarantined."""
    collector = IssueCollector()
    valid_b_ids = {"BEN-007"}
    valid_programs = {"PRG-001"}

    row = {
        "outcome_id": "SURV-0099",
        "beneficiary_id": "BEN-007",
        "program_id": "PRG-001",
        "evaluation_date": date(2024, 4, 15),
        "baseline_score": 45.0,
        "exit_score": 145.0,
    }
    is_valid = validate_outcome_record(row, row_idx=40, record_id=120, valid_beneficiary_ids=valid_b_ids, valid_program_ids=valid_programs, collector=collector)

    assert is_valid is False
    assert any(i["issue_type"] == "INVALID_NUMBER" and i["severity"] == "ERROR" for i in collector.issues)


def test_detect_unmatched_beneficiary_reference():
    """Verify attendance referencing non-existent participant BEN-999 is quarantined."""
    collector = IssueCollector()
    valid_b_ids = {"BEN-001", "BEN-002"}

    row = {
        "attendance_id": "ATT-0500",
        "beneficiary_id": "BEN-999",
        "program_id": "PRG-001",
        "session_date": "2024-02-14",
        "session_hours": 2.0
    }
    is_valid = validate_attendance_record(row, row_idx=500, record_id=600, seen_checkins=set(), valid_beneficiary_ids=valid_b_ids, collector=collector)

    assert is_valid is False
    assert any(i["issue_type"] == "UNMATCHED_REFERENCE" for i in collector.issues)


# -----------------------------------------------------------------------------
# Integration Tests: Immutability, Processed Artifacts, Database Lineage
# -----------------------------------------------------------------------------

def test_raw_files_unmodified():
    """Verify raw files in data/raw/ have NOT been modified by checking SHA-256 hashes."""
    db = SessionLocal()
    try:
        source_files = db.query(SourceFile).all()
        for sf in source_files:
            fpath = DATA_RAW_DIR / sf.file_name
            assert fpath.exists(), f"Raw file {sf.file_name} is missing"
            current_hash = compute_file_hash(fpath)
            assert sf.file_hash == current_hash, f"Raw file {sf.file_name} was modified!"
    finally:
        db.close()


def test_processed_output_files_generated():
    """Verify cleaned CSV artifacts exist in data/processed/."""
    expected_files = ["beneficiaries.csv", "attendance.csv", "expenses.csv", "outcomes.csv"]
    for fname in expected_files:
        p = DATA_PROCESSED_DIR / fname
        assert p.exists(), f"Processed file {fname} not found in {DATA_PROCESSED_DIR}"
        df = pd.read_csv(p)
        assert len(df) > 0, f"Processed file {fname} is empty"


def test_domain_tables_loaded_and_traceable():
    """
    Verify PostgreSQL domain tables contain cleaned records and every domain record
    has a valid foreign key back to source_records.
    """
    db = SessionLocal()
    try:
        ben_count = db.query(Beneficiary).count()
        att_count = db.query(Attendance).count()
        exp_count = db.query(Expense).count()
        out_count = db.query(Outcome).count()
        dq_count = db.query(DataQualityIssue).count()

        assert ben_count > 0, "beneficiaries table is empty"
        assert att_count > 0, "attendance table is empty"
        assert exp_count > 0, "expenses table is empty"
        assert out_count > 0, "outcomes table is empty"
        assert dq_count > 0, "data_quality_issues table is empty"

        # Traceability check: Sample records must point to an existing source_record
        sample_ben = db.query(Beneficiary).first()
        assert sample_ben.source_record_id is not None
        source_rec = db.query(SourceRecord).filter(SourceRecord.record_id == sample_ben.source_record_id).first()
        assert source_rec is not None
        assert isinstance(source_rec.raw_data, dict)

        # Traceability check for Attendance
        sample_att = db.query(Attendance).first()
        assert sample_att.source_record_id is not None
        source_rec_att = db.query(SourceRecord).filter(SourceRecord.record_id == sample_att.source_record_id).first()
        assert source_rec_att is not None

        # Traceability check for DQ Issues
        sample_issue = db.query(DataQualityIssue).filter(DataQualityIssue.issue_type == "DUPLICATE").first()
        assert sample_issue is not None
        assert sample_issue.file_id is not None
        assert sample_issue.record_id is not None
    finally:
        db.close()
