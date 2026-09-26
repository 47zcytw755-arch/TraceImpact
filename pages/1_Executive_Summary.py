"""
Executive Summary Dashboard Page.

WHAT:
Displays organization-wide nonprofit KPIs and executive visualizations:
- High-level metric cards (programs, beneficiaries, attendance, expenses, outcomes, DQ).
- 5 core analytical charts powered directly by Day 3 and Day 4 PostgreSQL views.
"""

import streamlit as st
import pandas as pd
from src.dashboard.components import render_sidebar, render_header, render_db_error
from src.dashboard.db import check_db_health
from src.dashboard.queries import (
    get_executive_kpis,
    get_program_reach_chart_data,
    get_attendance_consistency_chart_data,
    get_cost_per_beneficiary_chart_data,
    get_outcome_improvement_chart_data,
    get_dq_severity_distribution,
)
from src.dashboard.formatting import format_currency, format_number, format_percentage

st.set_page_config(page_title="Executive Summary — TraceImpact", page_icon="📈", layout="wide")

render_sidebar()
render_header(
    title="Executive Summary",
    subtitle="Organization-wide impact performance, contact hours, and data quality overview",
    icon="📈",
)

if not check_db_health():
    render_db_error()
    st.stop()

# -----------------------------------------------------------------------------
# 1. KPI Cards
# -----------------------------------------------------------------------------
kpis = get_executive_kpis()

st.markdown("### 🎯 **Key Impact & Operational Metrics**")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Programs", format_number(kpis.get("total_programs")), help="Active initiatives cataloged in master programs")
with col2:
    st.metric("Total Beneficiaries", format_number(kpis.get("total_beneficiaries")), help="Unique individuals verified and registered")
with col3:
    st.metric("Total Attendance Records", format_number(kpis.get("total_attendance")), help="Individual verified participation check-ins")
with col4:
    st.metric("Total Program Expenses", format_currency(kpis.get("total_expenses")), help="Total verified expenditures across all initiatives")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("Total Outcomes Surveys", format_number(kpis.get("total_outcomes")), help="Verified pre/post evaluation assessments")
with col6:
    st.metric("Data Quality Issues", format_number(kpis.get("total_issues")), help="Total anomalies cataloged by observability engine")
with col7:
    st.metric("Open Triage Issues", format_number(kpis.get("open_issues")), delta="-149 Normalized", delta_color="inverse")
with col8:
    st.metric("Issue Resolution Rate", format_percentage(kpis.get("resolution_rate")), help="Proportion of issues normalized or formally accepted")

st.markdown("---")

# -----------------------------------------------------------------------------
# 2. Executive Visualizations
# -----------------------------------------------------------------------------
st.markdown("### 📊 **Impact Performance Visualizations**")

# Row 1: Program Reach & Attendance Consistency
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("👥 Program Reach (Unique Beneficiaries Served)")
    reach_df = get_program_reach_chart_data()
    if not reach_df.empty:
        chart_data = reach_df.set_index("program_name")[["beneficiaries_served"]]
        st.bar_chart(chart_data)
        st.caption("Source: `v_program_reach` • Shows distinct community members engaged per initiative.")
    else:
        st.info("No reach data available.")

with row1_col2:
    st.subheader("⏱️ Attendance Consistency (Sessions / Beneficiary)")
    att_df = get_attendance_consistency_chart_data()
    if not att_df.empty:
        chart_data = att_df.set_index("program_name")[["sessions_per_beneficiary"]]
        st.bar_chart(chart_data)
        st.caption("Source: `v_attendance_consistency` • Average check-in depth per registered participant.")
    else:
        st.info("No attendance consistency data available.")

st.markdown("---")

# Row 2: Cost-Effectiveness & Outcome Improvement
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("💰 Cost per Beneficiary (₹ / Participant)")
    cost_df = get_cost_per_beneficiary_chart_data()
    if not cost_df.empty:
        chart_data = cost_df.set_index("program_name")[["cost_per_beneficiary"]]
        st.bar_chart(chart_data)
        st.caption("Source: `v_cost_per_beneficiary` • Lower values denote higher capital efficiency per person.")
    else:
        st.info("No cost data available.")

with row2_col2:
    st.subheader("📈 Outcome Improvement (Average Score Gain)")
    out_df = get_outcome_improvement_chart_data()
    if not out_df.empty:
        chart_data = out_df.set_index("program_name")[["avg_score_improvement"]]
        st.bar_chart(chart_data)
        st.caption("Source: `v_outcome_improvement` • Points gained from baseline evaluation to program exit.")
    else:
        st.info("No outcome improvement data available.")

st.markdown("---")

# Row 3: Data Quality Observability Severity Breakdown
st.subheader("🛡️ Data Quality Anomaly Severity Distribution")
dq_sev_df = get_dq_severity_distribution()

if not dq_sev_df.empty:
    sev_col1, sev_col2 = st.columns([1, 2])
    with sev_col1:
        st.dataframe(
            dq_sev_df.rename(columns={"severity": "Severity Level", "count": "Issue Count"}),
            use_container_width=True,
            hide_index=True,
        )
    with sev_col2:
        chart_data = dq_sev_df.set_index("severity")[["count"]]
        st.bar_chart(chart_data)
    st.caption("Source: `data_quality_issues` • ERROR: Quarantined defects (5.6%); WARNING: Usable with caution (6.8%); INFO: Auto-sanitized (87.6%).")
else:
    st.info("No data quality issue records available.")
