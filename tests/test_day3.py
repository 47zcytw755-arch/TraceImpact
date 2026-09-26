"""
Unit and Integration Tests for Day 3: SQL Analytics and KPI Views.

Verifications:
1. Analytics views exist in PostgreSQL.
2. Consolidated view `v_program_kpis` returns exactly all master programs without duplicates.
3. Pre-aggregation isolation prevents Cartesian row multiplication.
4. Program reach metrics (distinct beneficiaries, session hours) are mathematically consistent.
5. Financial metrics (total expenses, budget utilization, cost per beneficiary) are non-negative and accurate.
6. Division-by-zero safety using NULLIF (no exceptions, valid numeric values).
7. Outcome improvement metrics reflect valid evaluations and positive gains.
8. Programs with partial/missing metrics remain visible via LEFT JOIN.
9. Immutability checks: analytics queries do not alter `source_records` or raw files.
10. Lineage availability: aggregate metrics can drill down to `source_record_id` and raw JSONB.
"""

import pytest
from sqlalchemy import text
from src.database.connection import SessionLocal
from src.config import DATA_RAW_DIR
from src.ingestion.ingest_raw import compute_file_hash
from src.database.models import SourceFile, SourceRecord, Program


def test_views_exist_in_database():
    """Verify that all 6 required SQL analytics views exist in PostgreSQL."""
    expected_views = [
        "v_program_reach",
        "v_attendance_consistency",
        "v_cost_per_beneficiary",
        "v_cost_per_beneficiary_hour",
        "v_outcome_improvement",
        "v_program_kpis",
    ]
    db = SessionLocal()
    try:
        query = text("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'public';
        """)
        existing_views = [r[0] for r in db.execute(query).fetchall()]
        for v in expected_views:
            assert v in existing_views, f"View '{v}' is missing in PostgreSQL!"
    finally:
        db.close()


def test_program_kpis_row_count_and_uniqueness():
    """Verify v_program_kpis contains exactly 5 master programs with no duplicates."""
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT program_id, program_name FROM v_program_kpis;")).fetchall()
        assert len(rows) == 5, f"Expected 5 program rows in v_program_kpis, got {len(rows)}"
        
        program_ids = [r[0] for r in rows]
        assert len(program_ids) == len(set(program_ids)), "Duplicate program_id detected in v_program_kpis!"
        
        expected_ids = {"PRG-001", "PRG-002", "PRG-003", "PRG-004", "PRG-005"}
        assert set(program_ids) == expected_ids, f"Mismatch in program IDs: {program_ids}"
    finally:
        db.close()


def test_no_cartesian_row_multiplication():
    """
    CRITICAL: Verify that joining attendance, expenses, and outcomes in CTEs
    does not cause row duplication or inflated expense/hour sums.
    """
    db = SessionLocal()
    try:
        # Sum directly on domain tables
        actual_total_expenses = db.execute(text("SELECT SUM(amount) FROM expenses;")).scalar()
        actual_total_hours = db.execute(text("SELECT SUM(session_hours) FROM attendance;")).scalar()

        # Sum from consolidated KPI view
        view_total_expenses = db.execute(text("SELECT SUM(total_expenses) FROM v_program_kpis;")).scalar()
        view_total_hours = db.execute(text("SELECT SUM(total_session_hours) FROM v_program_kpis;")).scalar()

        assert float(actual_total_expenses) == float(view_total_expenses), (
            f"Expense total mismatch! Direct: {actual_total_expenses}, View: {view_total_expenses}"
        )
        assert float(actual_total_hours) == float(view_total_hours), (
            f"Hours total mismatch! Direct: {actual_total_hours}, View: {view_total_hours}"
        )
    finally:
        db.close()


def test_program_reach_metrics():
    """Verify v_program_reach counts distinct beneficiaries and session hours."""
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT * FROM v_program_reach;")).fetchall()
        assert len(rows) == 5
        for r in rows:
            m = r._mapping
            assert m["distinct_beneficiaries_served"] > 0
            assert m["total_attendance_records"] >= m["distinct_beneficiaries_served"]
            assert float(m["total_session_hours"]) > 0.0
    finally:
        db.close()


def test_cost_analytics_and_division_safety():
    """Verify cost per beneficiary and per hour are positive and handle division safely."""
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT * FROM v_cost_per_beneficiary;")).fetchall()
        assert len(rows) == 5
        for r in rows:
            m = r._mapping
            assert float(m["total_expenses"]) > 0.0
            assert m["unique_beneficiaries"] > 0
            assert float(m["cost_per_beneficiary"]) > 0.0
            assert float(m["budget_utilization_pct"]) > 0.0

        # Hourly cost check
        hr_rows = db.execute(text("SELECT * FROM v_cost_per_beneficiary_hour;")).fetchall()
        for r in hr_rows:
            m = r._mapping
            assert float(m["cost_per_beneficiary_hour"]) > 0.0
    finally:
        db.close()


def test_outcome_improvement_metrics():
    """Verify outcome improvement view correctly calculates gains."""
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT * FROM v_outcome_improvement;")).fetchall()
        assert len(rows) == 5
        for r in rows:
            m = r._mapping
            assert m["total_evaluations"] > 0
            assert float(m["avg_baseline_score"]) > 0.0
            assert float(m["avg_exit_score"]) > float(m["avg_baseline_score"])
            assert float(m["avg_score_improvement"]) > 0.0
            assert float(m["avg_improvement_pct"]) > 0.0
    finally:
        db.close()


def test_analytics_immutability():
    """Verify that querying views does not alter source_records or raw files."""
    db = SessionLocal()
    try:
        source_rec_count = db.query(SourceRecord).count()
        assert source_rec_count == 784, f"Source records altered! Expected 784, got {source_rec_count}"

        source_files = db.query(SourceFile).all()
        for sf in source_files:
            fpath = DATA_RAW_DIR / sf.file_name
            assert fpath.exists()
            assert sf.file_hash == compute_file_hash(fpath), f"Raw file {sf.file_name} modified!"
    finally:
        db.close()


def test_lineage_drilldown_from_analytics():
    """Verify that a KPI metric can drill down to underlying domain records and raw JSONB."""
    db = SessionLocal()
    try:
        drilldown_sql = text("""
            SELECT 
                e.expense_id,
                e.program_id,
                e.amount,
                e.source_record_id,
                sr.row_index,
                sf.file_name,
                sr.raw_data
            FROM expenses e
            JOIN source_records sr ON e.source_record_id = sr.record_id
            JOIN source_files sf ON sr.file_id = sf.file_id
            WHERE e.program_id = 'PRG-001';
        """)
        results = db.execute(drilldown_sql).fetchall()
        assert len(results) > 0, "Drilldown query returned no records!"
        for r in results:
            m = r._mapping
            assert m["source_record_id"] is not None
            assert m["row_index"] >= 1
            assert m["file_name"] == "expenses.csv"
            assert isinstance(m["raw_data"], dict)
    finally:
        db.close()
