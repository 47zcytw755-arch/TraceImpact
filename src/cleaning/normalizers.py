"""
Reusable Normalization Functions for TraceImpact Data Pipelines.

WHAT:
Provides pure, modular transformation functions for standardizing column names,
dates, program references, locations, numeric values, and privacy identifiers.

WHY:
Data entering from multiple field sources contains inconsistent formatting
(e.g., "₹12,500.00", "2 hrs", "DD/MM/YYYY", "digi-literacy"). Normalizing
these values is required before relational insertion, foreign key matching,
and accurate metric computation.

HOW:
Each function takes raw string inputs, handles null/empty cases, applies deterministic
parsing rules or mapping dictionaries, and returns clean Python types along with
diagnostic error messages if values are invalid.

CONCEPT:
Data Normalization & Defensive Parsing — ensuring data conforms to expected domain
types and business rules without silent corruption.
"""

import re
import hashlib
from datetime import datetime, date
from typing import Optional, Tuple, Any
import pandas as pd
from src.cleaning.column_maps import (
    COLUMN_NAME_MAPS,
    PROGRAM_ALIAS_TO_ID,
    LOCATION_NORMALIZATION_MAP,
    GENDER_NORMALIZATION_MAP,
    ATTENDANCE_STATUS_MAP,
    BOOLEAN_MAP,
)


def normalize_columns(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """
    WHAT:
    Renames DataFrame columns using an explicit canonical dictionary.

    WHY:
    Different field files use varying headers (e.g., 'participant_id' vs 'beneficiary_id',
    'expense_ref' vs 'expense_id'). Standardizing columns allows uniform downstream code.

    HOW:
    Looks up each cleaned column name in COLUMN_NAME_MAPS. If found, renames to canonical name.
    Preserves original columns if not in mapping.

    CONCEPT:
    Schema Unification across heterogeneous raw sources.
    """
    mapping = COLUMN_NAME_MAPS.get(dataset_name, {})
    new_cols = {}
    for col in df.columns:
        cleaned_col_key = str(col).strip().lower()
        if cleaned_col_key in mapping:
            new_cols[col] = mapping[cleaned_col_key]
        else:
            new_cols[col] = str(col).strip()
    return df.rename(columns=new_cols)


def parse_date(raw_date: Any) -> Tuple[Optional[date], Optional[str]]:
    """
    WHAT:
    Safely parses mixed date representations (YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY)
    into a Python datetime.date object.

    WHY:
    Date fields in spreadsheets often mix ISO formats with European or US formats.
    Silently converting invalid dates into arbitrary timestamps corrupts longitudinal
    impact metrics. Invalid dates must be detected and flagged.

    HOW:
    Tries multiple standard date formats sequentially. If no format matches or
    the value is an impossible calendar date (e.g., month 13), returns None with
    a descriptive error.

    CONCEPT:
    Multi-format Date Parsing without silent truncation or default epoch assignment.
    """
    if raw_date is None or pd.isna(raw_date):
        return None, None

    date_str = str(raw_date).strip()
    if not date_str or date_str.lower() in ["none", "nan", "null", ""]:
        return None, None

    # Common formats in nonprofit survey datasets
    candidate_formats = [
        "%Y-%m-%d",       # 2024-02-15
        "%d/%m/%Y",       # 15/02/2024 (common in India/UK)
        "%m/%d/%Y",       # 02/15/2024 (US)
        "%Y/%m/%d",       # 2024/02/15
        "%d-%m-%Y",       # 15-02-2024
        "%Y-%m-%d %H:%M:%S", # 2024-02-15 10:30:00
    ]

    for fmt in candidate_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date(), None
        except ValueError:
            continue

    return None, f"Invalid date format: '{date_str}'"


def normalize_program_name(raw_name: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    WHAT:
    Resolves informal program titles or codes (e.g., 'Digi-Literacy', 'Youth-Coding')
    to their canonical master program_id (e.g., 'PRG-001', 'PRG-003').

    WHY:
    Field logs rarely use rigid foreign key IDs. To populate relational foreign keys
    referencing `programs(program_id)`, we must map free-text titles deterministically.

    HOW:
    Cleans string, converts to lowercase, and checks `PROGRAM_ALIAS_TO_ID`.
    Returns (program_id, None) on match, or (None, error_description) if unmapped.

    CONCEPT:
    Entity Resolution & Controlled Vocabulary Alignment.
    """
    if raw_name is None or pd.isna(raw_name):
        return None, "Missing program identifier"

    clean_name = str(raw_name).strip().lower()
    if not clean_name:
        return None, "Empty program identifier"

    # Direct code match (e.g., 'PRG-001')
    upper_name = clean_name.upper()
    if upper_name in ["PRG-001", "PRG-002", "PRG-003", "PRG-004", "PRG-005"]:
        return upper_name, None

    # Alias dictionary lookup
    if clean_name in PROGRAM_ALIAS_TO_ID:
        return PROGRAM_ALIAS_TO_ID[clean_name], None

    return None, f"Unrecognized program title: '{raw_name}'"


def normalize_location(raw_location: Any) -> Optional[str]:
    """
    WHAT:
    Normalizes city/location strings (e.g., 'new delhi', 'Delhi NCR', 'noida ')
    to canonical city names.

    WHY:
    Enables accurate geographic aggregation for nonprofit regional impact dashboards.

    HOW:
    Looks up whitespace-stripped, lowercased string in `LOCATION_NORMALIZATION_MAP`.
    If not in map, strips excess whitespace and applies standard Title Casing.

    CONCEPT:
    Categorical Standardization.
    """
    if raw_location is None or pd.isna(raw_location):
        return None

    loc_str = str(raw_location).strip()
    if not loc_str or loc_str.lower() in ["none", "nan", "null"]:
        return None

    clean_key = loc_str.lower()
    if clean_key in LOCATION_NORMALIZATION_MAP:
        return LOCATION_NORMALIZATION_MAP[clean_key]

    # Controlled fallback: Clean multiple spaces, title case
    return " ".join(loc_str.split()).title()


def normalize_gender(raw_gender: Any) -> Optional[str]:
    """
    WHAT:
    Standardizes gender representations ('F', 'Female', 'm', 'Non-Binary').

    WHY:
    Nonprofit demographic metrics require consistent categorical groupings.

    HOW:
    Checks lowercased string against `GENDER_NORMALIZATION_MAP`.
    """
    if raw_gender is None or pd.isna(raw_gender):
        return None

    gender_str = str(raw_gender).strip().lower()
    return GENDER_NORMALIZATION_MAP.get(gender_str, str(raw_gender).strip())


def normalize_attendance_status(raw_status: Any) -> str:
    """
    WHAT:
    Normalizes attendance status ('present', 'P', 'Attended' -> 'Present').
    """
    if raw_status is None or pd.isna(raw_status):
        return "Present"

    clean_status = str(raw_status).strip().lower()
    return ATTENDANCE_STATUS_MAP.get(clean_status, "Present")


def parse_numeric(raw_val: Any) -> Tuple[Optional[float], Optional[str]]:
    """
    WHAT:
    Extracts a numeric float value from dirty inputs like '₹11,271.75', '2 hrs', '9116.77'.

    WHY:
    Financial and hours columns frequently contain formatting symbols, currency signs,
    or descriptive text from spreadsheet exports that cause SQL NUMERIC insertion failures.

    HOW:
    Strips currency symbols (₹, $, €), commas, and common unit suffixes (hrs, hr).
    Attempts float conversion. Returns (float_val, None) or (None, error_msg).

    CONCEPT:
    Coercive Numeric Parsing with Sanity Checks.
    """
    if raw_val is None or pd.isna(raw_val):
        return None, None

    val_str = str(raw_val).strip()
    if not val_str or val_str.lower() in ["none", "nan", "null", ""]:
        return None, None

    # Remove currency signs, commas, and unit words
    cleaned = re.sub(r"[₹$,€]", "", val_str)
    cleaned = re.sub(r"(?i)\s*(hrs|hr|hours|hour)", "", cleaned).strip()

    try:
        val = float(cleaned)
        return val, None
    except ValueError:
        return None, f"Non-numeric value: '{raw_val}'"


def normalize_boolean(raw_val: Any) -> Optional[bool]:
    """
    WHAT:
    Normalizes boolean representations ('Yes', 'Y', 'True', 'Pending').
    """
    if raw_val is None or pd.isna(raw_val):
        return False

    val_str = str(raw_val).strip().lower()
    return BOOLEAN_MAP.get(val_str, False)


def generate_anonymized_code(identifier: str, salt: str = "traceimpact_pii_salt_2024") -> str:
    """
    WHAT:
    Generates a deterministic 64-character SHA-256 hash for privacy protection.

    WHY:
    Beneficiary PII (personal names, phone numbers) must not be stored in cleartext
    in domain tables exposed to analytical queries.

    HOW:
    Concatenates identifier with a cryptographic salt and computes sha256.

    CONCEPT:
    Pseudonymization / Privacy by Design in data engineering.
    """
    payload = f"{salt}:{identifier}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
