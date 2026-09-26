"""
Test Suite for Day 4: Data Quality Scorecard Views & Issue Triage.

Verifies:
1. Existence of all 5 Day 4 quality views.
2. Accurate aggregation in v_data_quality_summary.
3. Severity totals reconciliation with total issues.
4. Status totals reconciliation.
5. File-level aggregation in v_data_quality_by_file.
6. Program-level aggregation in v_data_quality_by_program including UNASSIGNED.
7. Issue-type distribution in v_data_quality_by_type.
8. Blocking issue filtering in v_data_quality_blocking.
9. End-to-end quality issue lineage back to raw source records and files.
10. Triage utility lifecycle operations (resolve, accept, reopen).
11. Raw data immutability preservation.
"""

import hashlib
import pytest
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.config import DATA_RAW_DIR
from src.quality.triage import (
    get_issues,
    get_blocking_issues,
    get_data_quality_summary,
    get_quality_score,
    resolve_issue,
    reopen_issue,
    accept_issue,
)


@pytest.fixture(scope="module")
def db():
    """Provides a transactional database session for tests."""
    session = SessionLocal()
    yield session
    session.close()


def test_day4_views_exist(db):
    """Test 1: Verify all 5 Day 4 data quality views exist in PostgreSQL."""
    expected_views = {
        "v_data_quality_summary",
        "v_data_quality_by_file",
        "v_data_quality_by_program",
        "v_data_quality_by_type",
        "v_data_quality_blocking",
    }
    sql = """
        SELECT table_name FROM information_schema.views 
        WHERE table_schema = 'public';
    """
    existing_views = set(row[0] for row in db.execute(text(sql)).fetchall())
    missing = expected_views - existing_views
    assert not missing, f"Missing Day 4 views: {missing}"


def test_data_quality_summary_metrics(db):
    """Test 2: Verify v_data_quality_summary returns exactly 1 row with valid totals."""
    summary = get_data_quality_summary(db)
    assert summary is not None, "Summary view returned no data"
    assert summary["total_issues"] == 177, f"Expected 177 total issues, got {summary['total_issues']}"
    assert summary["error_count"] == 10, f"Expected 10 errors, got {summary['error_count']}"
    assert summary["warning_count"] == 12, f"Expected 12 warnings, got {summary['warning_count']}"
    assert summary["info_count"] == 155, f"Expected 155 info issues, got {summary['info_count']}"
    assert summary["total_source_records"] == 784, f"Expected 784 records, got {summary['total_source_records']}"


def test_severity_totals_reconcile(db):
    """Test 3: Verify severity counts sum exactly to total_issues."""
    summary = get_data_quality_summary(db)
    severity_sum = summary["error_count"] + summary["warning_count"] + summary["info_count"]
    assert severity_sum == summary["total_issues"], "Severity sum does not match total issues"


def test_status_totals_reconcile(db):
    """Test 4: Verify status counts sum exactly to total_issues."""
    summary = get_data_quality_summary(db)
    status_sum = summary["open_count"] + summary["resolved_count"] + summary["accepted_count"]
    assert status_sum == summary["total_issues"], "Status sum does not match total issues"


def test_file_level_aggregation(db):
    """Test 5: Verify v_data_quality_by_file reconciles with total issues."""
    sql = "SELECT filename, total_issues, error_count, warning_count, info_count FROM v_data_quality_by_file;"
    rows = db.execute(text(sql)).mappings().all()
    assert len(rows) >= 5, "Expected at least 5 source files"

    sum_issues = sum(r["total_issues"] for r in rows)
    assert sum_issues == 177, f"Sum of file issues {sum_issues} != 177"

    # programs.csv should have 0 issues
    prog_row = next((r for r in rows if r["filename"] == "programs.csv"), None)
    assert prog_row is not None
    assert prog_row["total_issues"] == 0


def test_program_level_aggregation(db):
    """Test 6: Verify v_data_quality_by_program captures all 5 programs plus UNASSIGNED."""
    sql = "SELECT program_id, program_name, total_issues, error_count FROM v_data_quality_by_program;"
    rows = db.execute(text(sql)).mappings().all()
    prog_ids = [r["program_id"] for r in rows]

    for expected in ["PRG-001", "PRG-002", "PRG-003", "PRG-004", "PRG-005", "UNASSIGNED"]:
        assert expected in prog_ids, f"Expected program {expected} in quality view"

    sum_issues = sum(r["total_issues"] for r in rows)
    assert sum_issues == 177, f"Program issues sum {sum_issues} != 177"


def test_issue_type_distribution(db):
    """Test 7: Verify v_data_quality_by_type sums to total issues."""
    sql = "SELECT issue_type, total_issues FROM v_data_quality_by_type;"
    rows = db.execute(text(sql)).mappings().all()
    sum_issues = sum(r["total_issues"] for r in rows)
    assert sum_issues == 177, f"Issue type sum {sum_issues} != 177"


def test_blocking_issues_filtering(db):
    """Test 8: Verify v_data_quality_blocking returns only active ERROR issues."""
    blocking = get_blocking_issues(db)
    assert len(blocking) == 10, f"Expected 10 active blocking issues, got {len(blocking)}"
    for b in blocking:
        assert b["severity"] == "ERROR", f"Blocking issue {b['issue_id']} has severity {b['severity']}"
        assert b["status"] == "OPEN", f"Blocking issue {b['issue_id']} has status {b['status']}"
        assert b["source_record_id"] is not None
        assert b["source_file"] is not None


def test_quality_issue_lineage(db):
    """Test 9: Verify end-to-end lineage from DQ issue to source_records and source_files."""
    sql = """
        SELECT 
            dqi.issue_id,
            dqi.severity,
            dqi.issue_type,
            sr.record_id,
            sr.row_index,
            sr.raw_data,
            sf.file_name,
            sf.file_hash
        FROM data_quality_issues dqi
        JOIN source_records sr ON dqi.record_id = sr.record_id
        JOIN source_files sf ON dqi.file_id = sf.file_id
        WHERE dqi.severity = 'ERROR'
        LIMIT 5;
    """
    rows = db.execute(text(sql)).mappings().all()
    assert len(rows) == 5, "Could not trace lineage for 5 error issues"
    for r in rows:
        assert r["record_id"] > 0
        assert r["row_index"] >= 0
        assert isinstance(r["raw_data"], dict)
        assert len(r["file_hash"]) == 64


def test_triage_helpers_lifecycle(db):
    """Test 10: Verify resolve, accept, and reopen operations update lifecycle state."""
    # Find an open warning issue to test lifecycle
    open_warnings = get_issues(db, status="OPEN", severity="WARNING")
    assert len(open_warnings) > 0, "No open warnings found to test triage"
    target_id = open_warnings[0]["issue_id"]

    # 1. Resolve issue
    resolved = resolve_issue(db, target_id, resolution_notes="Verified with field manager")
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None

    # 2. Reopen issue
    reopened = reopen_issue(db, target_id, notes="Needs further verification")
    assert reopened.status == "OPEN"
    assert reopened.resolved_at is None

    # 3. Accept issue
    accepted = accept_issue(db, target_id, resolution_notes="Acceptable variance for demographic reporting")
    assert accepted.status == "ACCEPTED"
    assert accepted.resolved_at is not None

    # Return back to OPEN to maintain test idempotency
    reopen_issue(db, target_id)


def test_raw_data_immutability(db):
    """Test 11: Verify raw source CSV files match source_files SHA-256 hashes exactly."""
    from src.database.models import SourceFile
    source_files = db.query(SourceFile).all()
    assert len(source_files) == 5, "Expected 5 source files"
    for sf in source_files:
        file_path = DATA_RAW_DIR / sf.file_name
        assert file_path.exists(), f"Raw file missing: {sf.file_name}"
        with open(file_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        assert actual_hash == sf.file_hash, f"Raw file {sf.file_name} hash mismatch!"
