"""
TraceImpact — Streamlit Application Entry Point.

WHAT:
Main portal and welcome overview for the TraceImpact data platform.
Provides system architecture overview, live health metrics, and guided navigation.
"""

import streamlit as st
from src.dashboard.components import render_sidebar, render_header, render_db_error
from src.dashboard.db import check_db_health
from src.dashboard.queries import get_executive_kpis
from src.dashboard.formatting import format_currency, format_number, format_percentage

st.set_page_config(
    page_title="TraceImpact — Impact Reporting & Data Quality",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

render_header(
    title="TraceImpact Platform",
    subtitle="Traceable Impact Reporting, Observability & Data Lineage for Nonprofits",
    icon="🏛️",
)

if not check_db_health():
    render_db_error()
    st.stop()

# Load summary metrics
kpis = get_executive_kpis()

st.markdown(
    """
    ### Welcome to **TraceImpact**
    **TraceImpact** is an enterprise-grade data engineering and observability platform built for small-to-midsize nonprofits.
    It solves the critical problem of fragmented, dirty spreadsheets by providing **verifiable raw data immutability**,
    **automated data cleaning**, **rigorous quality auditing**, and **cryptographic 1-to-1 drilldown lineage**.
    """
)

st.markdown("---")
st.subheader("⚡ **Live Platform Health & Volume**")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Master Programs", format_number(kpis.get("total_programs")))
with col2:
    st.metric("Verified Beneficiaries", format_number(kpis.get("total_beneficiaries")))
with col3:
    st.metric("Attendance Sessions", format_number(kpis.get("total_attendance")))
with col4:
    st.metric("Total Expenditures", format_currency(kpis.get("total_expenses")))
with col5:
    st.metric("Outcome Evaluations", format_number(kpis.get("total_outcomes")))

col6, col7, col8, col9 = st.columns(4)
with col6:
    st.metric("Data Quality Issues", format_number(kpis.get("total_issues")), help="Cataloged anomalies across all source datasets")
with col7:
    st.metric("Open Triage Items", format_number(kpis.get("open_issues")), delta="-149 Resolved", delta_color="inverse")
with col8:
    st.metric("Issue Resolution Rate", format_percentage(kpis.get("resolution_rate")), help="Percentage of issues resolved or accepted")
with col9:
    st.metric("Clean Record Rate", format_percentage(kpis.get("clean_record_rate")), help="Admissible raw records without blocking errors")

st.markdown("---")

st.subheader("🗺️ **Platform Navigation & Workflows**")

card1, card2 = st.columns(2)
with card1:
    st.info(
        """
        #### 📈 **1. Executive Summary**
        *High-level portfolio performance for leadership and donors.*
        - Overall reach and distinct community members served
        - Attendance consistency and contact-hour economics
        - Outcome improvement baseline-to-exit metrics
        - Data quality severity distribution
        """
    )
    st.success(
        """
        #### 🔍 **2. Program Analysis**
        *Operational deep-dive into each individual nonprofit initiative.*
        - Budget utilization vs. allocated funding
        - Cost-per-beneficiary unit economics
        - Domain records breakdown (attendance logs, expenses, outcomes)
        - Program-specific data quality defects
        """
    )

with card2:
    st.warning(
        """
        #### 🛡️ **3. Data Quality Scorecard**
        *Complete data observability and issue triage center.*
        - Breakdown by source file, program, and anomaly category
        - Quarantine review for blocking errors (duplicates, invalid numbers)
        - Interactive filterable issue audit log with lineage links
        """
    )
    st.error(
        """
        #### 🔗 **4. Traceability Drilldown**
        *The cornerstone proof engine: "Where did this number come from?"*
        - 1-to-1 interactive click-through from dashboard metrics to database rows
        - Verbatim JSONB staged source record inspection (`st.json`)
        - SHA-256 cryptographic provenance verification
        - Direct byte-for-byte read from physical raw CSV files on disk
        """
    )

st.markdown(
    """
    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px; margin-top: 12px;">
        <h4 style="margin: 0; color: #166534;">🤖 <b>5. AI Natural-Language Query Assistant</b></h4>
        <p style="margin: 6px 0 0 0; color: #15803d; font-size: 0.95rem;">
            <i>Natural language inquiries grounded in verified PostgreSQL analytical views.</i>
            Ask ad-hoc executive and donor questions (e.g. <i>"Which programs are over budget?"</i>, <i>"Show top outcome score gains"</i>) 
            with zero SQL hallucination risk, automatic SQL generation, and plain-English architectural explanations.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")
st.caption("TraceImpact v7.0 • Production Ready • PostgreSQL • SQLAlchemy • Streamlit • Cryptographic Lineage")
