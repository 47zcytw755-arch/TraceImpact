"""
Test Suite for Day 5: Streamlit Dashboard Foundation & Queries.

Verifies:
1. Dashboard modules import successfully.
2. Database health check returns True.
3. Executive KPI queries return expected database counts.
4. Program listing loads all 5 master programs.
5. Program KPI detail returns all 17 scorecard metrics.
6. Program domain records query returns expected entities.
7. Data quality summary queries return valid totals.
8. Issue filtering works by severity, status, and file.
9. Chart data generation produces non-empty DataFrames.
10. Empty-state behavior handles non-existent IDs gracefully.
"""

import pytest
import pandas as pd
from src.dashboard.db import check_db_health, get_db
from src.dashboard.formatting import format_currency, format_number, format_percentage
from src.dashboard.queries import (
    get_executive_kpis,
    get_all_programs,
    get_program_kpi_detail,
    get_program_domain_records,
    get_program_reach_chart_data,
    get_attendance_consistency_chart_data,
    get_cost_per_beneficiary_chart_data,
    get_outcome_improvement_chart_data,
    get_dq_severity_distribution,
    get_dq_summary,
    get_dq_by_file_df,
    get_dq_by_program_df,
    get_dq_by_type_df,
    get_dq_filtered_issues,
)


def test_dashboard_modules_import():
    """Test 1: Verify all dashboard modules and components import cleanly."""
    import src.dashboard.db as db_mod
    import src.dashboard.queries as queries_mod
    import src.dashboard.formatting as fmt_mod
    import src.dashboard.components as comp_mod
    assert db_mod is not None
    assert queries_mod is not None
    assert fmt_mod is not None
    assert comp_mod is not None


def test_database_health_check():
    """Test 2: Verify PostgreSQL connection health check passes."""
    assert check_db_health() is True


def test_executive_kpis_accuracy():
    """Test 3: Verify get_executive_kpis() returns expected ground-truth counts."""
    kpis = get_executive_kpis()
    assert kpis["total_programs"] == 5
    assert kpis["total_beneficiaries"] == 51
    assert kpis["total_attendance"] == 612
    assert float(kpis["total_expenses"]) == pytest.approx(666950.36, rel=1e-2)
    assert kpis["total_outcomes"] == 39
    assert kpis["total_issues"] == 177
    assert kpis["open_issues"] == 28
    assert float(kpis["resolution_rate"]) == pytest.approx(84.18, rel=1e-2)
    assert float(kpis["clean_record_rate"]) == pytest.approx(98.72, rel=1e-2)


def test_program_list_retrieval():
    """Test 4: Verify get_all_programs() retrieves all 5 initiatives."""
    progs = get_all_programs()
    assert len(progs) == 5
    ids = [p["program_id"] for p in progs]
    assert ids == ["PRG-001", "PRG-002", "PRG-003", "PRG-004", "PRG-005"]


def test_program_kpi_detail():
    """Test 5: Verify get_program_kpi_detail() returns single program scorecard."""
    detail = get_program_kpi_detail("PRG-001")
    assert detail is not None
    assert detail["program_id"] == "PRG-001"
    assert detail["program_name"] == "Digital Literacy Initiative"
    assert detail["beneficiaries_served"] == 42
    assert detail["total_attendance_records"] == 123
    assert float(detail["total_session_hours"]) == 224.0
    assert float(detail["total_expenses"]) == pytest.approx(130311.93, rel=1e-2)
    assert float(detail["budget_utilization_pct"]) == pytest.approx(86.87, rel=1e-2)


def test_program_domain_records():
    """Test 6: Verify domain record retrieval across all 4 business entities."""
    ben_df = get_program_domain_records("PRG-001", "beneficiaries", limit=10)
    assert isinstance(ben_df, pd.DataFrame)
    assert len(ben_df) > 0
    assert "source_record_id" in ben_df.columns

    att_df = get_program_domain_records("PRG-001", "attendance", limit=10)
    assert isinstance(att_df, pd.DataFrame)
    assert len(att_df) > 0
    assert "attendance_id" in att_df.columns

    exp_df = get_program_domain_records("PRG-001", "expenses", limit=10)
    assert isinstance(exp_df, pd.DataFrame)
    assert len(exp_df) > 0
    assert "amount" in exp_df.columns

    outc_df = get_program_domain_records("PRG-001", "outcomes", limit=10)
    assert isinstance(outc_df, pd.DataFrame)
    assert len(outc_df) > 0
    assert "score_improvement" in outc_df.columns


def test_chart_data_queries():
    """Test 7: Verify all 5 executive chart queries return non-empty DataFrames."""
    reach = get_program_reach_chart_data()
    assert len(reach) == 5

    att = get_attendance_consistency_chart_data()
    assert len(att) == 5

    cost = get_cost_per_beneficiary_chart_data()
    assert len(cost) == 5

    outcomes = get_outcome_improvement_chart_data()
    assert len(outcomes) == 5

    dq_dist = get_dq_severity_distribution()
    assert len(dq_dist) == 3  # ERROR, WARNING, INFO


def test_dq_scorecard_queries():
    """Test 8: Verify Day 4 view wrapper queries return consistent metrics."""
    summary = get_dq_summary()
    assert summary["total_issues"] == 177

    by_file = get_dq_by_file_df()
    assert len(by_file) >= 5
    assert by_file["total_issues"].sum() == 177

    by_prog = get_dq_by_program_df()
    assert len(by_prog) == 6  # 5 programs + UNASSIGNED
    assert by_prog["total_issues"].sum() == 177

    by_type = get_dq_by_type_df()
    assert len(by_type) == 6
    assert by_type["total_issues"].sum() == 177


def test_dq_filtering():
    """Test 9: Verify filtering by severity, status, and source file."""
    errors = get_dq_filtered_issues(severity="ERROR")
    assert len(errors) == 10

    open_issues = get_dq_filtered_issues(status="OPEN")
    assert len(open_issues) == 28

    resolved_issues = get_dq_filtered_issues(status="RESOLVED")
    assert len(resolved_issues) == 149

    att_issues = get_dq_filtered_issues(file_name="attendance.csv")
    assert len(att_issues) == 139


def test_formatting_utilities():
    """Test 10: Verify formatting functions handle nulls and numerical values correctly."""
    assert format_currency(130311.93) == "₹130,311.93"
    assert format_currency(None) == "₹0.00"

    assert format_number(1250) == "1,250"
    assert format_number(None) == "0"

    assert format_percentage(86.873, decimals=1) == "86.9%"
    assert format_percentage(None) == "0.0%"


def test_empty_state_handling():
    """Test 11: Verify non-existent program ID returns None / empty DataFrame."""
    invalid_detail = get_program_kpi_detail("PRG-999")
    assert invalid_detail is None

    empty_domain = get_program_domain_records("PRG-999", "beneficiaries")
    assert empty_domain.empty
