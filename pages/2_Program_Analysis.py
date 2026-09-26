"""
Program Analysis Dashboard Page.

WHAT:
Enables deep-dive operational inspection into individual nonprofit initiatives:
- Program metadata and financial allocation.
- Consolidated KPI metrics from `v_program_kpis`.
- Domain table breakdowns (beneficiaries, attendance, expenses, outcomes).
- Program-specific data quality anomalies with lineage coordinates.
"""

import streamlit as st
import pandas as pd
from src.dashboard.components import render_sidebar, render_header, render_db_error, render_empty_state
from src.dashboard.db import check_db_health
from src.dashboard.queries import (
    get_all_programs,
    get_program_kpi_detail,
    get_program_domain_records,
    get_program_issues,
)
from src.dashboard.formatting import (
    format_currency,
    format_number,
    format_percentage,
    get_severity_badge,
    get_status_badge,
)

st.set_page_config(page_title="Program Analysis — TraceImpact", page_icon="🔍", layout="wide")

render_sidebar()
render_header(
    title="Program Analysis",
    subtitle="Operational deep-dive, participant contact hours, unit economics, and domain records",
    icon="🔍",
)

if not check_db_health():
    render_db_error()
    st.stop()

# -----------------------------------------------------------------------------
# 1. Program Selection
# -----------------------------------------------------------------------------
programs = get_all_programs()

if not programs:
    render_empty_state("No programs found in the database.")
    st.stop()

# Build dropdown options
prog_options = {p["program_id"]: f"{p['program_id']} — {p['program_name']}" for p in programs}
selected_prog_id = st.selectbox(
    "Select a Program Initiative to Inspect:",
    options=list(prog_options.keys()),
    format_func=lambda x: prog_options[x],
)

prog_kpi = get_program_kpi_detail(selected_prog_id)

if not prog_kpi:
    render_empty_state(f"Could not load KPI details for program {selected_prog_id}.")
    st.stop()

# -----------------------------------------------------------------------------
# 2. Program Overview & Scorecard KPIs
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(f"### 📋 **{prog_kpi.get('program_name')} ({prog_kpi.get('program_id')})**")
st.caption(f"Target Focus Category: **{prog_kpi.get('target_category', 'General')}**")

# Row 1: Reach & Engagement
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Unique Beneficiaries", format_number(prog_kpi.get("beneficiaries_served")), help="Distinct participants attending this initiative")
with c2:
    st.metric("Total Attendance Logs", format_number(prog_kpi.get("total_attendance_records")), help="Total session check-ins recorded")
with c3:
    st.metric("Total Contact Hours", f"{float(prog_kpi.get('total_session_hours') or 0):,.1f} hrs", help="Cumulative contact hours delivered")
with c4:
    st.metric("Attendance Consistency", f"{float(prog_kpi.get('attendance_per_beneficiary') or 0):.2f} sess/person", help="Average sessions per participant")

# Row 2: Financials & Economics
c5, c6, c7, c8 = st.columns(4)
with c5:
    st.metric("Budget Allocated", format_currency(prog_kpi.get("budget_allocated")))
with c6:
    st.metric("Total Expenses", format_currency(prog_kpi.get("total_expenses")))
with c7:
    util = float(prog_kpi.get("budget_utilization_pct") or 0)
    delta_str = f"{util - 100:.1f}% Over" if util > 100 else f"{100 - util:.1f}% Under"
    st.metric(
        "Budget Utilization",
        format_percentage(util),
        delta=delta_str,
        delta_color="inverse" if util > 100 else "normal",
        help="Expenditures as percentage of allocated budget",
    )
with c8:
    st.metric("Cost per Beneficiary", format_currency(prog_kpi.get("cost_per_beneficiary")), help="Total expenditure divided by unique beneficiaries")

# Row 3: Outcomes & Efficacy
c9, c10, c11, c12 = st.columns(4)
with c9:
    st.metric("Cost per Contact Hour", format_currency(prog_kpi.get("cost_per_beneficiary_hour")), help="Standardized unit cost per participant contact hour")
with c10:
    st.metric("Total Evaluations", format_number(prog_kpi.get("total_evaluations")), help="Number of baseline vs exit evaluation surveys")
with c11:
    st.metric("Avg Baseline Score", f"{float(prog_kpi.get('avg_baseline_score') or 0):.1f} / 100")
with c12:
    st.metric(
        "Avg Score Improvement",
        f"+{float(prog_kpi.get('avg_improvement') or 0):.2f} pts",
        delta=f"+{float(prog_kpi.get('avg_improvement_pct') or 0):.1f}%",
        help="Point gain between entry baseline and program exit",
    )

st.markdown("---")

# -----------------------------------------------------------------------------
# 3. Domain Records Breakdown
# -----------------------------------------------------------------------------
st.markdown("### 🗂️ **Domain Records Exploration**")
st.caption("Inspect verified relational domain records for this initiative. Each row contains its cryptographic `source_record_id`.")

tab_ben, tab_att, tab_exp, tab_outc = st.tabs([
    "👥 Participating Beneficiaries",
    "📅 Attendance Logs",
    "💳 Program Expenses",
    "🎯 Outcome Surveys",
])

with tab_ben:
    ben_df = get_program_domain_records(selected_prog_id, "beneficiaries")
    if not ben_df.empty:
        st.dataframe(ben_df, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(ben_df)} verified participants. Notice `anonymized_code` protects PII.")
    else:
        st.info("No beneficiary records linked to this program.")

with tab_att:
    att_df = get_program_domain_records(selected_prog_id, "attendance")
    if not att_df.empty:
        st.dataframe(att_df, use_container_width=True, hide_index=True)
        st.caption(f"Showing recent attendance sessions. Use `source_record_id` to trace back to raw CSV.")
    else:
        st.info("No attendance records found.")

with tab_exp:
    exp_df = get_program_domain_records(selected_prog_id, "expenses")
    if not exp_df.empty:
        st.dataframe(exp_df, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(exp_df)} expense line items with receipt verification flags.")
    else:
        st.info("No expense records found.")

with tab_outc:
    outc_df = get_program_domain_records(selected_prog_id, "outcomes")
    if not outc_df.empty:
        st.dataframe(outc_df, use_container_width=True, hide_index=True)
        st.caption(f"Showing evaluation surveys measuring participant competency before and after participation.")
    else:
        st.info("No outcome records found.")

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. Program Data Quality Anomaly Log
# -----------------------------------------------------------------------------
st.markdown("### 🛡️ **Program Data Quality Anomaly Log**")
prog_issues = get_program_issues(selected_prog_id)

if prog_issues:
    st.write(f"Detected **{len(prog_issues)}** data quality anomalies for this program:")
    issue_df = pd.DataFrame(prog_issues)
    st.dataframe(
        issue_df[[
            "issue_id", "severity", "issue_type", "column_name", "raw_value",
            "description", "status", "source_file", "source_record_id"
        ]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Tip: Copy any `source_record_id` and open **4. Traceability** to inspect the original raw CSV line.")
else:
    st.success("🎉 No active data quality issues detected for this program!")
