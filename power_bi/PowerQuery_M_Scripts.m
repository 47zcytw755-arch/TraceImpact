// ============================================================================
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
