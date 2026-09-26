"""
Data Quality Validation and Issue Detection for TraceImpact.

WHAT:
Detects data-quality anomalies across all datasets:
- Exact and logical duplicates (duplicate IDs, duplicate check-ins, duplicate persons).
- Missing required vs optional values (differentiating WARNING vs ERROR).
- Invalid numbers (negative expenses, out-of-range outcome scores).
- Unmatched entity references (orphaned foreign keys in attendance, expenses, outcomes).
- Format inconsistencies (currency signs, non-numeric strings).

WHY:
Nonprofit spreadsheets frequently have dirty data. Silently dropping records hides
underlying collection issues; silently accepting invalid records distorts donor reporting.
Cataloging every issue in an immutable audit table maintains transparency and trust.

HOW:
Defines rule-based validator functions that inspect rows, collect structured issue
dictionaries with severity (INFO/WARNING/ERROR), and decide whether a record is
eligible for domain loading or quarantined.

CONCEPT:
Data Observability & Non-Destructive Validation — tracking data quality as first-class
metadata while preserving end-to-end traceability to original source records.
"""

from typing import Dict, List, Any, Optional, Set
import pandas as pd


class IssueCollector:
    """
    Collects structured DataQualityIssue records during pipeline execution.
    """

    def __init__(self, file_id: Optional[int] = None, file_name: Optional[str] = None):
        self.file_id = file_id
        self.file_name = file_name
        self.issues: List[Dict[str, Any]] = []

    def add_issue(
        self,
        record_id: Optional[int],
        row_number: int,
        column_name: str,
        issue_type: str,
        severity: str,
        raw_value: Any,
        description: str,
        status: str = "OPEN",
    ):
        """
        WHAT: Records an individual data quality finding.
        """
        self.issues.append({
            "file_id": self.file_id,
            "record_id": record_id,
            "row_number": row_number,
            "column_name": column_name,
            "issue_type": issue_type,       # DUPLICATE, MISSING_VALUE, INVALID_DATE, INVALID_NUMBER, UNMATCHED_REFERENCE, INCONSISTENT_VALUE, INVALID_FORMAT
            "severity": severity,           # INFO, WARNING, ERROR
            "raw_value": str(raw_value) if raw_value is not None else None,
            "description": description,
            "status": status,               # OPEN, RESOLVED, ACCEPTED
        })

    def count(self) -> int:
        return len(self.issues)

    def filter_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        return [iss for iss in self.issues if iss["severity"] == severity]


def validate_beneficiary_record(
    row: Dict[str, Any],
    row_idx: int,
    record_id: Optional[int],
    seen_ids: Set[str],
    seen_persons: Dict[str, str],
    collector: IssueCollector,
) -> bool:
    """
    WHAT:
    Validates a beneficiary record for duplicate IDs, duplicate person identities,
    missing demographic data, and formatting issues.

    WHY:
    Beneficiary records form the core entity table. Corrupted or duplicated participants
    distort reach counts and attendance metrics.

    HOW:
    - Checks duplicate beneficiary_id.
    - Checks duplicate person signature (lowercased full_name + phone).
    - Checks missing required fields (id, registration_date).
    - Checks optional fields (age, phone).
    Returns True if valid for domain loading, False if quarantined.

    CONCEPT:
    Entity Deduplication & Integrity Validation.
    """
    is_valid = True
    b_id = row.get("beneficiary_id")
    full_name = row.get("full_name")
    phone = row.get("contact_phone")
    age = row.get("age")
    reg_date = row.get("registration_date")

    # 1. Missing Required ID
    if not b_id or pd.isna(b_id) or str(b_id).strip() == "":
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="beneficiary_id",
            issue_type="MISSING_VALUE",
            severity="ERROR",
            raw_value=b_id,
            description="Beneficiary record is missing primary beneficiary_id.",
        )
        return False

    b_id_clean = str(b_id).strip().upper()

    # 2. Duplicate Primary ID
    if b_id_clean in seen_ids:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="beneficiary_id",
            issue_type="DUPLICATE",
            severity="ERROR",
            raw_value=b_id,
            description=f"Duplicate beneficiary_id '{b_id_clean}' detected in source dataset.",
        )
        return False
    seen_ids.add(b_id_clean)

    # 3. Duplicate Person Detection (Different ID but identical name & phone)
    if full_name and phone and not pd.isna(full_name) and not pd.isna(phone):
        person_signature = f"{str(full_name).strip().lower()}:{str(phone).strip()}"
        if person_signature in seen_persons:
            orig_id = seen_persons[person_signature]
            collector.add_issue(
                record_id=record_id,
                row_number=row_idx,
                column_name="full_name",
                issue_type="DUPLICATE",
                severity="WARNING",
                raw_value=full_name,
                description=f"Person '{full_name}' with phone '{phone}' already registered as {orig_id}; potential duplicate participant under new ID '{b_id_clean}'.",
                status="OPEN"
            )
            # We flag with WARNING as requested by duplicate rules:
            # "A beneficiary should not be considered a duplicate simply because two rows have the same name if another reliable identifier exists."
            # Since b_id is unique, we allow loading with WARNING flag so traceability is maintained.
        else:
            seen_persons[person_signature] = b_id_clean

    # 4. Missing Optional Demographic Fields (Age, Phone)
    if age is None or pd.isna(age) or str(age).strip() == "":
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="age",
            issue_type="MISSING_VALUE",
            severity="WARNING",
            raw_value=age,
            description=f"Beneficiary '{b_id_clean}' is missing age value.",
        )

    if not phone or pd.isna(phone) or str(phone).strip() == "":
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="contact_phone",
            issue_type="MISSING_VALUE",
            severity="INFO",
            raw_value=phone,
            description=f"Beneficiary '{b_id_clean}' has no contact phone registered.",
        )

    # 5. Missing / Invalid Registration Date
    if not reg_date or pd.isna(reg_date):
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="registration_date",
            issue_type="MISSING_VALUE",
            severity="WARNING",
            raw_value=reg_date,
            description=f"Beneficiary '{b_id_clean}' is missing registration_date.",
        )

    return is_valid


def validate_attendance_record(
    row: Dict[str, Any],
    row_idx: int,
    record_id: Optional[int],
    seen_checkins: Set[str],
    valid_beneficiary_ids: Set[str],
    collector: IssueCollector,
) -> bool:
    """
    WHAT:
    Validates attendance records for duplicate check-ins, unparseable hours,
    unmatched participant references, and missing program IDs.

    WHY:
    Double-logging by field staff artificially inflates participant session counts.
    Orphan records pointing to non-existent beneficiaries cause SQL Foreign Key
    constraint violations.

    HOW:
    - Checks duplicate check-in key: (beneficiary_id, program_id, session_date).
    - Verifies beneficiary_id exists in registered beneficiaries set.
    - Verifies program_id is resolved and valid.
    - Flags unparseable session hours.
    Returns True if valid for domain table loading, False if quarantined.

    CONCEPT:
    Foreign Key Validation & Multi-column Uniqueness Constraints in Application Logic.
    """
    b_id = row.get("beneficiary_id")
    program_id = row.get("program_id")
    session_date = row.get("session_date")
    session_hours = row.get("session_hours")
    att_id = row.get("attendance_id")

    # 1. Check Missing Date
    if not session_date or pd.isna(session_date):
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="session_date",
            issue_type="MISSING_VALUE",
            severity="ERROR",
            raw_value=session_date,
            description=f"Attendance record '{att_id}' is missing session_date.",
        )
        return False

    # 2. Check Unmatched / Missing Program
    if not program_id:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="program_title",
            issue_type="UNMATCHED_REFERENCE",
            severity="ERROR",
            raw_value=row.get("program_title") or row.get("program_name"),
            description=f"Attendance record '{att_id}' references an unresolvable program title.",
        )
        return False

    # 3. Check Unmatched Beneficiary Reference (Referential Integrity)
    if not b_id or b_id not in valid_beneficiary_ids:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="participant_id",
            issue_type="UNMATCHED_REFERENCE",
            severity="ERROR",
            raw_value=b_id,
            description=f"Attendance record '{att_id}' references unknown/unregistered participant '{b_id}'.",
        )
        return False

    # 4. Check Duplicate Check-in (Same participant + same program + same date)
    checkin_key = f"{b_id}:{program_id}:{session_date}"
    if checkin_key in seen_checkins:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="attendance_id",
            issue_type="DUPLICATE",
            severity="ERROR",
            raw_value=att_id,
            description=f"Duplicate attendance check-in for participant '{b_id}' in program '{program_id}' on date '{session_date}'.",
        )
        return False
    seen_checkins.add(checkin_key)

    # 5. Check Non-numeric / Missing Session Hours
    if session_hours is None or pd.isna(session_hours):
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="session_hours",
            issue_type="MISSING_VALUE",
            severity="WARNING",
            raw_value=session_hours,
            description=f"Attendance record '{att_id}' has missing session_hours; defaulted to 0.0.",
            status="RESOLVED"
        )

    return True


def validate_expense_record(
    row: Dict[str, Any],
    row_idx: int,
    record_id: Optional[int],
    valid_program_ids: Set[str],
    collector: IssueCollector,
) -> bool:
    """
    WHAT:
    Validates expense records for negative costs, missing program codes,
    unparseable amounts, and missing categories.

    WHY:
    Negative expenses or unallocated costs distort financial audit trails
    and budget vs expenditure calculations.

    HOW:
    - Verifies amount is positive numeric.
    - Verifies program_id is present and registered.
    - Flags missing expense_category as WARNING.
    Returns True if valid for domain table loading, False if quarantined.

    CONCEPT:
    Domain Rule Enforcement (Non-negativity & Referential Integrity).
    """
    exp_id = row.get("expense_id")
    prg_id = row.get("program_id")
    amt = row.get("amount")
    category = row.get("expense_category")
    incurred_date = row.get("incurred_date")

    # 1. Missing Date
    if not incurred_date or pd.isna(incurred_date):
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="incurred_date",
            issue_type="MISSING_VALUE",
            severity="ERROR",
            raw_value=incurred_date,
            description=f"Expense '{exp_id}' is missing incurred_date.",
        )
        return False

    # 2. Missing / Unmatched Program Reference
    if not prg_id or prg_id not in valid_program_ids:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="program_code",
            issue_type="UNMATCHED_REFERENCE",
            severity="ERROR",
            raw_value=prg_id,
            description=f"Expense '{exp_id}' has invalid or missing program code: '{prg_id}'.",
        )
        return False

    # 3. Invalid / Negative / Missing Numeric Amount
    if amt is None or pd.isna(amt):
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="amount_spent",
            issue_type="MISSING_VALUE",
            severity="ERROR",
            raw_value=amt,
            description=f"Expense '{exp_id}' has unparseable or missing amount.",
        )
        return False

    if amt < 0:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="amount_spent",
            issue_type="INVALID_NUMBER",
            severity="ERROR",
            raw_value=amt,
            description=f"Expense '{exp_id}' has negative amount: {amt:.2f}. Financial rules disallow negative expenditures.",
        )
        return False

    # 4. Missing Optional Category
    if not category or pd.isna(category) or str(category).strip() == "":
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="expense_category",
            issue_type="MISSING_VALUE",
            severity="WARNING",
            raw_value=category,
            description=f"Expense '{exp_id}' is missing expense_category.",
        )

    return True


def validate_outcome_record(
    row: Dict[str, Any],
    row_idx: int,
    record_id: Optional[int],
    valid_beneficiary_ids: Set[str],
    valid_program_ids: Set[str],
    collector: IssueCollector,
) -> bool:
    """
    WHAT:
    Validates survey evaluation scores for score boundaries (0 <= score <= 100),
    referential integrity, and evaluation dates.

    WHY:
    Outcomes data demonstrates nonprofit efficacy. Scores exceeding 100% indicate
    scale measurement errors and corrupt impact metrics.

    HOW:
    - Validates exit_score and baseline_score within [0.0, 100.0].
    - Verifies foreign keys to beneficiaries and programs.
    - Flags missing baseline_score as WARNING (partial evaluation).
    Returns True if valid for domain table loading, False if quarantined.

    CONCEPT:
    Range Boundary Verification & Nullable Evaluation State.
    """
    out_id = row.get("outcome_id")
    b_id = row.get("beneficiary_id")
    prg_id = row.get("program_id")
    eval_date = row.get("evaluation_date")
    base_score = row.get("baseline_score")
    exit_score = row.get("exit_score")

    # 1. Missing Date
    if not eval_date or pd.isna(eval_date):
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="evaluation_date",
            issue_type="MISSING_VALUE",
            severity="ERROR",
            raw_value=eval_date,
            description=f"Outcome survey '{out_id}' is missing evaluation_date.",
        )
        return False

    # 2. Check Referential Integrity
    if not b_id or b_id not in valid_beneficiary_ids:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="client_identifier",
            issue_type="UNMATCHED_REFERENCE",
            severity="ERROR",
            raw_value=b_id,
            description=f"Outcome survey '{out_id}' references unknown beneficiary '{b_id}'.",
        )
        return False

    if not prg_id or prg_id not in valid_program_ids:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="program_id",
            issue_type="UNMATCHED_REFERENCE",
            severity="ERROR",
            raw_value=prg_id,
            description=f"Outcome survey '{out_id}' references unknown program '{prg_id}'.",
        )
        return False

    # 3. Score Range Validation (0.0 to 100.0)
    if exit_score is not None and not pd.isna(exit_score):
        if exit_score < 0.0 or exit_score > 100.0:
            collector.add_issue(
                record_id=record_id,
                row_number=row_idx,
                column_name="exit_score",
                issue_type="INVALID_NUMBER",
                severity="ERROR",
                raw_value=exit_score,
                description=f"Outcome survey '{out_id}' exit_score {exit_score} is out of allowable bounds [0.0, 100.0].",
            )
            return False

    if base_score is not None and not pd.isna(base_score):
        if base_score < 0.0 or base_score > 100.0:
            collector.add_issue(
                record_id=record_id,
                row_number=row_idx,
                column_name="baseline_score",
                issue_type="INVALID_NUMBER",
                severity="ERROR",
                raw_value=base_score,
                description=f"Outcome survey '{out_id}' baseline_score {base_score} is out of allowable bounds [0.0, 100.0].",
            )
            return False
    else:
        collector.add_issue(
            record_id=record_id,
            row_number=row_idx,
            column_name="baseline_score",
            issue_type="MISSING_VALUE",
            severity="WARNING",
            raw_value=base_score,
            description=f"Outcome survey '{out_id}' has missing baseline_score.",
        )

    return True
