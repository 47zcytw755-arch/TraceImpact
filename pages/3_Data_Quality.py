"""
Data Quality Scorecard & Observability Page.

WHAT:
Displays the Day 4 Data Quality Scorecard and interactive issue triage log:
- High-level DQ metrics: total issues, severity breakdown, resolution rate, clean record rate.
- Multi-dimensional breakdowns by source file, program, and anomaly category.
- Interactive multi-parameter filters (severity, status, issue type, file, program).
- Detailed issue table displaying exact row coordinates and source_record_id lineage.
"""

import streamlit as st
import pandas as pd
from src.dashboard.components import render_sidebar, render_header, render_db_error, render_empty_state
from src.dashboard.db import check_db_health
from src.dashboard.queries import (
    get_dq_summary,
    get_dq_by_file_df,
    get_dq_by_program_df,
    get_dq_by_type_df,
    get_dq_filtered_issues,
    get_all_programs,
)
from src.dashboard.formatting import format_number, format_percentage

st.set_page_config(page_title="Data Quality — TraceImpact", page_icon="🛡️", layout="wide")

render_sidebar()
render_header(
    title="Data Quality Scorecard & Observability",
    subtitle="Audit log, anomaly quarantine, severity classification, and issue triage",
    icon="🛡️",
)

if not check_db_health():
    render_db_error()
    st.stop()

# -----------------------------------------------------------------------------
# 1. Summary Metrics
# -----------------------------------------------------------------------------
summary = get_dq_summary()

if not summary:
    render_empty_state("Could not load data quality summary metrics.")
    st.stop()

st.markdown("### 📊 **Data Quality Health Scorecard**")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Cataloged Issues", format_number(summary.get("total_issues")), help="Total anomalies recorded across all datasets")
with c2:
    st.metric(
        "Blocking Errors (Quarantined)",
        format_number(summary.get("error_count")),
        help="Violations blocked from domain tables to prevent metric skew",
    )
with c3:
    st.metric("Non-Blocking Warnings", format_number(summary.get("warning_count")), help="Missing or suspicious values loaded with caution")
with c4:
    st.metric("Auto-Sanitized Info", format_number(summary.get("info_count")), help="Syntactic/formatting variations cleaned during ingestion")

c5, c6, c7, c8 = st.columns(4)
with c5:
    st.metric("Open Triage Items", format_number(summary.get("open_count")), help="Issues awaiting manual verification or acceptance")
with c6:
    st.metric("Resolved Issues", format_number(summary.get("resolved_count")), help="Anomalies cleaned and normalized by pipeline")
with c7:
    st.metric("Issue Resolution Rate", format_percentage(summary.get("resolution_percentage")), help="Proportion of issues resolved or accepted")
with c8:
    st.metric("Clean Record Rate", format_percentage(summary.get("clean_record_rate")), help="Source records admitted without blocking errors")

st.markdown("---")

# -----------------------------------------------------------------------------
# 2. Multi-Dimensional Breakdown Tabs
# -----------------------------------------------------------------------------
st.markdown("### 🔍 **Anomaly Distribution Breakdowns**")

tab_file, tab_prog, tab_type = st.tabs([
    "📁 Issues by Source File",
    "🏢 Issues by Program",
    "🏷️ Issues by Anomaly Type",
])

with tab_file:
    file_df = get_dq_by_file_df()
    if not file_df.empty:
        col_t, col_c = st.columns([3, 2])
        with col_t:
            st.dataframe(file_df, use_container_width=True, hide_index=True)
        with col_c:
            st.bar_chart(file_df.set_index("filename")[["total_issues"]])
        st.caption("Source: `v_data_quality_by_file` • Highlights ingestion files with highest anomaly density.")
    else:
        st.info("No file-level issue data available.")

with tab_prog:
    prog_df = get_dq_by_program_df()
    if not prog_df.empty:
        col_t, col_c = st.columns([3, 2])
        with col_t:
            st.dataframe(prog_df, use_container_width=True, hide_index=True)
        with col_c:
            st.bar_chart(prog_df.set_index("program_id")[["total_issues"]])
        st.caption("Source: `v_data_quality_by_program` • UNASSIGNED includes organization-wide registration records.")
    else:
        st.info("No program-level issue data available.")

with tab_type:
    type_df = get_dq_by_type_df()
    if not type_df.empty:
        col_t, col_c = st.columns([3, 2])
        with col_t:
            st.dataframe(type_df, use_container_width=True, hide_index=True)
        with col_c:
            st.bar_chart(type_df.set_index("issue_type")[["total_issues"]])
        st.caption("Source: `v_data_quality_by_type` • Categorizes root-cause data defects.")
    else:
        st.info("No issue-type data available.")

st.markdown("---")

# -----------------------------------------------------------------------------
# 3. Interactive Triage & Filter Table
# -----------------------------------------------------------------------------
st.markdown("### 🛠️ **Interactive Issue Triage Explorer**")
st.caption("Filter and inspect issues. Every issue links directly to `source_record_id` and raw row coordinates.")

f1, f2, f3, f4, f5 = st.columns(5)
with f1:
    filter_sev = st.selectbox("Severity:", ["ALL", "ERROR", "WARNING", "INFO"])
with f2:
    filter_stat = st.selectbox("Status:", ["ALL", "OPEN", "RESOLVED", "ACCEPTED"])
with f3:
    filter_type = st.selectbox("Issue Type:", [
        "ALL", "DUPLICATE", "MISSING_VALUE", "INVALID_NUMBER", 
        "UNMATCHED_REFERENCE", "INCONSISTENT_VALUE", "INVALID_FORMAT"
    ])
with f4:
    filter_file = st.selectbox("Source File:", [
        "ALL", "attendance.csv", "beneficiaries.csv", "expenses.csv", "outcomes.csv", "programs.csv"
    ])
with f5:
    all_progs = get_all_programs()
    prog_opts = ["ALL", "UNASSIGNED"] + [p["program_id"] for p in all_progs]
    filter_prog = st.selectbox("Program:", prog_opts)

# Fetch filtered issues
filtered_df = get_dq_filtered_issues(
    severity=filter_sev,
    status=filter_stat,
    issue_type=filter_type,
    file_name=filter_file,
    program_id=filter_prog,
    limit=300,
)

if not filtered_df.empty:
    st.write(f"Showing **{len(filtered_df)}** matching issue records:")
    st.dataframe(
        filtered_df[[
            "issue_id", "severity", "issue_type", "issue_message", "status",
            "source_file", "row_number", "column_name", "raw_value",
            "program_id", "source_record_id"
        ]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Pro-tip: Note the `source_record_id` and navigate to **4. Traceability** to inspect the verbatim raw CSV row.")
else:
    render_empty_state("No data quality issues match the specified filter combination.")
