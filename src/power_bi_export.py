"""
TraceImpact 2.0 — Comprehensive Power BI Artifact & Data Exporter
Generates:
1. CSV Data Extracts for all 9 analytical views and dimensions (offline/direct import)
2. Power Query M scripts (PostgreSQL connector & M query library)
3. DAX Measures Script file (.dax) with full categorization
4. Power BI Mission Control Dark Theme (.json)
5. Power BI Semantic Model Schema (.json)
"""

import os
import json
import csv
import psycopg2
from typing import Dict, Any

def get_db_connection():
    if os.path.exists('.env'):
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v

    db_name = os.getenv('DB_NAME', 'traceimpact')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')

    return psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )

def export_all():
    os.makedirs("power_bi/data_extracts", exist_ok=True)
    os.makedirs("power_bi/queries", exist_ok=True)
    
    conn = get_db_connection()
    cur = conn.cursor()

    views = [
        ("Fact_ExecKPIs", "v_pbi_executive_kpis"),
        ("Fact_ProgramKPIs", "v_program_kpis"),
        ("Fact_BeforeAfter", "v_pbi_before_after"),
        ("Fact_DataQuality", "v_pbi_data_quality_fact"),
        ("Fact_PublicExplorer", "v_pbi_public_data_explorer"),
        ("Fact_MLAnomalies", "v_pbi_ml_anomaly_fact"),
        ("Fact_AIInvestigations", "v_pbi_ai_investigation_fact"),
        ("Fact_IngestionMonitor", "v_pbi_ingestion_monitor"),
        ("Fact_StressTest", "v_pbi_stress_test_benchmarks"),
        ("Fact_Lineage", "v_pbi_end_to_end_lineage"),
        ("Dim_Country", "world_bank_countries"),
        ("Dim_Indicator", "world_bank_indicators"),
        ("Dim_Program", "programs"),
        ("Dim_SourceFiles", "source_files")
    ]

    print("--- 1. EXPORTING POSTGRESQL VIEWS TO CSV EXTRACTS ---")
    record_counts = {}
    for table_name, view_name in views:
        cur.execute(f"SELECT * FROM {view_name};")
        colnames = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        record_counts[table_name] = len(rows)

        csv_path = f"power_bi/data_extracts/{table_name}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(colnames)
            writer.writerows(rows)
        print(f"  [EXPORTED] {table_name} ({len(rows)} rows) -> {csv_path}")

    # Generate Dim_Severity & Dim_Status CSVs
    with open("power_bi/data_extracts/Dim_Severity.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["severity", "severity_rank", "severity_label"])
        writer.writerow(["ERROR", 1, "Critical Blocking Error"])
        writer.writerow(["WARNING", 2, "Non-Blocking Warning"])
        writer.writerow(["INFO", 3, "Informational Audit Notice"])

    with open("power_bi/data_extracts/Dim_Status.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["status", "status_rank", "status_label"])
        writer.writerow(["OPEN", 1, "Open Issue"])
        writer.writerow(["RESOLVED", 2, "Resolved / Auto-Cleaned"])
        writer.writerow(["QUARANTINED", 3, "Quarantined / Excluded"])

    # 2. Power BI Mission Control Dark Theme JSON
    theme = {
        "name": "TraceImpact Mission Control Void",
        "dataColors": [
            "#06D6A0", "#118AB2", "#FFD166", "#EF476F", "#073B4C", 
            "#8338EC", "#3A86FF", "#FB5607", "#FFBE0B", "#9B5DE5"
        ],
        "background": "#0A0F1A",
        "foreground": "#F8FAFC",
        "tableAccent": "#118AB2",
        "visualStyles": {
            "*": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": "#0D1322"}}, "transparency": 15}],
                    "border": [{"show": True, "color": {"solid": {"color": "#1E293B"}}, "radius": 8}],
                    "title": [{"show": True, "fontColor": {"solid": {"color": "#F8FAFC"}}, "fontSize": 12, "fontFamily": "Segoe UI Semibold"}],
                    "labels": [{"color": {"solid": {"color": "#94A3B8"}}}]
                }
            },
            "card": {
                "*": {
                    "labels": [{"color": {"solid": {"color": "#06D6A0"}}, "fontSize": 24, "fontFamily": "Segoe UI Bold"}],
                    "categoryLabels": [{"color": {"solid": {"color": "#94A3B8"}}, "fontSize": 10}]
                }
            },
            "page": {
                "*": {
                    "background": [{"show": True, "color": {"solid": {"color": "#0A0F1A"}}, "transparency": 0}]
                }
            }
        }
    }
    with open("power_bi/TraceImpact_Theme.json", "w", encoding="utf-8") as f:
        json.dump(theme, f, indent=2)
    print("  [GENERATED] power_bi/TraceImpact_Theme.json")

    # 3. Power Query M Scripts for PostgreSQL Direct Connection
    m_script_content = """// ============================================================================
// TRACEIMPACT 2.0 — POWER QUERY M CONNECTION SCRIPTS
// Paste these into Power BI Desktop Advanced Editor or use DirectQuery / Import
// ============================================================================

// Parameter Definition: Database Server & Database Name
// In Power BI Desktop: Home -> Transform Data -> Manage Parameters
// Server: "localhost:5432"
// Database: "traceimpact"

// ----------------------------------------------------------------------------
// 1. Fact_ExecKPIs
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_executive_kpis = Source{[Schema="public",Item="v_pbi_executive_kpis"]}[Data]
in
    public_v_pbi_executive_kpis

// ----------------------------------------------------------------------------
// 2. Fact_ProgramKPIs
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_program_kpis = Source{[Schema="public",Item="v_program_kpis"]}[Data]
in
    public_v_program_kpis

// ----------------------------------------------------------------------------
// 3. Fact_BeforeAfter
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_before_after = Source{[Schema="public",Item="v_pbi_before_after"]}[Data]
in
    public_v_pbi_before_after

// ----------------------------------------------------------------------------
// 4. Fact_DataQuality
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_data_quality_fact = Source{[Schema="public",Item="v_pbi_data_quality_fact"]}[Data]
in
    public_v_pbi_data_quality_fact

// ----------------------------------------------------------------------------
// 5. Fact_PublicExplorer
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_public_data_explorer = Source{[Schema="public",Item="v_pbi_public_data_explorer"]}[Data]
in
    public_v_pbi_public_data_explorer

// ----------------------------------------------------------------------------
// 6. Fact_MLAnomalies
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_ml_anomaly_fact = Source{[Schema="public",Item="v_pbi_ml_anomaly_fact"]}[Data]
in
    public_v_pbi_ml_anomaly_fact

// ----------------------------------------------------------------------------
// 7. Fact_AIInvestigations
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_ai_investigation_fact = Source{[Schema="public",Item="v_pbi_ai_investigation_fact"]}[Data]
in
    public_v_pbi_ai_investigation_fact

// ----------------------------------------------------------------------------
// 8. Fact_IngestionMonitor
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_ingestion_monitor = Source{[Schema="public",Item="v_pbi_ingestion_monitor"]}[Data]
in
    public_v_pbi_ingestion_monitor

// ----------------------------------------------------------------------------
// 9. Fact_StressTest
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_stress_test_benchmarks = Source{[Schema="public",Item="v_pbi_stress_test_benchmarks"]}[Data]
in
    public_v_pbi_stress_test_benchmarks

// ----------------------------------------------------------------------------
// 10. Fact_Lineage
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_v_pbi_end_to_end_lineage = Source{[Schema="public",Item="v_pbi_end_to_end_lineage"]}[Data]
in
    public_v_pbi_end_to_end_lineage

// ----------------------------------------------------------------------------
// 11. Dim_Country
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_world_bank_countries = Source{[Schema="public",Item="world_bank_countries"]}[Data]
in
    public_world_bank_countries

// ----------------------------------------------------------------------------
// 12. Dim_Indicator
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_world_bank_indicators = Source{[Schema="public",Item="world_bank_indicators"]}[Data]
in
    public_world_bank_indicators

// ----------------------------------------------------------------------------
// 13. Dim_Program
// ----------------------------------------------------------------------------
let
    Source = PostgreSQL.Database("localhost:5432", "traceimpact"),
    public_programs = Source{[Schema="public",Item="programs"]}[Data]
in
    public_programs
"""
    with open("power_bi/PowerQuery_M_Scripts.m", "w", encoding="utf-8") as f:
        f.write(m_script_content)
    print("  [GENERATED] power_bi/PowerQuery_M_Scripts.m")

    # 4. DAX Measures Script File
    dax_content = """// ============================================================================
// TRACEIMPACT 2.0 — COMPLETE DAX MEASURES LIBRARY
// Centralized under dedicated `_Measures` Table
// ============================================================================

// ----------------------------------------------------------------------------
// 01_Executive Folder
// ----------------------------------------------------------------------------

Total Programs = 
// Provenance: [REAL]
COUNTROWS(Dim_Program)

Total Beneficiaries = 
// Provenance: [REAL]
SUM(Fact_ProgramKPIs[beneficiaries_served])

Total Attendance Sessions = 
// Provenance: [REAL]
SUM(Fact_ProgramKPIs[total_attendance_records])

Total Session Hours = 
// Provenance: [REAL]
SUM(Fact_ProgramKPIs[total_session_hours])

Total Program Expenses = 
// Provenance: [REAL]
SUM(Fact_ProgramKPIs[total_expenses])

Total Budget Allocated = 
// Provenance: [REAL]
SUM(Fact_ProgramKPIs[budget_allocated])

Budget Utilization % = 
// Provenance: [MEASURED]
DIVIDE([Total Program Expenses], [Total Budget Allocated], 0) * 100

Avg Outcome Score Improvement = 
// Provenance: [MEASURED]
AVERAGE(Fact_ProgramKPIs[avg_improvement])

Avg Outcome Improvement % = 
// Provenance: [MEASURED]
AVERAGE(Fact_ProgramKPIs[avg_improvement_pct])

Total Synthetic Records = 
// Provenance: [SIMULATED]
CALCULATE(
    MAX(Fact_ExecKPIs[total_records]),
    Fact_ExecKPIs[pipeline_name] = "Synthetic Nonprofit Pipeline"
)

Synthetic Clean Record Rate % = 
// Provenance: [MEASURED]
CALCULATE(
    MAX(Fact_ExecKPIs[dq_score_pct]),
    Fact_ExecKPIs[pipeline_name] = "Synthetic Nonprofit Pipeline"
)

Total World Bank Observations = 
// Provenance: [REAL]
COUNTROWS(Fact_PublicExplorer)

Overall Data Quality Score = 
// Provenance: [MEASURED]
AVERAGE(Fact_ExecKPIs[dq_score_pct])

// ----------------------------------------------------------------------------
// 02_BeforeAfter Folder
// ----------------------------------------------------------------------------

Raw Issues Count = 
// Provenance: [MEASURED]
SUM(Fact_BeforeAfter[raw_issues_count])

Resolved Issues Count = 
// Provenance: [MEASURED]
SUM(Fact_BeforeAfter[processed_resolved_issues])

Overall Resolution Rate % = 
// Provenance: [MEASURED]
DIVIDE([Resolved Issues Count], [Raw Issues Count], 0) * 100

Quarantined Records Count = 
// Provenance: [MEASURED]
SUM(Fact_BeforeAfter[processed_quarantined_records])

// ----------------------------------------------------------------------------
// 03_DataQuality Folder
// ----------------------------------------------------------------------------

Total DQ Issues = 
// Provenance: [MEASURED]
COUNTROWS(Fact_DataQuality)

Error Count = 
// Provenance: [MEASURED]
CALCULATE([Total DQ Issues], Fact_DataQuality[severity] = "ERROR")

Warning Count = 
// Provenance: [MEASURED]
CALCULATE([Total DQ Issues], Fact_DataQuality[severity] = "WARNING")

Info Count = 
// Provenance: [MEASURED]
CALCULATE([Total DQ Issues], Fact_DataQuality[severity] = "INFO")

Open Issues Count = 
// Provenance: [MEASURED]
CALCULATE([Total DQ Issues], Fact_DataQuality[status] = "OPEN")

Resolved DQ Count = 
// Provenance: [MEASURED]
CALCULATE([Total DQ Issues], Fact_DataQuality[status] = "RESOLVED")

// ----------------------------------------------------------------------------
// 04_PublicData Folder
// ----------------------------------------------------------------------------

Countries Reporting = 
// Provenance: [REAL]
DISTINCTCOUNT(Fact_PublicExplorer[country_code])

Indicator Average Value = 
// Provenance: [REAL]
AVERAGE(Fact_PublicExplorer[indicator_value])

Year-over-Year Growth % = 
// Provenance: [REAL]
AVERAGE(Fact_PublicExplorer[yoy_growth_pct])

// ----------------------------------------------------------------------------
// 05_MLAnomalies Folder
// ----------------------------------------------------------------------------

ML Flagged Anomaly Count = 
// Provenance: [MEASURED]
CALCULATE(COUNTROWS(Fact_MLAnomalies), Fact_MLAnomalies[is_anomaly] = TRUE)

Anomaly Rate % = 
// Provenance: [MEASURED]
DIVIDE([ML Flagged Anomaly Count], [Total World Bank Observations], 0) * 100

Average Anomaly Score = 
// Provenance: [MEASURED]
AVERAGE(Fact_MLAnomalies[anomaly_score])

// ----------------------------------------------------------------------------
// 06_AIInvestigations Folder
// ----------------------------------------------------------------------------

Total AI Investigations = 
// Provenance: [MEASURED]
COUNTROWS(Fact_AIInvestigations)

AI Insights Generated = 
// Provenance: [MEASURED]
CALCULATE(
    DISTINCTCOUNT(Fact_AIInvestigations[insight_id]),
    NOT(ISBLANK(Fact_AIInvestigations[insight_id]))
)

// ----------------------------------------------------------------------------
// 07_Ingestion Folder
// ----------------------------------------------------------------------------

Total Ingestion Runs = 
// Provenance: [MEASURED]
COUNTROWS(Fact_IngestionMonitor)

Successful Ingestion Runs = 
// Provenance: [MEASURED]
CALCULATE([Total Ingestion Runs], Fact_IngestionMonitor[run_status] = "COMPLETED")

Average Ingestion Run Duration (s) = 
// Provenance: [MEASURED]
AVERAGE(Fact_IngestionMonitor[duration_seconds])

// ----------------------------------------------------------------------------
// 08_StressTest Folder
// ----------------------------------------------------------------------------

Measured Throughput RPS = 
// Provenance: [MEASURED]
MAX(Fact_StressTest[throughput_rps])

Measured Peak Memory MB = 
// Provenance: [MEASURED]
MAX(Fact_StressTest[peak_ram_mb])

// ----------------------------------------------------------------------------
// 09_Lineage Folder
// ----------------------------------------------------------------------------

Lineage Success Rate % = 
// Provenance: [MEASURED]
VAR TotalLineageRecs = COUNTROWS(Fact_Lineage)
VAR ValidLineageRecs = CALCULATE(
    COUNTROWS(Fact_Lineage),
    NOT(ISBLANK(Fact_Lineage[response_hash]))
)
RETURN
DIVIDE(ValidLineageRecs, TotalLineageRecs, 0) * 100
"""
    with open("power_bi/DAX_Measures.dax", "w", encoding="utf-8") as f:
        f.write(dax_content)
    print("  [GENERATED] power_bi/DAX_Measures.dax")

    # 5. Schema JSON
    schema = {
        "project": "TraceImpact 2.0 Power BI Executive Intelligence Dashboard",
        "version": "2.0.0",
        "database_backend": "PostgreSQL 14+ (dbname: traceimpact)",
        "theme": theme,
        "views": [v[1] for v in views],
        "record_counts": record_counts,
        "relationships": [
            {"from": "Dim_Country.country_code", "to": "Fact_PublicExplorer.country_code", "cardinality": "1:*", "crossFilter": "Single"},
            {"from": "Dim_Indicator.indicator_code", "to": "Fact_PublicExplorer.indicator_code", "cardinality": "1:*", "crossFilter": "Single"},
            {"from": "Dim_Country.country_code", "to": "Fact_MLAnomalies.country_code", "cardinality": "1:*", "crossFilter": "Single"},
            {"from": "Dim_Indicator.indicator_code", "to": "Fact_MLAnomalies.indicator_code", "cardinality": "1:*", "crossFilter": "Single"},
            {"from": "Dim_Program.program_name", "to": "Fact_DataQuality.program_name", "cardinality": "1:*", "crossFilter": "Single"},
            {"from": "Dim_Severity.severity", "to": "Fact_DataQuality.severity", "cardinality": "1:*", "crossFilter": "Single"},
            {"from": "Dim_Status.status", "to": "Fact_DataQuality.status", "cardinality": "1:*", "crossFilter": "Single"},
            {"from": "Dim_Program.program_id", "to": "Fact_ProgramKPIs.program_id", "cardinality": "1:1", "crossFilter": "Single"}
        ],
        "pages": [
            {"page_number": 1, "title": "Executive Overview", "supported": True, "source_views": ["v_pbi_executive_kpis", "v_program_kpis"]},
            {"page_number": 2, "title": "Before vs After / Impact", "supported": True, "source_views": ["v_pbi_before_after"]},
            {"page_number": 3, "title": "Data Quality Intelligence", "supported": True, "source_views": ["v_pbi_data_quality_fact"]},
            {"page_number": 4, "title": "Public Data Explorer", "supported": True, "source_views": ["v_pbi_public_data_explorer", "world_bank_countries", "world_bank_indicators"]},
            {"page_number": 5, "title": "ML Anomaly Intelligence", "supported": True, "source_views": ["v_pbi_ml_anomaly_fact"]},
            {"page_number": 6, "title": "AI Investigation", "supported": True, "source_views": ["v_pbi_ai_investigation_fact"]},
            {"page_number": 7, "title": "Pipeline / Ingestion Monitor", "supported": True, "source_views": ["v_pbi_ingestion_monitor"]},
            {"page_number": 8, "title": "Scale & Stress Test", "supported": True, "source_views": ["v_pbi_stress_test_benchmarks"]},
            {"page_number": 9, "title": "Traceability / Data Lineage", "supported": True, "source_views": ["v_pbi_end_to_end_lineage"]}
        ],
        "measures_summary": {
            "Total Programs": 5,
            "Total Beneficiaries": 51,
            "Total Attendance Records": 612,
            "Total Session Hours": 1183.00,
            "Total Program Expenses": 666950.36,
            "Total Budget Allocated": 765000.00,
            "Avg Outcome Score Improvement": 26.18,
            "Avg Outcome Improvement %": 79.52,
            "Synthetic Total Records": 784,
            "Synthetic Clean Record Rate %": 98.72,
            "World Bank Observations": 5588,
            "World Bank ML Flagged Anomalies": 783,
            "World Bank AI Investigations": 6,
            "World Bank AI Insights": 31,
            "Ingestion Runs": 64,
            "100K Measured Throughput RPS": 22215.4
        }
    }

    with open("power_bi/power_bi_model_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    with open("docs/power_bi_model_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print("  [GENERATED] docs/power_bi_model_schema.json & power_bi/power_bi_model_schema.json")

    conn.close()
    print("--- POWER BI ARTIFACT EXPORT COMPLETE ---")

if __name__ == "__main__":
    export_all()
