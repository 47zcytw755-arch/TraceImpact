"""
Database and File System Loader for TraceImpact Cleaned Datasets.

WHAT:
1. Exports reproducible, cleaned CSV files into `data/processed/`.
2. Idempotently loads valid domain records into PostgreSQL tables:
   `beneficiaries`, `attendance`, `expenses`, `outcomes`.
3. Inserts detected data quality anomalies into `data_quality_issues`.

WHY:
Persisting cleaned datasets to `data/processed/` provides file-based snapshots
for downstream analytics or inspection without touching raw inputs.
Loading into relational domain tables establishes foreign-key enforced integrity,
while storing data quality issues guarantees non-destructive auditability.

HOW:
Uses SQLAlchemy Session within a single ACID transaction. Deletes prior domain
and issue rows (in strict child-to-parent relational order) before bulk inserting
new clean rows.

CONCEPT:
Idempotent Loading & Referential Integrity (Cascade and foreign key order).
"""

import logging
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd
from sqlalchemy.orm import Session
from src.config import DATA_PROCESSED_DIR
from src.database.models import (
    Beneficiary,
    Attendance,
    Expense,
    Outcome,
    DataQualityIssue,
)

logger = logging.getLogger(__name__)


def export_processed_csvs(cleaned_dfs: Dict[str, pd.DataFrame], output_dir: Path = DATA_PROCESSED_DIR):
    """
    WHAT:
    Saves cleaned DataFrames into data/processed/ directory.

    WHY:
    Separates raw immutable data from cleaned, standardized artifacts.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, df in cleaned_dfs.items():
        out_path = output_dir / f"{name}.csv"
        df.to_csv(out_path, index=False)
        logger.info("Saved processed CSV: %s (%d rows)", out_path, len(df))


def load_domain_and_issues(
    db: Session,
    cleaned_dfs: Dict[str, pd.DataFrame],
    all_issues: List[Dict[str, Any]],
):
    """
    WHAT:
    Inserts clean records into PostgreSQL domain tables and logs all DQ issues.

    WHY:
    Populates normalized analytics tables while tracking every data anomaly.

    HOW:
    Cleans previous domain records in child-to-parent order:
    outcomes -> expenses -> attendance -> beneficiaries -> data_quality_issues
    Then bulk adds new objects and commits.
    """
    logger.info("Clearing existing domain records and data quality issues for clean reload...")
    db.query(Outcome).delete()
    db.query(Expense).delete()
    db.query(Attendance).delete()
    db.query(Beneficiary).delete()
    db.query(DataQualityIssue).delete()
    db.flush()

    # 1. Load Beneficiaries
    df_ben = cleaned_dfs.get("beneficiaries", pd.DataFrame())
    ben_objects = []
    for _, row in df_ben.iterrows():
        ben_objects.append(Beneficiary(
            beneficiary_id=row["beneficiary_id"],
            source_record_id=row["source_record_id"],
            anonymized_code=row["anonymized_code"],
            gender=row["gender"],
            age=int(row["age"]) if pd.notna(row["age"]) and row["age"] is not None else None,
            city_location=row["city_location"],
            registration_date=row["registration_date"],
        ))
    db.add_all(ben_objects)
    db.flush()
    logger.info("Loaded %d records into 'beneficiaries'", len(ben_objects))

    # 2. Load Attendance
    df_att = cleaned_dfs.get("attendance", pd.DataFrame())
    att_objects = []
    for _, row in df_att.iterrows():
        att_objects.append(Attendance(
            attendance_id=row["attendance_id"],
            source_record_id=row["source_record_id"],
            beneficiary_id=row["beneficiary_id"],
            program_id=row["program_id"],
            session_date=row["session_date"],
            attendance_status=row["attendance_status"],
            session_hours=float(row["session_hours"]) if pd.notna(row["session_hours"]) else 0.0,
        ))
    db.add_all(att_objects)
    db.flush()
    logger.info("Loaded %d records into 'attendance'", len(att_objects))

    # 3. Load Expenses
    df_exp = cleaned_dfs.get("expenses", pd.DataFrame())
    exp_objects = []
    for _, row in df_exp.iterrows():
        exp_objects.append(Expense(
            expense_id=row["expense_id"],
            source_record_id=row["source_record_id"],
            program_id=row["program_id"],
            expense_category=row["expense_category"],
            amount=float(row["amount"]),
            incurred_date=row["incurred_date"],
            receipt_verified=bool(row["receipt_verified"]),
        ))
    db.add_all(exp_objects)
    db.flush()
    logger.info("Loaded %d records into 'expenses'", len(exp_objects))

    # 4. Load Outcomes
    df_out = cleaned_dfs.get("outcomes", pd.DataFrame())
    out_objects = []
    for _, row in df_out.iterrows():
        out_objects.append(Outcome(
            outcome_id=row["outcome_id"],
            source_record_id=row["source_record_id"],
            beneficiary_id=row["beneficiary_id"],
            program_id=row["program_id"],
            indicator_name=row["indicator_name"],
            baseline_score=float(row["baseline_score"]) if pd.notna(row["baseline_score"]) and row["baseline_score"] is not None else None,
            exit_score=float(row["exit_score"]) if pd.notna(row["exit_score"]) and row["exit_score"] is not None else None,
            evaluation_date=row["evaluation_date"],
        ))
    db.add_all(out_objects)
    db.flush()
    logger.info("Loaded %d records into 'outcomes'", len(out_objects))

    # 5. Load Data Quality Issues
    dq_objects = []
    for iss in all_issues:
        dq_objects.append(DataQualityIssue(
            file_id=iss["file_id"],
            record_id=iss["record_id"],
            row_number=iss["row_number"],
            column_name=iss["column_name"],
            issue_type=iss["issue_type"],
            severity=iss["severity"],
            raw_value=iss["raw_value"],
            description=iss["description"],
            status=iss["status"],
        ))
    db.add_all(dq_objects)
    db.commit()
    logger.info("Loaded %d issues into 'data_quality_issues'", len(dq_objects))
