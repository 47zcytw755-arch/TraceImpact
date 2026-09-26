"""
Reusable Presentation Components for Streamlit Dashboard.

WHAT:
Standard UI widgets: metric cards, page headers, navigation sidebars, alert banners,
and empty-state containers.

WHY:
Enforces visual cohesion across all 4 dashboard pages and avoids boilerplate UI code.
"""

import streamlit as st
from datetime import datetime
from src.dashboard.db import check_db_health


def render_sidebar():
    """Renders the standard TraceImpact sidebar with metadata and connection status."""
    with st.sidebar:
        st.markdown("## 📊 **TraceImpact**")
        st.caption("Traceable Impact Reporting & Data Quality Platform")
        st.markdown("---")

        # Database health check indicator
        is_healthy = check_db_health()
        if is_healthy:
            st.success("🟢 PostgreSQL Connected")
        else:
            st.error("🔴 Database Disconnected")

        st.markdown("---")
        st.markdown("### 🧭 **Navigation Guide**")
        st.markdown(
            """
            - **1. Executive Summary**: Organization-wide impact KPIs & trends
            - **2. Program Analysis**: Deep-dive into individual initiatives
            - **3. Data Quality**: Observability scorecard & issue triage
            - **4. Traceability**: End-to-end audit drilldown to raw CSVs
            """
        )
        st.markdown("---")
        st.caption(f"System Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


def render_header(title: str, subtitle: str, icon: str = "📈"):
    """Renders consistent top banner on each dashboard page."""
    st.title(f"{icon} {title}")
    st.markdown(f"*{subtitle}*")
    st.markdown("---")


def render_empty_state(message: str = "No data found matching the selected criteria."):
    """Renders user-friendly empty state when queries return no results."""
    st.info(f"ℹ️ {message}")


def render_db_error():
    """Renders user-friendly database connection failure banner."""
    st.error(
        "⚠️ **Unable to connect to PostgreSQL database.**\n\n"
        "Please ensure your PostgreSQL server is running and credentials in `.env` are valid."
    )
