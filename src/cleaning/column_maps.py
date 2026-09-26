"""
Explicit Column and Value Mapping Configurations for TraceImpact.

WHAT:
Defines declarative dictionaries that map heterogeneous source column names,
program name variations, dirty location strings, gender codes, and boolean flags
into standardized, canonical representations.

WHY:
Nonprofits receive data from diverse field staff, paper forms, and mobile apps.
Hardcoding ad-hoc inline replacements scattered across scripts leads to brittle,
untestable code. Centralized mapping configuration makes data contracts explicit,
auditable, and easily maintainable.

HOW:
Dictionary lookups with case-insensitive and whitespace-stripped keys provide
deterministic O(1) canonicalization.

CONCEPT:
Schema Harmonization & Data Contract — transforming non-standard input variants
into a controlled, uniform vocabulary before loading into a relational system.
"""

# -----------------------------------------------------------------------------
# 1. Column Name Normalization Mappings
# -----------------------------------------------------------------------------
# Maps various legacy, camelCase, or field-specific headers to canonical names.
COLUMN_NAME_MAPS = {
    "beneficiaries": {
        "beneficiary_id": "beneficiary_id",
        "beneficiaryid": "beneficiary_id",
        "participant_id": "beneficiary_id",
        "participantid": "beneficiary_id",
        "participant_code": "beneficiary_id",
        "full_name": "full_name",
        "fullname": "full_name",
        "name": "full_name",
        "gender": "gender",
        "sex": "gender",
        "age": "age",
        "city_location": "city_location",
        "location": "city_location",
        "city": "city_location",
        "registration_date": "registration_date",
        "registrationdate": "registration_date",
        "signup_date": "registration_date",
        "contact_phone": "contact_phone",
        "phone": "contact_phone",
        "mobile": "contact_phone",
    },
    "attendance": {
        "attendance_id": "attendance_id",
        "attendanceid": "attendance_id",
        "participant_id": "beneficiary_id",
        "participantid": "beneficiary_id",
        "beneficiary_id": "beneficiary_id",
        "program_title": "program_name",
        "program_name": "program_name",
        "program": "program_name",
        "programname": "program_name",
        "session_date": "session_date",
        "sessiondate": "session_date",
        "date": "session_date",
        "attendance_status": "attendance_status",
        "status": "attendance_status",
        "session_hours": "session_hours",
        "hours": "session_hours",
    },
    "expenses": {
        "expense_ref": "expense_id",
        "expenseref": "expense_id",
        "expense_id": "expense_id",
        "program_code": "program_id",
        "program_id": "program_id",
        "programid": "program_id",
        "expense_category": "expense_category",
        "category": "expense_category",
        "amount_spent": "amount",
        "amount": "amount",
        "cost": "amount",
        "incurred_date": "incurred_date",
        "expense_date": "incurred_date",
        "date": "incurred_date",
        "receipt_verified": "receipt_verified",
        "verified": "receipt_verified",
    },
    "outcomes": {
        "survey_id": "outcome_id",
        "surveyid": "outcome_id",
        "outcome_id": "outcome_id",
        "client_identifier": "beneficiary_id",
        "beneficiary_id": "beneficiary_id",
        "participant_id": "beneficiary_id",
        "program_id": "program_id",
        "programid": "program_id",
        "metric_name": "indicator_name",
        "indicator_name": "indicator_name",
        "indicator": "indicator_name",
        "baseline_score": "baseline_score",
        "exit_score": "exit_score",
        "evaluation_date": "evaluation_date",
        "survey_date": "evaluation_date",
        "date": "evaluation_date",
    },
    "programs": {
        "program_id": "program_id",
        "program_name": "program_name",
        "target_category": "target_category",
        "budget_allocated": "budget_allocated",
        "start_date": "start_date",
        "end_date": "end_date",
    }
}

# -----------------------------------------------------------------------------
# 2. Program Alias to Canonical Program ID Mapping
# -----------------------------------------------------------------------------
# Known variations logged in field sheets mapped to registered master program_id.
PROGRAM_ALIAS_TO_ID = {
    # PRG-001: Digital Literacy Initiative
    "prg-001": "PRG-001",
    "digital literacy initiative": "PRG-001",
    "digital literacy": "PRG-001",
    "digital-literacy": "PRG-001",
    "digi-literacy": "PRG-001",

    # PRG-002: Women Vocational Sewing
    "prg-002": "PRG-002",
    "women vocational sewing": "PRG-002",
    "vocational sewing": "PRG-002",
    "women sewing workshop": "PRG-002",

    # PRG-003: Youth Coding Bootcamp
    "prg-003": "PRG-003",
    "youth coding bootcamp": "PRG-003",
    "youth-coding": "PRG-003",
    "coding bootcamp": "PRG-003",

    # PRG-004: Elderly Healthcare Outreach
    "prg-004": "PRG-004",
    "elderly healthcare outreach": "PRG-004",
    "elderly health": "PRG-004",
    "health outreach": "PRG-004",

    # PRG-005: Community Nutrition Drive
    "prg-005": "PRG-005",
    "community nutrition drive": "PRG-005",
    "nutrition drive": "PRG-005",
    "community-nutrition": "PRG-005",
}

# -----------------------------------------------------------------------------
# 3. Location Normalization Mapping
# -----------------------------------------------------------------------------
LOCATION_NORMALIZATION_MAP = {
    "new delhi": "New Delhi",
    "delhi": "New Delhi",
    "n. delhi": "New Delhi",
    "delhi ncr": "New Delhi",
    "noida": "Noida",
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "faridabad": "Faridabad",
}

# -----------------------------------------------------------------------------
# 4. Gender Normalization Mapping
# -----------------------------------------------------------------------------
GENDER_NORMALIZATION_MAP = {
    "female": "Female",
    "f": "Female",
    "male": "Male",
    "m": "Male",
    "non-binary": "Non-Binary",
    "nb": "Non-Binary",
}

# -----------------------------------------------------------------------------
# 5. Attendance Status Normalization Mapping
# -----------------------------------------------------------------------------
ATTENDANCE_STATUS_MAP = {
    "present": "Present",
    "p": "Present",
    "attended": "Present",
    "absent": "Absent",
    "a": "Absent",
    "excused": "Excused",
    "e": "Excused",
}

# -----------------------------------------------------------------------------
# 6. Boolean Normalization Mapping
# -----------------------------------------------------------------------------
BOOLEAN_MAP = {
    "yes": True,
    "y": True,
    "true": True,
    "1": True,
    "no": False,
    "n": False,
    "false": False,
    "0": False,
    "pending": False,  # Pending receipt verification treated as unverified
}
