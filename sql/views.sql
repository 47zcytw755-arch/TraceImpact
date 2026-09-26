-- =============================================================================
-- TraceImpact: SQL Analytics & KPI Views Layer (Day 3)
-- =============================================================================
-- Purpose:
-- Transforms normalized domain data (programs, beneficiaries, attendance,
-- expenses, outcomes) into standard nonprofit performance metrics.
--
-- Design Principles:
-- 1. Pre-aggregated Common Table Expressions (CTEs) prevent Cartesian row multiplication.
-- 2. NULLIF prevents division-by-zero errors.
-- 3. LEFT JOIN guarantees programs with partial or zero records remain visible.
-- 4. Exposes consistent data contracts for future Streamlit dashboarding.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. PROGRAM REACH VIEW (v_program_reach)
-- -----------------------------------------------------------------------------
-- Measures the breadth of community engagement per program.
CREATE OR REPLACE VIEW v_program_reach AS
SELECT 
    p.program_id,
    p.program_name,
    p.target_category,
    COUNT(DISTINCT a.beneficiary_id) AS distinct_beneficiaries_served,
    COUNT(a.attendance_id) AS total_attendance_records,
    COALESCE(SUM(a.session_hours), 0.00) AS total_session_hours
FROM programs p
LEFT JOIN attendance a ON p.program_id = a.program_id
GROUP BY p.program_id, p.program_name, p.target_category;

-- -----------------------------------------------------------------------------
-- 2. ATTENDANCE CONSISTENCY VIEW (v_attendance_consistency)
-- -----------------------------------------------------------------------------
-- Evaluates participant engagement depth and session density.
CREATE OR REPLACE VIEW v_attendance_consistency AS
SELECT 
    p.program_id,
    p.program_name,
    COUNT(a.attendance_id) AS total_attendance_records,
    COUNT(DISTINCT a.beneficiary_id) AS unique_beneficiaries,
    COALESCE(SUM(a.session_hours), 0.00) AS total_session_hours,
    ROUND(COALESCE(AVG(a.session_hours), 0.00), 2) AS avg_session_hours,
    ROUND(COUNT(a.attendance_id)::numeric / NULLIF(COUNT(DISTINCT a.beneficiary_id), 0), 2) AS attendance_records_per_beneficiary
FROM programs p
LEFT JOIN attendance a ON p.program_id = a.program_id
GROUP BY p.program_id, p.program_name;

-- -----------------------------------------------------------------------------
-- 3. COST PER BENEFICIARY VIEW (v_cost_per_beneficiary)
-- -----------------------------------------------------------------------------
-- Evaluates program financial efficiency per participant reached.
CREATE OR REPLACE VIEW v_cost_per_beneficiary AS
WITH exp_agg AS (
    SELECT 
        program_id,
        COALESCE(SUM(amount), 0.00) AS total_expenses
    FROM expenses
    GROUP BY program_id
),
ben_agg AS (
    SELECT 
        program_id,
        COUNT(DISTINCT beneficiary_id) AS unique_beneficiaries
    FROM attendance
    GROUP BY program_id
)
SELECT 
    p.program_id,
    p.program_name,
    p.budget_allocated,
    COALESCE(e.total_expenses, 0.00) AS total_expenses,
    COALESCE(b.unique_beneficiaries, 0) AS unique_beneficiaries,
    ROUND((COALESCE(e.total_expenses, 0.00) / NULLIF(p.budget_allocated, 0.00)) * 100, 2) AS budget_utilization_pct,
    ROUND(COALESCE(e.total_expenses, 0.00) / NULLIF(b.unique_beneficiaries, 0), 2) AS cost_per_beneficiary
FROM programs p
LEFT JOIN exp_agg e ON p.program_id = e.program_id
LEFT JOIN ben_agg b ON p.program_id = b.program_id;

-- -----------------------------------------------------------------------------
-- 4. COST PER BENEFICIARY HOUR VIEW (v_cost_per_beneficiary_hour)
-- -----------------------------------------------------------------------------
-- Evaluates financial efficiency normalized by contact hours.
CREATE OR REPLACE VIEW v_cost_per_beneficiary_hour AS
WITH exp_agg AS (
    SELECT 
        program_id,
        COALESCE(SUM(amount), 0.00) AS total_expenses
    FROM expenses
    GROUP BY program_id
),
hours_agg AS (
    SELECT 
        program_id,
        COALESCE(SUM(session_hours), 0.00) AS total_session_hours
    FROM attendance
    GROUP BY program_id
)
SELECT 
    p.program_id,
    p.program_name,
    COALESCE(e.total_expenses, 0.00) AS total_expenses,
    COALESCE(h.total_session_hours, 0.00) AS total_session_hours,
    ROUND(COALESCE(e.total_expenses, 0.00) / NULLIF(h.total_session_hours, 0.00), 2) AS cost_per_beneficiary_hour
FROM programs p
LEFT JOIN exp_agg e ON p.program_id = e.program_id
LEFT JOIN hours_agg h ON p.program_id = h.program_id;

-- -----------------------------------------------------------------------------
-- 5. OUTCOME IMPROVEMENT VIEW (v_outcome_improvement)
-- -----------------------------------------------------------------------------
-- Evaluates participant growth between baseline and exit evaluations.
CREATE OR REPLACE VIEW v_outcome_improvement AS
SELECT 
    p.program_id,
    p.program_name,
    COUNT(o.outcome_id) AS total_evaluations,
    ROUND(COALESCE(AVG(o.baseline_score), 0.00), 2) AS avg_baseline_score,
    ROUND(COALESCE(AVG(o.exit_score), 0.00), 2) AS avg_exit_score,
    ROUND(COALESCE(AVG(o.exit_score - o.baseline_score), 0.00), 2) AS avg_score_improvement,
    ROUND(
        COALESCE(
            AVG((o.exit_score - o.baseline_score) / NULLIF(o.baseline_score, 0.00)) * 100,
            0.00
        ), 2
    ) AS avg_improvement_pct
FROM programs p
LEFT JOIN outcomes o ON p.program_id = o.program_id
GROUP BY p.program_id, p.program_name;

-- -----------------------------------------------------------------------------
-- 6. CONSOLIDATED PROGRAM KPIS VIEW (v_program_kpis)
-- -----------------------------------------------------------------------------
-- Comprehensive executive scorecard joining reach, engagement, costs, and impact.
CREATE OR REPLACE VIEW v_program_kpis AS
WITH att_summary AS (
    SELECT 
        program_id,
        COUNT(attendance_id) AS total_attendance_records,
        COUNT(DISTINCT beneficiary_id) AS beneficiaries_served,
        COALESCE(SUM(session_hours), 0.00) AS total_session_hours,
        ROUND(COALESCE(AVG(session_hours), 0.00), 2) AS avg_session_hours,
        ROUND(COUNT(attendance_id)::numeric / NULLIF(COUNT(DISTINCT beneficiary_id), 0), 2) AS attendance_per_beneficiary
    FROM attendance
    GROUP BY program_id
),
exp_summary AS (
    SELECT 
        program_id,
        COUNT(expense_id) AS total_expense_records,
        COALESCE(SUM(amount), 0.00) AS total_expenses
    FROM expenses
    GROUP BY program_id
),
out_summary AS (
    SELECT 
        program_id,
        COUNT(outcome_id) AS total_evaluations,
        ROUND(COALESCE(AVG(baseline_score), 0.00), 2) AS avg_baseline_score,
        ROUND(COALESCE(AVG(exit_score), 0.00), 2) AS avg_exit_score,
        ROUND(COALESCE(AVG(exit_score - baseline_score), 0.00), 2) AS avg_improvement,
        ROUND(
            COALESCE(
                AVG((exit_score - baseline_score) / NULLIF(baseline_score, 0.00)) * 100,
                0.00
            ), 2
        ) AS avg_improvement_pct
    FROM outcomes
    GROUP BY program_id
)
SELECT 
    p.program_id,
    p.program_name,
    p.target_category,
    p.budget_allocated,
    COALESCE(att.beneficiaries_served, 0) AS beneficiaries_served,
    COALESCE(att.total_attendance_records, 0) AS total_attendance_records,
    COALESCE(att.total_session_hours, 0.00) AS total_session_hours,
    COALESCE(att.avg_session_hours, 0.00) AS avg_session_hours,
    COALESCE(att.attendance_per_beneficiary, 0.00) AS attendance_per_beneficiary,
    COALESCE(exp.total_expenses, 0.00) AS total_expenses,
    ROUND((COALESCE(exp.total_expenses, 0.00) / NULLIF(p.budget_allocated, 0.00)) * 100, 2) AS budget_utilization_pct,
    ROUND(COALESCE(exp.total_expenses, 0.00) / NULLIF(att.beneficiaries_served, 0), 2) AS cost_per_beneficiary,
    ROUND(COALESCE(exp.total_expenses, 0.00) / NULLIF(att.total_session_hours, 0.00), 2) AS cost_per_beneficiary_hour,
    COALESCE(outc.total_evaluations, 0) AS total_evaluations,
    outc.avg_baseline_score,
    outc.avg_exit_score,
    outc.avg_improvement,
    outc.avg_improvement_pct
FROM programs p
LEFT JOIN att_summary att ON p.program_id = att.program_id
LEFT JOIN exp_summary exp ON p.program_id = exp.program_id
LEFT JOIN out_summary outc ON p.program_id = outc.program_id;
