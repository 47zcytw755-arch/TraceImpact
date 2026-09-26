"""
Day 2 Pipeline Runner: Data Cleaning, Quality Validation, and Domain Loading.

WHAT:
Orchestrates the complete Day 2 data pipeline:
1. Fetches immutable staged records from `source_records`.
2. Normalizes column headers, dates, program names, locations, and numbers.
3. Detects duplicates, missing values, boundary violations, and orphan references.
4. Generates clean datasets in `data/processed/`.
5. Loads verified domain records into PostgreSQL tables (`beneficiaries`, `attendance`, `expenses`, `outcomes`).
6. Catalogs all data quality issues in `data_quality_issues`.
7. Prints a comprehensive execution audit summary.

WHY:
Provides a single reproducible entry point (`python -m src.cleaning.run_pipeline`)
for testing and operational automation.

HOW:
Reads staged JSONB dictionaries from PostgreSQL, passes them through pure functional
transformers, collects structured DataQualityIssue records, and commits results
in an atomic database transaction.

CONCEPT:
Batch ETL / ELT Pipeline Orchestration with Data Quality Gates & Audit Logging.
"""

import sys
import logging
from typing import Dict, List, Any, Tuple
import pandas as pd
from sqlalchemy.orm import Session
from src.database.connection import SessionLocal
from src.database.models import SourceFile, SourceRecord, Program
from src.cleaning.transformers import (
    transform_beneficiaries,
    transform_attendance,
    transform_expenses,
    transform_outcomes,
)
from src.cleaning.loader import export_processed_csvs, load_domain_and_issues

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_staged_records_by_file(db: Session, file_name: str) -> Tuple[int, List[Dict[str, Any]]]:
    """
    WHAT:
    Retrieves all staged JSONB rows for a specific source file, preserving original record_id.
    """
    source_file = db.query(SourceFile).filter(SourceFile.file_name == file_name).first()
    if not source_file:
        raise FileNotFoundError(f"Source file '{file_name}' not found in source_files staging table. Run ingestion first.")

    records = (
        db.query(SourceRecord)
        .filter(SourceRecord.file_id == source_file.file_id)
        .order_by(SourceRecord.row_index)
        .all()
    )

    flattened = []
    for r in records:
        row_dict = dict(r.raw_data)
        row_dict["record_id"] = r.record_id
        row_dict["row_index"] = r.row_index
        row_dict["file_id"] = r.file_id
        flattened.append(row_dict)

    return source_file.file_id, flattened


def run_pipeline() -> Dict[str, Any]:
    """
    Executes the complete Day 2 cleaning, validation, and domain loading pipeline.
    """
    logger.info("==================================================================")
    logger.info("STARTING DAY 2: DATA CLEANING, VALIDATION & DOMAIN LOADING PIPELINE")
    logger.info("==================================================================")

    db = SessionLocal()
    try:
        # 1. Fetch Master Programs Catalog
        programs = db.query(Program).all()
        valid_program_ids = {p.program_id for p in programs}
        logger.info("Retrieved %d registered master programs: %s", len(valid_program_ids), sorted(list(valid_program_ids)))

        # 2. Process Beneficiaries
        ben_file_id, ben_staged = get_staged_records_by_file(db, "beneficiaries.csv")
        clean_ben_df, ben_issues, valid_ben_ids = transform_beneficiaries(ben_staged, ben_file_id)
        logger.info("Beneficiaries processed: %d staged -> %d valid (%d issues)", len(ben_staged), len(clean_ben_df), len(ben_issues))

        # 3. Process Attendance
        att_file_id, att_staged = get_staged_records_by_file(db, "attendance.csv")
        clean_att_df, att_issues = transform_attendance(att_staged, att_file_id, valid_ben_ids, valid_program_ids)
        logger.info("Attendance processed: %d staged -> %d valid (%d issues)", len(att_staged), len(clean_att_df), len(att_issues))

        # 4. Process Expenses
        exp_file_id, exp_staged = get_staged_records_by_file(db, "expenses.csv")
        clean_exp_df, exp_issues = transform_expenses(exp_staged, exp_file_id, valid_program_ids)
        logger.info("Expenses processed: %d staged -> %d valid (%d issues)", len(exp_staged), len(clean_exp_df), len(exp_issues))

        # 5. Process Outcomes
        out_file_id, out_staged = get_staged_records_by_file(db, "outcomes.csv")
        clean_out_df, out_issues = transform_outcomes(out_staged, out_file_id, valid_ben_ids, valid_program_ids)
        logger.info("Outcomes processed: %d staged -> %d valid (%d issues)", len(out_staged), len(clean_out_df), len(out_issues))

        # 6. Export to data/processed/
        cleaned_dfs = {
            "beneficiaries": clean_ben_df,
            "attendance": clean_att_df,
            "expenses": clean_exp_df,
            "outcomes": clean_out_df,
        }
        export_processed_csvs(cleaned_dfs)

        # 7. Load into PostgreSQL Domain Tables and Data Quality Issues
        all_issues = ben_issues + att_issues + exp_issues + out_issues
        load_domain_and_issues(db, cleaned_dfs, all_issues)

        # 8. Compile Audit Metrics
        summary = {
            "programs": len(programs),
            "beneficiaries": {
                "staged": len(ben_staged),
                "valid": len(clean_ben_df),
                "issues": len(ben_issues),
            },
            "attendance": {
                "staged": len(att_staged),
                "valid": len(clean_att_df),
                "issues": len(att_issues),
            },
            "expenses": {
                "staged": len(exp_staged),
                "valid": len(clean_exp_df),
                "issues": len(exp_issues),
            },
            "outcomes": {
                "staged": len(out_staged),
                "valid": len(clean_out_df),
                "issues": len(out_issues),
            },
            "total_issues": len(all_issues),
            "issues_by_severity": {
                "ERROR": sum(1 for i in all_issues if i["severity"] == "ERROR"),
                "WARNING": sum(1 for i in all_issues if i["severity"] == "WARNING"),
                "INFO": sum(1 for i in all_issues if i["severity"] == "INFO"),
            },
            "issues_by_type": {},
        }
        for iss in all_issues:
            t = iss["issue_type"]
            summary["issues_by_type"][t] = summary["issues_by_type"].get(t, 0) + 1

        print_execution_summary(summary)
        return summary

    finally:
        db.close()


def print_execution_summary(s: Dict[str, Any]):
    """Prints a structured summary of pipeline execution."""
    print("\n" + "=" * 60)
    print("           TRACEIMPACT DAY 2 EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Master Programs: {s['programs']}")
    print("-" * 60)
    print(f"Beneficiaries:")
    print(f"  Staged Records:       {s['beneficiaries']['staged']}")
    print(f"  Clean Domain Loaded:  {s['beneficiaries']['valid']}")
    print(f"  Issues Detected:      {s['beneficiaries']['issues']}")
    print("-" * 60)
    print(f"Attendance Logs:")
    print(f"  Staged Records:       {s['attendance']['staged']}")
    print(f"  Clean Domain Loaded:  {s['attendance']['valid']}")
    print(f"  Issues Detected:      {s['attendance']['issues']}")
    print("-" * 60)
    print(f"Expenses:")
    print(f"  Staged Records:       {s['expenses']['staged']}")
    print(f"  Clean Domain Loaded:  {s['expenses']['valid']}")
    print(f"  Issues Detected:      {s['expenses']['issues']}")
    print("-" * 60)
    print(f"Outcomes Surveys:")
    print(f"  Staged Records:       {s['outcomes']['staged']}")
    print(f"  Clean Domain Loaded:  {s['outcomes']['valid']}")
    print(f"  Issues Detected:      {s['outcomes']['issues']}")
    print("-" * 60)
    print(f"Data Quality Audit Totals:")
    print(f"  Total Issues Logged:  {s['total_issues']}")
    print(f"  Severity Breakdown:")
    for sev, count in s["issues_by_severity"].items():
        print(f"    - {sev:<8}: {count}")
    print(f"  Issue Types Breakdown:")
    for itype, count in sorted(s["issues_by_type"].items()):
        print(f"    - {itype:<20}: {count}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    from typing import Tuple
    run_pipeline()
