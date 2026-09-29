"""
Public Data Explorer — TraceImpact 2.0.

WHAT:
Interactive exploration and visualization for real-world development indicators
ingested via the World Bank API.

WHY:
Demonstrates TraceImpact as a dual-source enterprise data platform capable of
handling both controlled internal operational datasets and external public REST APIs
with full provenance, lineage, and data quality validation.
"""

import streamlit as st
import pandas as pd
from src.dashboard.components import render_sidebar, render_header, render_db_error, render_empty_state
from src.dashboard.db import check_db_health
from src.dashboard.queries import (
    get_world_bank_kpis,
    get_world_bank_indicators_list,
    get_world_bank_countries_list,
    get_world_bank_trend_data,
    get_world_bank_indicator_summary_df,
    get_world_bank_latest_table,
    get_world_bank_lineage,
    get_api_ingestion_runs_history,
)
from src.dashboard.formatting import format_number

st.set_page_config(page_title="Public Data Explorer — TraceImpact 2.0", page_icon="🌐", layout="wide")

render_sidebar()
render_header(
    title="Public Data Explorer — World Bank Indicators",
    subtitle="Real-world development indicators ingested via World Bank API with bronze-to-silver lineage",
    icon="🌐",
)

if not check_db_health():
    render_db_error()
    st.stop()

# -----------------------------------------------------------------------------
# 1. Domain Banner & KPI Cards
# -----------------------------------------------------------------------------
st.info(
    "💡 **REAL PUBLIC DATA DOMAIN**: This dataset is fetched programmatically from the "
    "[World Bank Indicators API](http://api.worldbank.org/v2) and maintained separately from the synthetic nonprofit operational database."
)

kpis = get_world_bank_kpis()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Countries / Regions", format_number(kpis.get("total_countries", 0)), help="Cataloged sovereign nations and regional aggregates")
with c2:
    st.metric("Total Indicators", format_number(kpis.get("total_indicators", 0)), help="Active macroeconomic and social development metrics")
with c3:
    st.metric("Verified Observations", format_number(kpis.get("total_observations", 0)), help="Validated country-year data points in PostgreSQL")
with c4:
    yr_range = f"{kpis.get('min_year', 'N/A')} – {kpis.get('max_year', 'N/A')}"
    st.metric("Reporting Horizon", yr_range, help="Chronological span of ingested annual observations")

st.markdown("---")

# -----------------------------------------------------------------------------
# 2. Interactive Indicator & Country Explorer
# -----------------------------------------------------------------------------
indicators = get_world_bank_indicators_list()
countries = get_world_bank_countries_list()

if not indicators or not countries:
    render_empty_state("No World Bank indicators or countries found in the database. Run `python -m src.ingestion.world_bank` to ingest data.")
    st.stop()

ind_map = {i["indicator_code"]: f"{i['indicator_name']} ({i['indicator_code']})" for i in indicators}
country_map = {c["country_code"]: f"{c['country_name']} ({c['country_code']})" for c in countries}

col_ind, col_cnt = st.columns([1, 1])
with col_ind:
    selected_ind = st.selectbox(
        "1. Select Global Development Indicator:",
        options=list(ind_map.keys()),
        format_func=lambda x: ind_map[x],
    )

# Default to prominent comparative economies
default_countries = [c for c in ["IN", "US", "CN", "GB", "DE", "BR"] if c in country_map]
with col_cnt:
    selected_countries = st.multiselect(
        "2. Select Countries for Comparative Trend Analysis:",
        options=list(country_map.keys()),
        default=default_countries[:4],
        format_func=lambda x: country_map[x],
    )

# -----------------------------------------------------------------------------
# 3. Visual Multi-Year Trends
# -----------------------------------------------------------------------------
st.subheader("📈 Multi-Year Comparative Trend")

if selected_countries:
    trend_df = get_world_bank_trend_data(selected_ind, selected_countries)
    if not trend_df.empty:
        # Pivot for Streamlit line chart: index=year, columns=country_name, values=indicator_value
        pivot_df = trend_df.pivot(index="year", columns="country_name", values="indicator_value")
        st.line_chart(pivot_df, use_container_width=True)
    else:
        render_empty_state("No observation records found for the selected country and indicator criteria.")
else:
    st.caption("Please select one or more countries to display the trend analysis.")

# -----------------------------------------------------------------------------
# 4. Global Statistics & Latest Country Rankings
# -----------------------------------------------------------------------------
st.markdown("---")
tab_latest, tab_stats = st.tabs(["📊 Latest Reported Rankings", "🌐 Global Indicator Summary"])

with tab_latest:
    st.caption("Derived from SQL analytical view `v_world_bank_latest_indicators`.")
    latest_df = get_world_bank_latest_table(selected_ind, limit=50)
    if not latest_df.empty:
        st.dataframe(latest_df, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No data available.")

with tab_stats:
    st.caption("Derived from SQL analytical view `v_world_bank_indicator_summary`.")
    summary_df = get_world_bank_indicator_summary_df(selected_ind)
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        render_empty_state("No summary data available.")

# -----------------------------------------------------------------------------
# 5. Public API 1-to-1 Lineage Trace
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔗 Public API End-to-End Lineage Drilldown")
st.markdown(
    """
    Trace any real-world indicator observation back through the entire data pipeline:
    ```
    Dashboard Metric ➔ world_bank_observations ➔ api_raw_responses (Bronze JSONB) ➔ SHA-256 Hash ➔ Ingestion Run Metadata
    ```
    """
)

col_t1, col_t2 = st.columns(2)
with col_t1:
    lineage_country = st.selectbox(
        "Select Country to Trace:",
        options=list(country_map.keys()),
        index=list(country_map.keys()).index("IN") if "IN" in country_map else 0,
        format_func=lambda x: country_map[x],
        key="lineage_c_select",
    )
with col_t2:
    lineage_year = st.selectbox("Select Year to Trace:", [2021, 2020, 2019, 2018], index=0)

lineage_record = get_world_bank_lineage(country_code=lineage_country, indicator_code=selected_ind, year=lineage_year)

if lineage_record:
    st.success(f"✅ Verified 1-to-1 API Lineage for `{lineage_record['country_name']}` ({lineage_year})")
    
    # 4-Step Verification Container
    step1, step2 = st.columns(2)
    with step1:
        st.markdown("### 1️⃣ Cleaned Domain Observation (`world_bank_observations`)")
        st.json({
            "observation_id": lineage_record["observation_id"],
            "country_code": lineage_record["country_code"],
            "country_name": lineage_record["country_name"],
            "indicator_code": lineage_record["indicator_code"],
            "indicator_name": lineage_record["indicator_name"],
            "year": lineage_record["year"],
            "indicator_value": float(lineage_record["indicator_value"]) if lineage_record["indicator_value"] is not None else None,
            "unit": lineage_record["unit"],
            "raw_response_id": lineage_record["raw_response_id"],
            "raw_record_index": lineage_record["raw_record_index"],
        })

    with step2:
        st.markdown("### 2️⃣ Verbatim Staged JSON Payload (Bronze Layer)")
        st.caption(f"Retrieved from `api_raw_responses` payload array at index #{lineage_record['raw_record_index']}.")
        st.json(lineage_record["raw_json_record"])

    st.markdown("### 3️⃣ Ingestion Run & Cryptographic Provenance (`api_raw_responses`)")
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.metric("Raw Response ID", str(lineage_record["raw_response_id"]))
        st.metric("API Page Number", f"Page {lineage_record['page_number']}")
    with mc2:
        st.metric("Run ID", f"Run #{lineage_record['run_id']}")
        st.metric("Run Status", str(lineage_record["run_status"]))
    with mc3:
        st.metric("Ingested At", str(lineage_record["ingested_at"])[:19])
        st.metric("Records Per Page", str(lineage_record["per_page"]))

    st.markdown("**Cryptographic SHA-256 Response Fingerprint:**")
    st.code(lineage_record["response_hash"], language="text")
    st.caption("Guarantees that the received API response page has remained 100% byte-for-byte immutable in PostgreSQL.")

else:
    render_empty_state(f"No observation found for {lineage_country} - {selected_ind} in {lineage_year}.")

# -----------------------------------------------------------------------------
# 6. Pipeline Automation & Ingestion Execution History
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("⏱️ Ingestion Pipeline Execution History & Status")
st.caption(
    "Automated background scheduler execution log from PostgreSQL table `api_ingestion_runs`. "
    "Maintains full auditability for run status, duration, pages, records inserted, records updated, and errors."
)

runs_df = get_api_ingestion_runs_history(limit=15)

if not runs_df.empty:
    # Summary cards from latest run
    latest_run = runs_df.iloc[0]
    
    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        st.metric("Latest Run ID", f"Run #{latest_run['run_id']}")
    with rc2:
        status_label = "🟢 COMPLETED" if latest_run["status"] == "COMPLETED" else f"🔴 {latest_run['status']}"
        st.metric("Latest Status", status_label)
    with rc3:
        st.metric("Inserted / Updated", f"{latest_run['records_inserted']:,} / {latest_run.get('records_updated', 0):,}")
    with rc4:
        dur = f"{float(latest_run['duration_seconds']):.2f}s" if pd.notna(latest_run.get('duration_seconds')) else "N/A"
        st.metric("Execution Duration", dur)

    st.dataframe(
        runs_df[[
            "run_id", "source_name", "run_type", "status", "total_pages",
            "total_records", "records_inserted", "records_updated", "records_quarantined",
            "duration_seconds", "started_at", "completed_at", "error_message"
        ]],
        use_container_width=True,
        hide_index=True,
    )
else:
    render_empty_state("No ingestion execution history recorded.")


# -----------------------------------------------------------------------------
# 7. Machine Learning Anomaly Detection Monitor
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🤖 Machine Learning Anomaly Detection Engine")
st.markdown(
    """
    **Isolation Forest (scikit-learn)** evaluates multi-year country indicator trajectories and 
    cross-country peer baselines to identify statistically extreme observations.
    
    > ⚠️ **METHODOLOGICAL NOTE & NON-CAUSALITY NOTICE**:  
    > Anomaly detection isolates observations exhibiting statistical divergence (Z-scores, growth breakouts).  
    > **It DOES NOT identify causal drivers or policy consequences.**
    """
)

from src.dashboard.queries import (
    get_ml_anomaly_models,
    get_world_bank_anomalies,
    get_anomaly_investigation,
    get_ai_insights,
    get_ai_lineage_trace,
)
from src.ai.investigator import WorldBankInvestigator

models_df = get_ml_anomaly_models()
if not models_df.empty:
    m_active = models_df.iloc[0]
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("Active Model", f"{m_active['model_name']} ({m_active['model_version']})")
    with m_col2:
        st.metric("Algorithm", str(m_active["algorithm"]).split(".")[-1])
    with m_col3:
        st.metric("Training Samples", f"{m_active['training_sample_count']:,} obs")
    with m_col4:
        st.metric("Baseline Contamination", f"{float(m_active['contamination_rate']) * 100:.1f}%")

anomalies_df = get_world_bank_anomalies(limit=100)

if not anomalies_df.empty:
    st.write(f"Displaying top **{len(anomalies_df)} statistical anomalies** sorted by decision score (lower score = higher outlier probability):")

    # Filter row
    f1, f2 = st.columns(2)
    with f1:
        filter_ind = st.selectbox(
            "Filter Anomalies by Indicator:",
            options=["ALL"] + list(anomalies_df["indicator_code"].unique()),
            format_func=lambda x: "All Indicators" if x == "ALL" else f"{x} - {anomalies_df[anomalies_df['indicator_code']==x]['indicator_name'].iloc[0]}"
        )
    with f2:
        filter_c = st.text_input("Filter Anomalies by Country Code (e.g. IN, US, BR):", "").strip().upper()

    filtered_anom = anomalies_df.copy()
    if filter_ind != "ALL":
        filtered_anom = filtered_anom[filtered_anom["indicator_code"] == filter_ind]
    if filter_c:
        filtered_anom = filtered_anom[filtered_anom["country_code"] == filter_c]

    st.dataframe(
        filtered_anom[[
            "anomaly_id", "country_name", "region", "indicator_name", "year",
            "indicator_value", "anomaly_score", "has_investigation"
        ]],
        use_container_width=True,
        hide_index=True,
    )
else:
    render_empty_state("No anomalies recorded. Run `python -m src.ml.anomaly_detector` to execute anomaly detection.")


# -----------------------------------------------------------------------------
# 8. AI Data Investigation & Grounded Insights
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("🔬 AI-Assisted Data Investigation")
st.markdown(
    """
    Select an ML-detected anomaly to trigger an **AI Investigation**. The engine gathers quantitative 
    historical baselines, co-occurring development indicators, and trajectory dynamics to synthesize 
    a grounded finding strictly bounded by verifiable data.
    """
)

if not anomalies_df.empty:
    anomaly_options = {
        row["anomaly_id"]: f"Anomaly #{row['anomaly_id']} — {row['country_name']} ({row['year']}): {row['indicator_name']} [Score: {float(row['anomaly_score']):.4f}]"
        for _, row in anomalies_df.iterrows()
    }
    
    selected_anomaly_id = st.selectbox(
        "Select Anomaly for Grounded Investigation:",
        options=list(anomaly_options.keys()),
        format_func=lambda x: anomaly_options[x]
    )

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_inv_btn = st.button("🔍 Investigate Anomaly", type="primary")

    existing_inv = get_anomaly_investigation(selected_anomaly_id)

    if run_inv_btn or existing_inv:
        if run_inv_btn and not existing_inv:
            with st.spinner("Compiling statistical baseline & synthesizing grounded investigation..."):
                investigator = WorldBankInvestigator()
                existing_inv = investigator.investigate_anomaly(selected_anomaly_id)
                st.success("✅ Investigation synthesized and persisted to PostgreSQL `ai_investigations`.")

        if existing_inv:
            st.markdown("#### 📋 Investigation Findings & Evidence")
            
            # Finding Alert
            st.info(f"**FINDING**: {existing_inv['finding_summary']}")

            tab_ev, tab_interp, tab_lineage = st.tabs([
                "📊 Quantitative Evidence & Context", 
                "💡 Potential Interpretations & Boundaries",
                "🔗 Source-to-Insight Traceability"
            ])

            with tab_ev:
                ev_c1, ev_c2 = st.columns(2)
                with ev_c1:
                    st.markdown("**Structured Quantitative Evidence:**")
                    st.json(existing_inv["structured_evidence"])
                with ev_c2:
                    st.markdown("**Co-occurring Indicators (Same Country & Year):**")
                    if existing_inv.get("related_indicators"):
                        st.dataframe(pd.DataFrame(existing_inv["related_indicators"]), hide_index=True)
                    else:
                        st.caption("No additional co-occurring indicators available for this country-year.")

                st.markdown("**Multi-Year Historical Comparison Trajectory:**")
                if existing_inv.get("historical_comparison"):
                    hist_df = pd.DataFrame(existing_inv["historical_comparison"]).sort_values("year")
                    st.line_chart(hist_df.set_index("year"), use_container_width=True)

            with tab_interp:
                st.markdown("**Grounded Synthesis:**")
                st.text(existing_inv["ai_explanation"])

                st.markdown("**Plausible Hypotheses (Explicitly Non-Causal & Interpretative):**")
                st.markdown(existing_inv["possible_interpretation"])

                st.warning(f"**LIMITATIONS & BOUNDARIES**:\n\n{existing_inv['limitations']}")

            with tab_lineage:
                st.markdown("**End-to-End Audit Trail (View `v_world_bank_ai_lineage`):**")
                lineage_data = get_ai_lineage_trace(anomaly_id=selected_anomaly_id)
                if lineage_data:
                    lc1, lc2 = st.columns(2)
                    with lc1:
                        st.markdown("##### 🏛️ Downstream AI & ML Records")
                        st.write(f"- **Investigation ID:** #{existing_inv['investigation_id']}")
                        st.write(f"- **Anomaly ID:** #{existing_inv['anomaly_id']}")
                        st.write(f"- **Isolation Forest Score:** {float(existing_inv['anomaly_score']):.5f}")
                        st.write(f"- **Observation ID:** #{existing_inv['observation_id']}")
                    with lc2:
                        st.markdown("##### 🌐 Upstream Bronze Raw Provenance")
                        st.write(f"- **Ingestion Run ID:** #{lineage_data.get('run_id')}")
                        st.write(f"- **Source Endpoint:** `{lineage_data.get('endpoint_url')}`")
                        st.write(f"- **Raw Response ID:** #{lineage_data.get('response_id')} (Page {lineage_data.get('page_number')})")
                        st.write(f"- **SHA-256 Hash:** `{lineage_data.get('response_hash')}`")
                else:
                    st.caption("Run investigation to link insight lineage.")

# -----------------------------------------------------------------------------
# 9. AI Grounded Insights Feed
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("💡 Automated AI Grounded Insights Feed")
st.caption(
    "Automated insights generated by the AI Investigation engine from statistical outliers. "
    "Every insight is grounded in measurable facts and preserves full database lineage."
)

insights_df = get_ai_insights(limit=15)
if not insights_df.empty:
    st.dataframe(
        insights_df[[
            "insight_id", "country_name", "indicator_name", "year", "insight_type",
            "title", "evidence_text", "created_at"
        ]],
        use_container_width=True,
        hide_index=True,
    )
else:
    render_empty_state("No AI insights generated yet. Click 'Investigate Anomaly' above or run `python -m src.ai.investigator`.")

