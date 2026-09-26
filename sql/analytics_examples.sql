-- =============================================================================
-- TraceImpact: Analytical & Traceability Example Queries (Day 3)
-- =============================================================================
-- These queries demonstrate how the SQL analytics layer answers key nonprofit
-- operational, financial, and impact questions while preserving source lineage.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Which programs served the most unique beneficiaries? (Program Reach)
-- -----------------------------------------------------------------------------
SELECT 
    program_id,
    program_name,
    target_category,
    distinct_beneficiaries_served,
    total_attendance_records,
    total_session_hours
FROM v_program_reach
ORDER BY distinct_beneficiaries_served DESC, total_attendance_records DESC;

-- -----------------------------------------------------------------------------
-- 2. Which programs had the highest expenditure and budget utilization?
-- -----------------------------------------------------------------------------
SELECT 
    program_id,
    program_name,
    budget_allocated,
    total_expenses,
    budget_utilization_pct,
    CASE 
        WHEN budget_utilization_pct > 100 THEN 'OVER BUDGET'
        WHEN budget_utilization_pct >= 85 THEN 'ON TRACK'
        ELSE 'UNDER UTILIZED'
    END AS budget_status
FROM v_cost_per_beneficiary
ORDER BY total_expenses DESC;

-- -----------------------------------------------------------------------------
-- 3. Program Financial Efficiency: Cost per Beneficiary & Cost per Hour
-- -----------------------------------------------------------------------------
SELECT 
    k.program_id,
    k.program_name,
    k.beneficiaries_served,
    k.total_session_hours,
    k.total_expenses,
    k.cost_per_beneficiary,
    k.cost_per_beneficiary_hour
FROM v_program_kpis k
ORDER BY k.cost_per_beneficiary ASC;

-- -----------------------------------------------------------------------------
-- 4. Program Impact Efficacy: Average Outcome Improvement
-- -----------------------------------------------------------------------------
SELECT 
    program_id,
    program_name,
    total_evaluations,
    avg_baseline_score,
    avg_exit_score,
    avg_improvement,
    avg_improvement_pct
FROM v_outcome_improvement
ORDER BY avg_improvement DESC;

-- -----------------------------------------------------------------------------
-- 5. Comprehensive 360-Degree Program Scorecard
-- -----------------------------------------------------------------------------
SELECT *
FROM v_program_kpis
WHERE program_id = 'PRG-001';

-- -----------------------------------------------------------------------------
-- 6. LINEAGE DRILLDOWN: From a Program Expense Total Back to Raw CSV Rows
-- -----------------------------------------------------------------------------
-- Demonstrates TraceImpact's core value proposition:
-- Aggregate Metric -> Domain Record -> source_record_id -> raw_data JSONB -> CSV
SELECT 
    e.expense_id,
    e.program_id,
    p.program_name,
    e.expense_category,
    e.amount,
    e.incurred_date,
    e.receipt_verified,
    e.source_record_id,
    sr.file_id,
    sf.file_name AS source_file,
    sr.row_index AS raw_csv_row_number,
    sr.raw_data AS raw_staged_payload
FROM expenses e
JOIN programs p ON e.program_id = p.program_id
JOIN source_records sr ON e.source_record_id = sr.record_id
JOIN source_files sf ON sr.file_id = sf.file_id
WHERE e.program_id = 'PRG-001'
ORDER BY e.incurred_date ASC;

-- -----------------------------------------------------------------------------
-- 7. LINEAGE DRILLDOWN: From Program Attendance Back to Raw CSV Check-ins
-- -----------------------------------------------------------------------------
SELECT 
    a.attendance_id,
    a.program_id,
    p.program_name,
    a.beneficiary_id,
    b.anonymized_code,
    b.city_location,
    a.session_date,
    a.attendance_status,
    a.session_hours,
    a.source_record_id,
    sf.file_name AS source_file,
    sr.row_index AS raw_csv_row_number,
    sr.raw_data AS raw_staged_payload
FROM attendance a
JOIN programs p ON a.program_id = p.program_id
JOIN beneficiaries b ON a.beneficiary_id = b.beneficiary_id
JOIN source_records sr ON a.source_record_id = sr.record_id
JOIN source_files sf ON sr.file_id = sf.file_id
WHERE a.program_id = 'PRG-001'
LIMIT 5;
