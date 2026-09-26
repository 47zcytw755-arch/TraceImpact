"""
Data Quality Issue Triage and Resolution Service.

WHAT:
Provides controlled backend operations for querying, filtering, resolving, and
accepting data quality anomalies detected across the TraceImpact platform.

WHY:
Empowers nonprofit administrators and data stewards to manage the lifecycle of
data quality findings (OPEN -> RESOLVED / ACCEPTED) with explicit timestamps and
audit notes, while retaining full lineage to source records.

HOW:
Interacts with the `data_quality_issues` table and Day 4 SQL views through
SQLAlchemy ORM sessions.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database.models import DataQualityIssue, SourceFile, SourceRecord, Program


def get_issues(
    db: Session,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    file_name: Optional[str] = None,
    program_id: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves filtered list of data quality issues with source file and program context.
    """
    query = (
        db.query(DataQualityIssue)
        .outerjoin(SourceFile, DataQualityIssue.file_id == SourceFile.file_id)
        .outerjoin(Program, DataQualityIssue.program_id == Program.program_id)
    )

    if status:
        query = query.filter(DataQualityIssue.status == status.upper())
    if severity:
        query = query.filter(DataQualityIssue.severity == severity.upper())
    if issue_type:
        query = query.filter(DataQualityIssue.issue_type == issue_type)
    if file_name:
        query = query.filter(SourceFile.file_name == file_name)
    if program_id:
        if program_id.upper() == "UNASSIGNED":
            query = query.filter(DataQualityIssue.program_id.is_(None))
        else:
            query = query.filter(DataQualityIssue.program_id == program_id)

    query = query.order_by(DataQualityIssue.issue_id.asc())

    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    results = []
    for issue in query.all():
        results.append({
            "issue_id": issue.issue_id,
            "file_id": issue.file_id,
            "filename": issue.source_file.file_name if issue.source_file else None,
            "record_id": issue.record_id,
            "row_number": issue.row_number,
            "column_name": issue.column_name,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "raw_value": issue.raw_value,
            "description": issue.description,
            "status": issue.status,
            "program_id": issue.program_id,
            "program_name": issue.program.program_name if issue.program else None,
            "detected_at": issue.detected_at,
            "resolved_at": issue.resolved_at,
            "resolved_by": issue.resolved_by,
            "resolution_notes": issue.resolution_notes,
        })
    return results


def get_open_issues(
    db: Session,
    severity: Optional[str] = None,
    issue_type: Optional[str] = None,
    file_name: Optional[str] = None,
    program_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Convenience helper to retrieve issues with status='OPEN'."""
    return get_issues(
        db,
        status="OPEN",
        severity=severity,
        issue_type=issue_type,
        file_name=file_name,
        program_id=program_id,
    )


def get_blocking_issues(db: Session) -> List[Dict[str, Any]]:
    """
    Retrieves active blocking issues (severity='ERROR' and status='OPEN')
    directly from the optimized view `v_data_quality_blocking`.
    """
    sql = "SELECT * FROM v_data_quality_blocking ORDER BY issue_id ASC"
    rows = db.execute(text(sql)).mappings().all()
    return [dict(r) for r in rows]


def resolve_issue(
    db: Session,
    issue_id: int,
    resolution_notes: Optional[str] = None,
    resolved_by: Optional[str] = "Administrator",
) -> Optional[DataQualityIssue]:
    """
    Marks an open data quality issue as RESOLVED with audit notes.
    """
    issue = db.query(DataQualityIssue).filter(DataQualityIssue.issue_id == issue_id).first()
    if not issue:
        return None

    issue.status = "RESOLVED"
    issue.resolved_at = datetime.now(timezone.utc)
    issue.resolved_by = resolved_by
    if resolution_notes:
        issue.resolution_notes = resolution_notes

    db.commit()
    db.refresh(issue)
    return issue


def accept_issue(
    db: Session,
    issue_id: int,
    resolution_notes: Optional[str] = None,
    resolved_by: Optional[str] = "Administrator",
) -> Optional[DataQualityIssue]:
    """
    Marks an issue as ACCEPTED (acknowledged domain variance) with audit notes.
    """
    issue = db.query(DataQualityIssue).filter(DataQualityIssue.issue_id == issue_id).first()
    if not issue:
        return None

    issue.status = "ACCEPTED"
    issue.resolved_at = datetime.now(timezone.utc)
    issue.resolved_by = resolved_by
    if resolution_notes:
        issue.resolution_notes = resolution_notes

    db.commit()
    db.refresh(issue)
    return issue


def reopen_issue(
    db: Session,
    issue_id: int,
    notes: Optional[str] = None,
) -> Optional[DataQualityIssue]:
    """
    Reopens a previously resolved or accepted issue back to OPEN.
    """
    issue = db.query(DataQualityIssue).filter(DataQualityIssue.issue_id == issue_id).first()
    if not issue:
        return None

    issue.status = "OPEN"
    issue.resolved_at = None
    issue.resolved_by = None
    if notes:
        issue.resolution_notes = f"[REOPENED] {notes}"

    db.commit()
    db.refresh(issue)
    return issue


def get_data_quality_summary(db: Session) -> Dict[str, Any]:
    """
    Queries the high-level data quality summary from `v_data_quality_summary`.
    """
    sql = "SELECT * FROM v_data_quality_summary"
    row = db.execute(text(sql)).mappings().first()
    return dict(row) if row else {}


def get_quality_score(db: Session) -> Dict[str, Any]:
    """
    Calculates defensible data quality scorecards based on live database metrics:
    - Clean Record Rate (CRR): (total_source_records - error_count) / total_source_records
    - Resolution Rate (RR): (resolved_count + accepted_count) / total_issues
    - Open Defect Rate (ODR): open_count / total_issues
    - Data Reliability Index (DRI): Composite score weighting CRR (60%), RR (20%), and (100 - error_pct) (20%)
    """
    summary = get_data_quality_summary(db)
    if not summary:
        return {}

    total_records = float(summary.get("total_source_records") or 1)
    error_count = float(summary.get("error_count") or 0)
    total_issues = float(summary.get("total_issues") or 1)
    resolved_count = float(summary.get("resolved_count") or 0)
    accepted_count = float(summary.get("accepted_count") or 0)
    open_count = float(summary.get("open_count") or 0)

    clean_record_rate = round(((total_records - error_count) / total_records) * 100, 2)
    resolution_rate = round(((resolved_count + accepted_count) / total_issues) * 100, 2)
    open_defect_rate = round((open_count / total_issues) * 100, 2)

    # Data Reliability Index: 0 to 100 composite index
    dri = round(
        (clean_record_rate * 0.60) +
        (resolution_rate * 0.20) +
        ((100.0 - float(summary.get("error_percentage") or 0)) * 0.20),
        2,
    )

    return {
        "clean_record_rate": clean_record_rate,
        "resolution_rate": resolution_rate,
        "open_defect_rate": open_defect_rate,
        "data_reliability_index": dri,
        "summary": summary,
    }
