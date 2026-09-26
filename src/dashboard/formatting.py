"""
Data Formatting and Presentation Utilities for Streamlit UI.

WHAT:
Standardizes the display of currencies, percentages, counts, and status badges.

WHY:
Ensures consistent visual hierarchy and clean number representation across all
dashboard pages without ad-hoc string formatting.
"""

from typing import Union, Any, Optional
from datetime import date, datetime
from decimal import Decimal


def format_currency(value: Optional[Union[float, Decimal, int]]) -> str:
    """Formats numeric values into Indian Rupee currency strings."""
    if value is None:
        return "₹0.00"
    try:
        val = float(value)
        return f"₹{val:,.2f}"
    except (ValueError, TypeError):
        return f"₹{value}"


def format_percentage(value: Optional[Union[float, Decimal, int]], decimals: int = 1) -> str:
    """Formats numeric values as percentages with specified decimal places."""
    if value is None:
        return "0.0%"
    try:
        val = float(value)
        return f"{val:.{decimals}f}%"
    except (ValueError, TypeError):
        return f"{value}%"


def format_number(value: Optional[Union[float, Decimal, int]], decimals: int = 0) -> str:
    """Formats numeric values with thousand-separator commas."""
    if value is None:
        return "0"
    try:
        val = float(value)
        if decimals == 0:
            return f"{int(round(val)):,}"
        return f"{val:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def format_date(value: Optional[Union[date, datetime, str]]) -> str:
    """Formats date objects or date strings into ISO YYYY-MM-DD."""
    if value is None:
        return "N/A"
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)


def get_severity_badge(severity: str) -> str:
    """Returns markdown badge representation of issue severity."""
    sev = str(severity).upper()
    if sev == "ERROR":
        return "🔴 ERROR"
    elif sev == "WARNING":
        return "🟡 WARNING"
    elif sev == "INFO":
        return "🔵 INFO"
    return sev


def get_status_badge(status: str) -> str:
    """Returns markdown badge representation of issue lifecycle status."""
    st = str(status).upper()
    if st == "OPEN":
        return "🟠 OPEN"
    elif st == "RESOLVED":
        return "🟢 RESOLVED"
    elif st == "ACCEPTED":
        return "🟣 ACCEPTED"
    return st
