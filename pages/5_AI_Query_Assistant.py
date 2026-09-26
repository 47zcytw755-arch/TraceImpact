"""
AI Query Assistant Page — TraceImpact.

WHAT:
Enables natural-language inquiries over PostgreSQL analytical and data quality views.
Translates questions into pre-approved, safe SQL queries, executes them against
the database, and returns data tables, visualizations, and plain-English SQL explanations.

WHY:
Demonstrates modern AI-augmented reporting for executives, grant evaluators, and auditors
while maintaining strict data governance (read-only, zero hallucinated SQL, zero data corruption).
"""

import streamlit as st
import pandas as pd
from src.dashboard.components import render_sidebar, render_header, render_db_error
from src.dashboard.db import check_db_health
from src.dashboard.ai_assistant import AIAssistantEngine

st.set_page_config(page_title="AI Query Assistant — TraceImpact", page_icon="🤖", layout="wide")

render_sidebar()
render_header(
    title="AI Query Assistant",
    subtitle="Ask natural-language impact questions grounded in verified PostgreSQL analytical views",
    icon="🤖",
)

if not check_db_health():
    render_db_error()
    st.stop()

# -----------------------------------------------------------------------------
# 1. Architectural Safety & Governance Callout
# -----------------------------------------------------------------------------
st.info(
    "🛡️ **Enterprise Governance Guarantee:** This AI Assistant maps natural-language queries "
    "strictly to **pre-vetted, read-only analytical views** (`v_program_kpis`, `v_cost_per_beneficiary`, "
    "`v_outcome_improvement`, `v_program_reach`, `v_data_quality_blocking`). "
    "Zero risk of arbitrary SQL injection, zero Cartesian multiplication, and zero hallucinated numbers."
)

# -----------------------------------------------------------------------------
# 2. Query Selector & Interaction Modes
# -----------------------------------------------------------------------------
presets = AIAssistantEngine.get_preset_queries()
preset_titles = [f"[{p['category']}] {p['title']}" for p in presets]

mode = st.radio(
    "Choose inquiry mode:",
    ["💡 Curated Executive Inquiries (Recommended for Quick Demo)", "✍️ Custom Natural-Language Question"],
    horizontal=True,
)

selected_question = None

if "Curated" in mode:
    preset_choice = st.selectbox(
        "Select a curated executive question:",
        preset_titles,
        help="Select a standard donor or audit question to immediately view live data and SQL explanation."
    )
    # Find matching preset
    for p in presets:
        if f"[{p['category']}] {p['title']}" == preset_choice:
            selected_question = p["question"]
            break
else:
    custom_input = st.text_input(
        "Type your question in plain English:",
        placeholder="e.g. Which program is over budget? Or: Show outcome improvement for Coding Bootcamp",
        help="Type any inquiry related to program reach, attendance hours, budgets, outcome scores, or data quality."
    )
    if custom_input:
        selected_question = custom_input
    else:
        st.markdown(
            "> *Try asking: 'Which programs are over budget?', 'Show me attendance hours for all programs', "
            "'What are the top outcome score improvements?', or 'What data quality errors were quarantined?'*"
        )

# -----------------------------------------------------------------------------
# 3. Query Execution & Results Rendering
# -----------------------------------------------------------------------------
if selected_question:
    st.markdown("---")
    st.subheader(f"💬 Inquiry: *\"{selected_question}\"*")

    with st.spinner("Analyzing inquiry and querying PostgreSQL views..."):
        try:
            result = AIAssistantEngine.answer_question(selected_question)
            
            # Answer Summary Card
            st.success(result["answer"])

            # Data Results Table
            st.markdown("#### 📊 **Verified Result Data (Live PostgreSQL View)**")
            df: pd.DataFrame = result["df"]
            if not df.empty:
                st.dataframe(df, use_container_width=True)
                st.caption(f"Showing {len(df)} verified row(s) retrieved from PostgreSQL.")
            else:
                st.warning("No records matched the specified criteria.")

            # Technical Details Accordion: SQL Execution & Explainer
            with st.expander("🔍 **View Executed SQL & Technical Lineage Explanation**", expanded=True):
                col_sql, col_exp = st.columns([1, 1])
                
                with col_sql:
                    st.markdown("**Executed SQL Query (Read-Only):**")
                    st.code(result["sql"], language="sql")
                
                with col_exp:
                    st.markdown("**Plain-English Architectural Explanation:**")
                    st.markdown(result["explanation"])
                    st.markdown(
                        f"- **Domain Category:** `{result.get('category', 'General')}`\n"
                        "- **Data Source:** Verified Analytical View Layer\n"
                        "- **Integrity Guarantee:** CTE Pre-Aggregated, Division-by-Zero Protected (`NULLIF`)"
                    )

        except Exception as e:
            st.error(f"Error processing inquiry: {str(e)}")

# -----------------------------------------------------------------------------
# 4. Architecture Data Flow Diagram
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🏛️ **AI Natural-Language Query Architecture**")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────┐
│ User / Executive Natural Language Question                      │
│ (e.g., "Which programs are over budget?")                       │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Intent Mapping & Parameter Guardrails (src/dashboard/ai_assistant.py) │
│ - Strict keyword validation (No DML / DDL allowed)              │
│ - Safe entity extraction (PRG-001 ... PRG-005)                  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Approved PostgreSQL View Layer (Day 3 & Day 4 Views)            │
│ - v_cost_per_beneficiary, v_outcome_improvement, v_program_kpis │
│ - v_data_quality_blocking, v_program_reach                      │
│ (Pre-aggregated CTEs guarantee zero Cartesian row multiplication)│
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Formatted Streamlit Output (pages/5_AI_Query_Assistant.py)      │
│ 1. Executive Plain-English Answer                               │
│ 2. Live Tabular Data (Pandas DataFrame)                         │
│ 3. Executed SQL Code & Architectural Explanation                │
└─────────────────────────────────────────────────────────────────┘
```
""")
