"""
Test Suite for Day 6: Traceability Drilldown UI & Cryptographic Lineage.

Verifies:
1. Program -> domain record lookup returns valid source_record_id.
2. Domain record references valid source_record_id in source_records.
3. source_record_id -> source_records retrieves intact JSONB raw_data.
4. source_records -> source_files links to valid physical file metadata.
5. source_file contains valid 64-char SHA-256 hash and total row count.
6. row_index is preserved and points to exact row coordinates.
7. Physical raw CSV file on disk contains matching row values.
8. Data quality issue -> source_record_id lineage links directly to raw data.
9. Invalid or missing record IDs return None safely without raising uncaught exceptions.
10. Quarantined records preserve lineage while exhibiting no domain table entity.
"""

import pytest
from src.dashboard.queries import (
    get_program_domain_records,
    get_traceability_record,
    get_physical_csv_row,
    get_dq_filtered_issues,
)


def test_program_to_domain_record_lineage():
    """Test 1: Verify domain records contain non-null source_record_id values."""
    for domain in ["attendance", "beneficiaries", "expenses", "outcomes"]:
        df = get_program_domain_records("PRG-001", domain, limit=5)
        assert not df.empty, f"No records returned for domain {domain}"
        assert "source_record_id" in df.columns, f"Domain {domain} missing source_record_id"
        assert df["source_record_id"].notna().all(), f"Found null source_record_id in {domain}"


def test_traceability_record_retrieval():
    """Test 2: Verify get_traceability_record() returns complete 1-to-1 lineage chain."""
    trace = get_traceability_record(51)
    assert trace is not None
    assert trace["record_id"] == 51
    assert trace["file_name"] == "attendance.csv"
    assert trace["row_index"] == 51
    assert isinstance(trace["raw_data"], dict)
    assert len(trace["file_hash"]) == 64


def test_domain_entity_discovery_in_lineage():
    """Test 3: Verify traceability record discovers linked business entity."""
    trace = get_traceability_record(51)
    domain_entities = trace.get("domain_entities", {})
    assert "attendance" in domain_entities
    att = domain_entities["attendance"]
    assert att["attendance_id"] == "ATT-0051"
    assert att["program_id"] == "PRG-004"


def test_source_file_metadata_integrity():
    """Test 4: Verify source_file metadata links properly with total row counts."""
    trace = get_traceability_record(51)
    assert trace["file_total_rows"] == 618  # raw attendance.csv rows
    assert trace["file_id"] == 2


def test_physical_csv_verification():
    """Test 5: Verify live read from data/raw/ matches database JSONB values."""
    trace = get_traceability_record(51)
    physical = trace.get("physical_csv")
    assert physical is not None
    assert physical["row_number"] == 51

    # Verify key field matches between disk and database JSONB
    disk_dict = physical["raw_dict"]
    json_data = trace["raw_data"]
    assert disk_dict["attendance_id"] == json_data["attendance_id"]
    assert disk_dict["participant_id"] == json_data["participant_id"]
    assert disk_dict["session_date"] == json_data["session_date"]


def test_dq_issue_to_source_record_lineage():
    """Test 6: Verify Data Quality issues resolve to valid source records."""
    # Find a quarantined error issue
    error_issues = get_dq_filtered_issues(severity="ERROR", limit=5)
    assert len(error_issues) > 0
    first_error = error_issues.iloc[0]

    record_id = int(first_error["source_record_id"])
    trace = get_traceability_record(record_id)
    assert trace is not None
    assert trace["record_id"] == record_id
    assert len(trace["data_quality_issues"]) > 0

    # Ensure this quarantined record is linked to an issue in its trace
    issue_ids = [i["issue_id"] for i in trace["data_quality_issues"]]
    assert int(first_error["issue_id"]) in issue_ids


def test_quarantined_record_domain_absence():
    """Test 7: Verify a quarantined record exhibits no domain entity (was blocked)."""
    # Issue #349 is EXP-0068 (negative expense) with record_id 686
    error_issues = get_dq_filtered_issues(severity="ERROR", issue_type="INVALID_NUMBER")
    assert len(error_issues) > 0
    exp_error = error_issues[error_issues["source_file"] == "expenses.csv"].iloc[0]
    rec_id = int(exp_error["source_record_id"])

    trace = get_traceability_record(rec_id)
    assert trace is not None
    # Because it was quarantined, domain_entities should NOT contain 'expense'
    assert "expense" not in trace.get("domain_entities", {})


def test_invalid_record_id_safety():
    """Test 8: Verify non-existent record IDs return None safely."""
    trace = get_traceability_record(999999)
    assert trace is None

    physical = get_physical_csv_row("non_existent_file.csv", 1)
    assert physical is None

    physical_out_of_bounds = get_physical_csv_row("attendance.csv", 99999)
    assert physical_out_of_bounds is None


def test_beneficiary_pii_lineage():
    """Test 9: Verify beneficiary lineage preserves anonymized_code without raw PII leak."""
    # Record 619 is BEN-001
    trace = get_traceability_record(619)
    assert trace is not None
    assert trace["file_name"] == "beneficiaries.csv"

    domain_entities = trace.get("domain_entities", {})
    assert "beneficiary" in domain_entities
    ben = domain_entities["beneficiary"]
    assert "anonymized_code" in ben
    assert len(ben["anonymized_code"]) == 64
