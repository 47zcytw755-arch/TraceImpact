"""
Dataset Transformers for TraceImpact Data Cleaning Pipeline.

WHAT:
End-to-end dataset transformation pipelines for:
- Beneficiaries (PII anonymization, demographic cleaning, duplicate identification).
- Attendance (program title resolution, check-in deduplication, referential integrity).
- Expenses (currency string sanitization, non-negative validation, program attribution).
- Outcomes (score boundary enforcement, evaluation dates, metric naming).

WHY:
Transforms raw staged JSON dictionaries into clean, relational Pandas DataFrames
ready for PostgreSQL domain table loading while capturing all data quality anomalies.

HOW:
Each transformer:
1. Normalizes column names.
2. Applies field-level normalizers (dates, numbers, strings).
3. Executes validation and anomaly detection rules.
4. Quarantines invalid or duplicate records into DataQualityIssue audit logs.
5. Retains `source_record_id` on every clean row for lineage tracking.

CONCEPT:
Extract-Transform-Validate (ETV) Architecture in Modern Data Engineering.
"""

from typing import List, Dict, Any, Tuple, Set
import pandas as pd
from src.cleaning.normalizers import (
    normalize_columns,
    parse_date,
    normalize_program_name,
    normalize_location,
    normalize_gender,
    normalize_attendance_status,
    parse_numeric,
    normalize_boolean,
    generate_anonymized_code,
)
from src.cleaning.validators import (
    IssueCollector,
    validate_beneficiary_record,
    validate_attendance_record,
    validate_expense_record,
    validate_outcome_record,
)


def transform_beneficiaries(
    staged_records: List[Dict[str, Any]],
    file_id: int,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]], Set[str]]:
    """
    WHAT:
    Transforms raw beneficiary records into clean demographic rows with anonymized PII.

    WHY:
    Guarantees participant uniqueness, data consistency, and PII anonymization.

    HOW:
    - Standardizes column names.
    - Anonymizes full_name into anonymized_code.
    - Cleans gender and city location.
    - Validates uniqueness of beneficiary_id and person identities.
    """
    collector = IssueCollector(file_id=file_id, file_name="beneficiaries.csv")
    seen_ids: Set[str] = set()
    seen_persons: Dict[str, str] = {}
    valid_beneficiary_ids: Set[str] = set()
    clean_rows: List[Dict[str, Any]] = []

    # Convert to DataFrame for column normalization
    df_raw = pd.DataFrame(staged_records)
    df_norm = normalize_columns(df_raw, "beneficiaries")

    for idx, row in df_norm.iterrows():
        rec_id = row.get("record_id")
        row_num = row.get("row_index", idx + 1)
        raw_b_id = row.get("beneficiary_id")
        raw_name = row.get("full_name")
        raw_phone = row.get("contact_phone")
        raw_reg_date = row.get("registration_date")
        raw_gender = row.get("gender")
        raw_age = row.get("age")
        raw_loc = row.get("city_location")

        # 1. Parse date
        clean_date, date_err = parse_date(raw_reg_date)
        if date_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="registration_date",
                issue_type="INVALID_DATE",
                severity="WARNING",
                raw_value=raw_reg_date,
                description=date_err,
            )

        # 2. Parse age
        clean_age = None
        if raw_age is not None and not pd.isna(raw_age) and str(raw_age).strip():
            try:
                clean_age = int(float(raw_age))
            except ValueError:
                collector.add_issue(
                    record_id=rec_id,
                    row_number=row_num,
                    column_name="age",
                    issue_type="INVALID_NUMBER",
                    severity="WARNING",
                    raw_value=raw_age,
                    description=f"Unparseable age value: '{raw_age}'",
                )

        # 3. Clean categorical values
        clean_gender = normalize_gender(raw_gender)
        clean_loc = normalize_location(raw_loc)
        anon_code = generate_anonymized_code(f"{raw_b_id}:{raw_name}") if raw_name else None

        # Build candidate record
        cand_dict = {
            "beneficiary_id": str(raw_b_id).strip().upper() if raw_b_id else None,
            "source_record_id": rec_id,
            "anonymized_code": anon_code,
            "gender": clean_gender,
            "age": clean_age,
            "city_location": clean_loc,
            "registration_date": clean_date,
            "full_name": raw_name,
            "contact_phone": raw_phone,
        }

        # 4. Validate
        is_valid = validate_beneficiary_record(
            row=cand_dict,
            row_idx=row_num,
            record_id=rec_id,
            seen_ids=seen_ids,
            seen_persons=seen_persons,
            collector=collector,
        )

        if is_valid:
            valid_b_id = cand_dict["beneficiary_id"]
            valid_beneficiary_ids.add(valid_b_id)
            clean_rows.append({
                "beneficiary_id": valid_b_id,
                "source_record_id": rec_id,
                "anonymized_code": anon_code,
                "gender": clean_gender,
                "age": clean_age,
                "city_location": clean_loc,
                "registration_date": clean_date,
            })

    clean_df = pd.DataFrame(clean_rows)
    return clean_df, collector.issues, valid_beneficiary_ids


def transform_attendance(
    staged_records: List[Dict[str, Any]],
    file_id: int,
    valid_beneficiary_ids: Set[str],
    valid_program_ids: Set[str],
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    WHAT:
    Transforms attendance logs, resolving informal program titles and discarding duplicate check-ins.
    """
    collector = IssueCollector(file_id=file_id, file_name="attendance.csv")
    seen_checkins: Set[str] = set()
    clean_rows: List[Dict[str, Any]] = []

    df_raw = pd.DataFrame(staged_records)
    df_norm = normalize_columns(df_raw, "attendance")

    for idx, row in df_norm.iterrows():
        rec_id = row.get("record_id")
        row_num = row.get("row_index", idx + 1)
        raw_att_id = row.get("attendance_id")
        raw_b_id = row.get("beneficiary_id")
        raw_prg_title = row.get("program_name")
        raw_date = row.get("session_date")
        raw_status = row.get("attendance_status")
        raw_hours = row.get("session_hours")

        # 1. Resolve program title to canonical program_id
        prog_id, prog_err = normalize_program_name(raw_prg_title)
        if prog_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="program_title",
                issue_type="UNMATCHED_REFERENCE",
                severity="ERROR",
                raw_value=raw_prg_title,
                description=prog_err,
            )

        # 2. Parse session date
        clean_date, date_err = parse_date(raw_date)
        if date_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="session_date",
                issue_type="INVALID_DATE",
                severity="ERROR",
                raw_value=raw_date,
                description=date_err,
            )

        # 3. Parse session hours (handles strings like '2 hrs')
        clean_hours, hours_err = parse_numeric(raw_hours)
        if hours_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="session_hours",
                issue_type="INVALID_NUMBER",
                severity="WARNING",
                raw_value=raw_hours,
                description=hours_err,
            )
            clean_hours = 0.0
        elif raw_hours is not None and isinstance(raw_hours, str) and ("hr" in raw_hours.lower()):
            # Log format normalization issue
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="session_hours",
                issue_type="INCONSISTENT_VALUE",
                severity="INFO",
                raw_value=raw_hours,
                description=f"Session hours '{raw_hours}' normalized to numeric {clean_hours:.2f}.",
                status="RESOLVED",
            )

        clean_status = normalize_attendance_status(raw_status)
        clean_b_id = str(raw_b_id).strip().upper() if raw_b_id else None

        cand_dict = {
            "attendance_id": str(raw_att_id).strip().upper() if raw_att_id else None,
            "source_record_id": rec_id,
            "beneficiary_id": clean_b_id,
            "program_id": prog_id,
            "session_date": clean_date,
            "attendance_status": clean_status,
            "session_hours": clean_hours if clean_hours is not None else 0.0,
            "program_title": raw_prg_title,
        }

        # 4. Validate
        is_valid = validate_attendance_record(
            row=cand_dict,
            row_idx=row_num,
            record_id=rec_id,
            seen_checkins=seen_checkins,
            valid_beneficiary_ids=valid_beneficiary_ids,
            collector=collector,
        )

        if is_valid:
            clean_rows.append({
                "attendance_id": cand_dict["attendance_id"],
                "source_record_id": rec_id,
                "beneficiary_id": clean_b_id,
                "program_id": prog_id,
                "session_date": clean_date,
                "attendance_status": clean_status,
                "session_hours": clean_hours if clean_hours is not None else 0.0,
            })

    clean_df = pd.DataFrame(clean_rows)
    return clean_df, collector.issues


def transform_expenses(
    staged_records: List[Dict[str, Any]],
    file_id: int,
    valid_program_ids: Set[str],
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    WHAT:
    Transforms expense records, sanitizing currency strings ('₹11,271.75') and discarding negative costs.
    """
    collector = IssueCollector(file_id=file_id, file_name="expenses.csv")
    clean_rows: List[Dict[str, Any]] = []

    df_raw = pd.DataFrame(staged_records)
    df_norm = normalize_columns(df_raw, "expenses")

    for idx, row in df_norm.iterrows():
        rec_id = row.get("record_id")
        row_num = row.get("row_index", idx + 1)
        raw_exp_id = row.get("expense_id")
        raw_prg_id = row.get("program_id")
        raw_cat = row.get("expense_category")
        raw_amt = row.get("amount")
        raw_date = row.get("incurred_date")
        raw_ver = row.get("receipt_verified")

        # 1. Parse date
        clean_date, date_err = parse_date(raw_date)
        if date_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="incurred_date",
                issue_type="INVALID_DATE",
                severity="ERROR",
                raw_value=raw_date,
                description=date_err,
            )

        # 2. Parse numeric amount and flag currency symbol formatting
        clean_amt, amt_err = parse_numeric(raw_amt)
        if amt_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="amount_spent",
                issue_type="INVALID_NUMBER",
                severity="ERROR",
                raw_value=raw_amt,
                description=amt_err,
            )
        elif raw_amt is not None and isinstance(raw_amt, str) and ("₹" in raw_amt or "$" in raw_amt or "," in raw_amt):
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="amount_spent",
                issue_type="INVALID_FORMAT",
                severity="INFO",
                raw_value=raw_amt,
                description=f"Currency string '{raw_amt}' sanitized to numeric float {clean_amt:.2f}.",
                status="RESOLVED",
            )

        # 3. Clean boolean verification flag
        clean_verified = normalize_boolean(raw_ver)
        clean_prg_id = str(raw_prg_id).strip().upper() if raw_prg_id else None

        cand_dict = {
            "expense_id": str(raw_exp_id).strip().upper() if raw_exp_id else None,
            "source_record_id": rec_id,
            "program_id": clean_prg_id,
            "expense_category": str(raw_cat).strip() if raw_cat and not pd.isna(raw_cat) else "General Operational",
            "amount": clean_amt,
            "incurred_date": clean_date,
            "receipt_verified": clean_verified,
        }

        # 4. Validate
        is_valid = validate_expense_record(
            row=cand_dict,
            row_idx=row_num,
            record_id=rec_id,
            valid_program_ids=valid_program_ids,
            collector=collector,
        )

        if is_valid:
            clean_rows.append(cand_dict)

    clean_df = pd.DataFrame(clean_rows)
    return clean_df, collector.issues


def transform_outcomes(
    staged_records: List[Dict[str, Any]],
    file_id: int,
    valid_beneficiary_ids: Set[str],
    valid_program_ids: Set[str],
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    WHAT:
    Transforms outcome survey scores, enforcing boundary conditions [0.0, 100.0].
    """
    collector = IssueCollector(file_id=file_id, file_name="outcomes.csv")
    clean_rows: List[Dict[str, Any]] = []

    df_raw = pd.DataFrame(staged_records)
    df_norm = normalize_columns(df_raw, "outcomes")

    for idx, row in df_norm.iterrows():
        rec_id = row.get("record_id")
        row_num = row.get("row_index", idx + 1)
        raw_out_id = row.get("outcome_id")
        raw_b_id = row.get("beneficiary_id")
        raw_prg_id = row.get("program_id")
        raw_metric = row.get("indicator_name")
        raw_base = row.get("baseline_score")
        raw_exit = row.get("exit_score")
        raw_date = row.get("evaluation_date")

        # 1. Parse date
        clean_date, date_err = parse_date(raw_date)
        if date_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="evaluation_date",
                issue_type="INVALID_DATE",
                severity="ERROR",
                raw_value=raw_date,
                description=date_err,
            )

        # 2. Parse scores
        clean_base, _ = parse_numeric(raw_base)
        clean_exit, exit_err = parse_numeric(raw_exit)
        if exit_err:
            collector.add_issue(
                record_id=rec_id,
                row_number=row_num,
                column_name="exit_score",
                issue_type="INVALID_NUMBER",
                severity="ERROR",
                raw_value=raw_exit,
                description=exit_err,
            )

        clean_b_id = str(raw_b_id).strip().upper() if raw_b_id else None
        clean_prg_id = str(raw_prg_id).strip().upper() if raw_prg_id else None

        cand_dict = {
            "outcome_id": str(raw_out_id).strip().upper() if raw_out_id else None,
            "source_record_id": rec_id,
            "beneficiary_id": clean_b_id,
            "program_id": clean_prg_id,
            "indicator_name": str(raw_metric).strip() if raw_metric else "Evaluation",
            "baseline_score": clean_base,
            "exit_score": clean_exit,
            "evaluation_date": clean_date,
        }

        # 3. Validate
        is_valid = validate_outcome_record(
            row=cand_dict,
            row_idx=row_num,
            record_id=rec_id,
            valid_beneficiary_ids=valid_beneficiary_ids,
            valid_program_ids=valid_program_ids,
            collector=collector,
        )

        if is_valid:
            clean_rows.append(cand_dict)

    clean_df = pd.DataFrame(clean_rows)
    return clean_df, collector.issues
