"""
Data Retrieval and Query Layer for Streamlit Dashboard.

WHAT:
Encapsulates all PostgreSQL analytical and lineage queries powering Days 5 & 6.
Leverages Day 3 KPI views (`v_program_reach`, `v_attendance_consistency`,
`v_cost_per_beneficiary`, `v_outcome_improvement`, `v_program_kpis`) and Day 4
Data Quality views (`v_data_quality_summary`, `v_data_quality_by_file`,
`v_data_quality_by_program`, `v_data_quality_by_type`, `v_data_quality_blocking`).

WHY:
Prevents SQL logic leakage into UI view components, supports unit testing without
Streamlit runtime dependencies, and enables clean query caching.
"""

import csv
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
from sqlalchemy import text
from src.dashboard.db import get_db
from src.config import DATA_RAW_DIR

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 1. Executive Summary Queries
# -----------------------------------------------------------------------------

def get_executive_kpis() -> Dict[str, Any]:
    """Retrieves high-level summary KPIs directly from database tables and views."""
    with get_db() as db:
        sql = """
            SELECT 
                (SELECT COUNT(*) FROM programs) AS total_programs,
                (SELECT COUNT(*) FROM beneficiaries) AS total_beneficiaries,
                (SELECT COUNT(*) FROM attendance) AS total_attendance,
                (SELECT COALESCE(SUM(amount), 0) FROM expenses) AS total_expenses,
                (SELECT COUNT(*) FROM outcomes) AS total_outcomes,
                (SELECT COUNT(*) FROM data_quality_issues) AS total_issues,
                (SELECT COUNT(*) FROM data_quality_issues WHERE status = 'OPEN') AS open_issues,
                (SELECT ROUND((COUNT(*) FILTER (WHERE status IN ('RESOLVED', 'ACCEPTED'))::numeric / NULLIF(COUNT(*), 0)) * 100, 2) 
                 FROM data_quality_issues) AS resolution_rate,
                (SELECT ROUND(((COUNT(*) - (SELECT COUNT(*) FROM data_quality_issues WHERE severity = 'ERROR'))::numeric / NULLIF(COUNT(*), 0)) * 100, 2)
                 FROM source_records) AS clean_record_rate
        """
        row = db.execute(text(sql)).mappings().first()
        return dict(row) if row else {}


def get_program_reach_chart_data() -> pd.DataFrame:
    """Retrieves program reach metrics from Day 3 view v_program_reach."""
    with get_db() as db:
        sql = """
            SELECT 
                program_id,
                program_name,
                distinct_beneficiaries_served AS beneficiaries_served,
                total_attendance_records,
                total_session_hours
            FROM v_program_reach
            ORDER BY distinct_beneficiaries_served DESC;
        """
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_attendance_consistency_chart_data() -> pd.DataFrame:
    """Retrieves engagement consistency from Day 3 view v_attendance_consistency."""
    with get_db() as db:
        sql = """
            SELECT 
                program_id,
                program_name,
                attendance_records_per_beneficiary AS sessions_per_beneficiary,
                avg_session_hours,
                total_session_hours
            FROM v_attendance_consistency
            ORDER BY attendance_records_per_beneficiary DESC;
        """
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_cost_per_beneficiary_chart_data() -> pd.DataFrame:
    """Retrieves financial efficiency metrics from Day 3 view v_cost_per_beneficiary."""
    with get_db() as db:
        sql = """
            SELECT 
                program_id,
                program_name,
                budget_allocated,
                total_expenses,
                budget_utilization_pct,
                cost_per_beneficiary
            FROM v_cost_per_beneficiary
            ORDER BY cost_per_beneficiary ASC;
        """
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_outcome_improvement_chart_data() -> pd.DataFrame:
    """Retrieves impact gains from Day 3 view v_outcome_improvement."""
    with get_db() as db:
        sql = """
            SELECT 
                program_id,
                program_name,
                total_evaluations,
                avg_baseline_score,
                avg_exit_score,
                avg_score_improvement,
                avg_improvement_pct
            FROM v_outcome_improvement
            ORDER BY avg_score_improvement DESC;
        """
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_dq_severity_distribution() -> pd.DataFrame:
    """Retrieves issue severity distribution from data_quality_issues."""
    with get_db() as db:
        sql = """
            SELECT 
                severity,
                COUNT(*) AS count
            FROM data_quality_issues
            GROUP BY severity
            ORDER BY 
                CASE severity 
                    WHEN 'ERROR' THEN 1 
                    WHEN 'WARNING' THEN 2 
                    WHEN 'INFO' THEN 3 
                    ELSE 4 
                END;
        """
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


# -----------------------------------------------------------------------------
# 2. Program Analysis Queries
# -----------------------------------------------------------------------------

def get_all_programs() -> List[Dict[str, Any]]:
    """Retrieves list of all master programs for dropdown selectors."""
    with get_db() as db:
        sql = "SELECT program_id, program_name, target_category, budget_allocated FROM programs ORDER BY program_id;"
        rows = db.execute(text(sql)).mappings().all()
        return [dict(r) for r in rows]


def get_program_kpi_detail(program_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the consolidated KPI scorecard row for a single program."""
    with get_db() as db:
        sql = "SELECT * FROM v_program_kpis WHERE program_id = :program_id;"
        row = db.execute(text(sql), {"program_id": program_id}).mappings().first()
        return dict(row) if row else None


def get_program_domain_records(program_id: str, domain: str, limit: int = 50) -> pd.DataFrame:
    """
    Retrieves domain records associated with a program for deep-dive analysis.
    Supported domains: 'beneficiaries', 'attendance', 'expenses', 'outcomes'.
    """
    with get_db() as db:
        if domain == "beneficiaries":
            sql = """
                SELECT DISTINCT 
                    b.beneficiary_id,
                    b.anonymized_code,
                    b.city_location,
                    b.gender,
                    b.age,
                    b.registration_date,
                    b.source_record_id
                FROM beneficiaries b
                JOIN attendance a ON b.beneficiary_id = a.beneficiary_id
                WHERE a.program_id = :program_id
                ORDER BY b.beneficiary_id ASC
                LIMIT :limit;
            """
        elif domain == "attendance":
            sql = """
                SELECT 
                    attendance_id,
                    session_date,
                    attendance_status,
                    session_hours,
                    beneficiary_id,
                    source_record_id
                FROM attendance
                WHERE program_id = :program_id
                ORDER BY session_date DESC, attendance_id ASC
                LIMIT :limit;
            """
        elif domain == "expenses":
            sql = """
                SELECT 
                    expense_id,
                    expense_category,
                    amount,
                    incurred_date,
                    receipt_verified,
                    source_record_id
                FROM expenses
                WHERE program_id = :program_id
                ORDER BY incurred_date DESC, expense_id ASC
                LIMIT :limit;
            """
        elif domain == "outcomes":
            sql = """
                SELECT 
                    outcome_id,
                    indicator_name,
                    baseline_score,
                    exit_score,
                    ROUND(exit_score - baseline_score, 2) AS score_improvement,
                    evaluation_date,
                    beneficiary_id,
                    source_record_id
                FROM outcomes
                WHERE program_id = :program_id
                ORDER BY evaluation_date DESC, outcome_id ASC
                LIMIT :limit;
            """
        else:
            return pd.DataFrame()

        rows = db.execute(text(sql), {"program_id": program_id, "limit": limit}).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_program_issues(program_id: str) -> List[Dict[str, Any]]:
    """Retrieves data quality issues associated with a specific program."""
    with get_db() as db:
        sql = """
            SELECT 
                dqi.issue_id,
                dqi.severity,
                dqi.issue_type,
                dqi.column_name,
                dqi.raw_value,
                dqi.description,
                dqi.status,
                dqi.record_id AS source_record_id,
                sf.file_name AS source_file
            FROM data_quality_issues dqi
            LEFT JOIN source_files sf ON dqi.file_id = sf.file_id
            WHERE dqi.program_id = :program_id
            ORDER BY 
                CASE dqi.severity WHEN 'ERROR' THEN 1 WHEN 'WARNING' THEN 2 ELSE 3 END,
                dqi.issue_id ASC;
        """
        rows = db.execute(text(sql), {"program_id": program_id}).mappings().all()
        return [dict(r) for r in rows]


# -----------------------------------------------------------------------------
# 3. Data Quality Scorecard Queries
# -----------------------------------------------------------------------------

def get_dq_summary() -> Dict[str, Any]:
    """Retrieves aggregate metrics from v_data_quality_summary."""
    with get_db() as db:
        sql = "SELECT * FROM v_data_quality_summary;"
        row = db.execute(text(sql)).mappings().first()
        return dict(row) if row else {}


def get_dq_by_file_df() -> pd.DataFrame:
    """Retrieves file-level breakdown from v_data_quality_by_file."""
    with get_db() as db:
        sql = "SELECT * FROM v_data_quality_by_file ORDER BY total_issues DESC;"
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_dq_by_program_df() -> pd.DataFrame:
    """Retrieves program-level breakdown from v_data_quality_by_program."""
    with get_db() as db:
        sql = "SELECT * FROM v_data_quality_by_program;"
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_dq_by_type_df() -> pd.DataFrame:
    """Retrieves issue-type breakdown from v_data_quality_by_type."""
    with get_db() as db:
        sql = "SELECT * FROM v_data_quality_by_type ORDER BY total_issues DESC;"
        rows = db.execute(text(sql)).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


def get_dq_filtered_issues(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    issue_type: Optional[str] = None,
    file_name: Optional[str] = None,
    program_id: Optional[str] = None,
    limit: int = 250,
) -> pd.DataFrame:
    """Retrieves filtered data quality issues for interactive triage table."""
    with get_db() as db:
        query = """
            SELECT 
                dqi.issue_id,
                dqi.severity,
                dqi.issue_type,
                dqi.description AS issue_message,
                dqi.status,
                COALESCE(dqi.program_id, 'UNASSIGNED') AS program_id,
                COALESCE(p.program_name, 'Unassigned / Org-Level') AS program_name,
                sf.file_name AS source_file,
                dqi.record_id AS source_record_id,
                dqi.row_number,
                dqi.column_name,
                dqi.raw_value,
                dqi.detected_at,
                dqi.resolved_at
            FROM data_quality_issues dqi
            LEFT JOIN source_files sf ON dqi.file_id = sf.file_id
            LEFT JOIN programs p ON dqi.program_id = p.program_id
            WHERE 1=1
        """
        params: Dict[str, Any] = {"limit": limit}

        if severity and severity != "ALL":
            query += " AND dqi.severity = :severity"
            params["severity"] = severity
        if status and status != "ALL":
            query += " AND dqi.status = :status"
            params["status"] = status
        if issue_type and issue_type != "ALL":
            query += " AND dqi.issue_type = :issue_type"
            params["issue_type"] = issue_type
        if file_name and file_name != "ALL":
            query += " AND sf.file_name = :file_name"
            params["file_name"] = file_name
        if program_id and program_id != "ALL":
            if program_id == "UNASSIGNED":
                query += " AND dqi.program_id IS NULL"
            else:
                query += " AND dqi.program_id = :program_id"
                params["program_id"] = program_id

        query += " ORDER BY dqi.issue_id ASC LIMIT :limit;"

        rows = db.execute(text(query), params).mappings().all()
        return pd.DataFrame([dict(r) for r in rows])


# -----------------------------------------------------------------------------
# 4. Day 6 Traceability & Lineage Queries
# -----------------------------------------------------------------------------

def get_traceability_record(record_id: int) -> Optional[Dict[str, Any]]:
    """
    Performs full 1-to-1 lineage trace for a given source_record_id:
    source_record_id -> source_records -> source_files -> raw CSV coordinates.
    Also discovers all domain entities and quality issues referencing this record.
    """
    with get_db() as db:
        sql = """
            SELECT 
                sr.record_id,
                sr.file_id,
                sr.row_index,
                sr.raw_data,
                sr.ingested_at,
                sf.file_name,
                sf.file_hash,
                sf.total_rows AS file_total_rows
            FROM source_records sr
            JOIN source_files sf ON sr.file_id = sf.file_id
            WHERE sr.record_id = :record_id;
        """
        row = db.execute(text(sql), {"record_id": record_id}).mappings().first()
        if not row:
            return None

        result = dict(row)

        # 1. Discover domain entities referencing this source record
        domain_entities: Dict[str, Any] = {}

        # Check beneficiaries
        ben = db.execute(
            text("SELECT beneficiary_id, anonymized_code, city_location, gender, age FROM beneficiaries WHERE source_record_id = :rid"),
            {"rid": record_id}
        ).mappings().first()
        if ben:
            domain_entities["beneficiary"] = dict(ben)

        # Check attendance
        att = db.execute(
            text("SELECT attendance_id, program_id, session_date, attendance_status, session_hours FROM attendance WHERE source_record_id = :rid"),
            {"rid": record_id}
        ).mappings().first()
        if att:
            domain_entities["attendance"] = dict(att)

        # Check expenses
        exp = db.execute(
            text("SELECT expense_id, program_id, expense_category, amount, incurred_date, receipt_verified FROM expenses WHERE source_record_id = :rid"),
            {"rid": record_id}
        ).mappings().first()
        if exp:
            domain_entities["expense"] = dict(exp)

        # Check outcomes
        outc = db.execute(
            text("SELECT outcome_id, program_id, indicator_name, baseline_score, exit_score, evaluation_date FROM outcomes WHERE source_record_id = :rid"),
            {"rid": record_id}
        ).mappings().first()
        if outc:
            domain_entities["outcome"] = dict(outc)

        # Check programs
        prog = db.execute(
            text("SELECT program_id, program_name, target_category, budget_allocated FROM programs WHERE source_record_id = :rid"),
            {"rid": record_id}
        ).mappings().first()
        if prog:
            domain_entities["program"] = dict(prog)

        result["domain_entities"] = domain_entities

        # 2. Discover data quality issues attached to this record
        issues = db.execute(
            text("""
                SELECT issue_id, severity, issue_type, column_name, raw_value, description, status 
                FROM data_quality_issues 
                WHERE record_id = :rid
                ORDER BY issue_id ASC;
            """),
            {"rid": record_id}
        ).mappings().all()
        result["data_quality_issues"] = [dict(i) for i in issues]

        # 3. Read exact physical CSV line from disk
        physical_csv = get_physical_csv_row(result["file_name"], result["row_index"])
        result["physical_csv"] = physical_csv

        return result


def get_physical_csv_row(file_name: str, row_index: int) -> Optional[Dict[str, Any]]:
    """
    Safely reads the exact physical row from data/raw/<file_name> at 1-based row_index.
    Guarantees read-only inspection without file modification.
    """
    csv_path = DATA_RAW_DIR / file_name
    if not csv_path.exists():
        return None

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            for idx, row in enumerate(reader, start=1):
                if idx == row_index:
                    return {
                        "row_number": idx,
                        "headers": headers,
                        "raw_row_list": row,
                        "raw_dict": dict(zip(headers, row)),
                    }
    except Exception as e:
        logger.error("Error reading physical CSV row: %s", e)
        return None

    return None
