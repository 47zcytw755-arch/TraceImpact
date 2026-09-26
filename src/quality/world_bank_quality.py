"""
Data Quality Validation Engine for World Bank Public Indicator Ingestion.
Enforces schema validity, completeness, numeric constraints, and idempotency.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text
from src.database.connection import engine


@dataclass
class WorldBankDQIssue:
    """Represents a data quality anomaly discovered in an API payload."""
    issue_type: str
    severity: str
    description: str
    country_code: Optional[str] = None
    indicator_code: Optional[str] = None
    year: Optional[int] = None
    raw_value: Optional[str] = None
    status: str = "OPEN"


class WorldBankValidator:
    """
    Validates World Bank observation records extracted from API pages.
    """

    @staticmethod
    def validate_observation(raw_rec: Dict[str, Any]) -> Tuple[bool, List[WorldBankDQIssue], Dict[str, Any]]:
        """
        Validates and normalizes a single raw observation from World Bank JSON.
        
        Returns:
            Tuple of:
            - is_valid (bool): True if record can be admitted to silver domain table.
            - issues (List[WorldBankDQIssue]): List of cataloged issues.
            - cleaned_data (Dict[str, Any]): Normalized record values.
        """
        issues: List[WorldBankDQIssue] = []

        # 1. Country extraction
        country_obj = raw_rec.get("country") or {}
        country_code = country_obj.get("id") or raw_rec.get("countryiso3code")
        country_name = country_obj.get("value")
        iso3_code = raw_rec.get("countryiso3code")

        if not country_code:
            issues.append(WorldBankDQIssue(
                issue_type="MISSING_COUNTRY",
                severity="ERROR",
                description="Observation record is missing country identification code.",
                raw_value=str(raw_rec.get("country")),
                status="QUARANTINED",
            ))

        # 2. Indicator extraction
        indicator_obj = raw_rec.get("indicator") or {}
        indicator_code = indicator_obj.get("id")
        indicator_name = indicator_obj.get("value")

        if not indicator_code:
            issues.append(WorldBankDQIssue(
                issue_type="MISSING_INDICATOR",
                severity="ERROR",
                description="Observation record is missing indicator identification code.",
                country_code=country_code,
                raw_value=str(raw_rec.get("indicator")),
                status="QUARANTINED",
            ))

        # 3. Year extraction and validation
        raw_year = raw_rec.get("date")
        year = None
        try:
            if raw_year is not None:
                year = int(str(raw_year).strip())
                if year < 1960 or year > 2030:
                    issues.append(WorldBankDQIssue(
                        issue_type="INVALID_YEAR_RANGE",
                        severity="ERROR",
                        description=f"Year {year} is out of expected reporting bounds (1960-2030).",
                        country_code=country_code,
                        indicator_code=indicator_code,
                        year=year,
                        raw_value=str(raw_year),
                        status="QUARANTINED",
                    ))
            else:
                issues.append(WorldBankDQIssue(
                    issue_type="MISSING_YEAR",
                    severity="ERROR",
                    description="Observation record is missing reporting year/date.",
                    country_code=country_code,
                    indicator_code=indicator_code,
                    status="QUARANTINED",
                ))
        except (ValueError, TypeError):
            issues.append(WorldBankDQIssue(
                issue_type="INVALID_YEAR_FORMAT",
                severity="ERROR",
                description=f"Year '{raw_year}' could not be parsed as an integer.",
                country_code=country_code,
                indicator_code=indicator_code,
                raw_value=str(raw_year),
                status="QUARANTINED",
            ))

        # 4. Numeric Value validation
        raw_val = raw_rec.get("value")
        indicator_value = None
        if raw_val is None:
            # Missing values in public indicators are common (non-blocking INFO/WARNING)
            issues.append(WorldBankDQIssue(
                issue_type="MISSING_VALUE",
                severity="INFO",
                description=f"No value reported for {country_code} in {year} (null observation).",
                country_code=country_code,
                indicator_code=indicator_code,
                year=year,
                raw_value=None,
                status="RESOLVED",
            ))
        else:
            try:
                indicator_value = float(raw_val)
            except (ValueError, TypeError):
                issues.append(WorldBankDQIssue(
                    issue_type="INVALID_NUMERIC",
                    severity="ERROR",
                    description=f"Metric value '{raw_val}' could not be parsed as numeric.",
                    country_code=country_code,
                    indicator_code=indicator_code,
                    year=year,
                    raw_value=str(raw_val),
                    status="QUARANTINED",
                ))

        # Determine overall validity: if any ERROR severity exists, quarantine record
        has_blocking_error = any(iss.severity == "ERROR" for iss in issues)
        is_valid = not has_blocking_error and indicator_value is not None

        cleaned_data = {
            "country_code": country_code,
            "country_name": country_name,
            "iso3_code": iso3_code,
            "indicator_code": indicator_code,
            "indicator_name": indicator_name,
            "year": year,
            "indicator_value": indicator_value,
            "obs_status": raw_rec.get("obs_status") or "",
            "unit": raw_rec.get("unit") or "",
            "decimal_places": int(raw_rec.get("decimal") or 0),
        }

        return is_valid, issues, cleaned_data


def persist_dq_issues(
    run_id: int,
    raw_response_id: int,
    issues: List[WorldBankDQIssue],
) -> None:
    """
    Persists data quality issues to world_bank_data_quality_issues audit table.
    """
    if not issues:
        return

    sql = text("""
        INSERT INTO world_bank_data_quality_issues (
            run_id, raw_response_id, country_code, indicator_code, year,
            issue_type, severity, raw_value, description, status, detected_at
        ) VALUES (
            :run_id, :raw_response_id, :country_code, :indicator_code, :year,
            :issue_type, :severity, :raw_value, :description, :status, CURRENT_TIMESTAMP
        );
    """)

    params = [
        {
            "run_id": run_id,
            "raw_response_id": raw_response_id,
            "country_code": iss.country_code,
            "indicator_code": iss.indicator_code,
            "year": iss.year,
            "issue_type": iss.issue_type,
            "severity": iss.severity,
            "raw_value": iss.raw_value,
            "description": iss.description,
            "status": iss.status,
        }
        for iss in issues
    ]

    with engine.begin() as conn:
        conn.execute(sql, params)
