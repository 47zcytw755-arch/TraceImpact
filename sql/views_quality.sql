-- =============================================================================
-- TraceImpact: Traceable Impact Reporting & Data Quality Platform
-- Day 4: Data Quality Scorecard & Observability Views
-- =============================================================================
-- WHAT:
-- Production analytical views summarizing data quality health across source files,
-- programs, issue types, and blocking status.
--
-- WHY:
-- Enables nonprofit administrators and executives to monitor data hygiene, assess
-- the reliability of impact metrics, triage blocking defects, and track the
-- lifecycle of anomalies from detection to resolution.
--
-- HOW:
-- - Aggregates from `data_quality_issues`, `source_files`, `source_records`, and `programs`.
-- - Employs defensive arithmetic via `NULLIF` to guard against division-by-zero.
-- - Categorizes severity: ERROR (blocking/quarantined), WARNING (usable with caution), INFO (sanitized).
-- - Tracks lifecycle: OPEN, RESOLVED, ACCEPTED.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. OVERALL DATA QUALITY SUMMARY VIEW (v_data_quality_summary)
-- -----------------------------------------------------------------------------
-- Single-row executive scorecard exposing total issues, severity breakdown,
-- resolution rate, and clean record rate.
CREATE OR REPLACE VIEW v_data_quality_summary AS
WITH issue_stats AS (
    SELECT 
        COUNT(*) AS total_issues,
        COUNT(*) FILTER (WHERE severity = 'ERROR') AS error_count,
        COUNT(*) FILTER (WHERE severity = 'WARNING') AS warning_count,
        COUNT(*) FILTER (WHERE severity = 'INFO') AS info_count,
        COUNT(*) FILTER (WHERE status = 'OPEN') AS open_count,
        COUNT(*) FILTER (WHERE status = 'RESOLVED') AS resolved_count,
        COUNT(*) FILTER (WHERE status = 'ACCEPTED') AS accepted_count
    FROM data_quality_issues
),
record_stats AS (
    SELECT COUNT(*) AS total_source_records FROM source_records
)
SELECT 
    i.total_issues,
    i.error_count,
    i.warning_count,
    i.info_count,
    i.open_count,
    i.resolved_count,
    i.accepted_count,
    ROUND((i.error_count::numeric / NULLIF(i.total_issues, 0)) * 100, 2) AS error_percentage,
    ROUND((i.warning_count::numeric / NULLIF(i.total_issues, 0)) * 100, 2) AS warning_percentage,
    ROUND((i.info_count::numeric / NULLIF(i.total_issues, 0)) * 100, 2) AS info_percentage,
    ROUND(((i.resolved_count + i.accepted_count)::numeric / NULLIF(i.total_issues, 0)) * 100, 2) AS resolution_percentage,
    r.total_source_records,
    ROUND(((r.total_source_records - i.error_count)::numeric / NULLIF(r.total_source_records, 0)) * 100, 2) AS clean_record_rate
FROM issue_stats i
CROSS JOIN record_stats r;


-- -----------------------------------------------------------------------------
-- 2. DATA QUALITY BY SOURCE FILE VIEW (v_data_quality_by_file)
-- -----------------------------------------------------------------------------
-- Aggregates issues per source file to identify ingestion points with the
-- highest defect rates.
CREATE OR REPLACE VIEW v_data_quality_by_file AS
SELECT 
    sf.file_id AS source_file_id,
    sf.file_name AS filename,
    COUNT(dqi.issue_id) AS total_issues,
    COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'ERROR') AS error_count,
    COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'WARNING') AS warning_count,
    COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'INFO') AS info_count,
    COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'OPEN') AS open_count,
    COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'RESOLVED') AS resolved_count,
    COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'ACCEPTED') AS accepted_count
FROM source_files sf
LEFT JOIN data_quality_issues dqi ON sf.file_id = dqi.file_id
GROUP BY sf.file_id, sf.file_name
ORDER BY total_issues DESC, sf.file_name ASC;


-- -----------------------------------------------------------------------------
-- 3. DATA QUALITY BY PROGRAM VIEW (v_data_quality_by_program)
-- -----------------------------------------------------------------------------
-- Evaluates data quality concentration across organization programs.
-- Unassigned organization-level issues (e.g. beneficiary registration) are
-- safely captured under the 'UNASSIGNED' category without silent dropping.
CREATE OR REPLACE VIEW v_data_quality_by_program AS
WITH assigned_programs AS (
    SELECT 
        p.program_id,
        p.program_name,
        COUNT(dqi.issue_id) AS total_issues,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'ERROR') AS error_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'WARNING') AS warning_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'INFO') AS info_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'OPEN') AS open_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'RESOLVED') AS resolved_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'ACCEPTED') AS accepted_count
    FROM programs p
    LEFT JOIN data_quality_issues dqi ON p.program_id = dqi.program_id
    GROUP BY p.program_id, p.program_name
),
unassigned_issues AS (
    SELECT 
        'UNASSIGNED' AS program_id,
        'Unassigned / Organization-Level' AS program_name,
        COUNT(dqi.issue_id) AS total_issues,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'ERROR') AS error_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'WARNING') AS warning_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.severity = 'INFO') AS info_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'OPEN') AS open_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'RESOLVED') AS resolved_count,
        COUNT(dqi.issue_id) FILTER (WHERE dqi.status = 'ACCEPTED') AS accepted_count
    FROM data_quality_issues dqi
    WHERE dqi.program_id IS NULL
    HAVING COUNT(dqi.issue_id) > 0
)
SELECT * FROM (
    SELECT * FROM assigned_programs
    UNION ALL
    SELECT * FROM unassigned_issues
) combined_programs
ORDER BY 
    CASE WHEN program_id = 'UNASSIGNED' THEN 1 ELSE 0 END,
    total_issues DESC,
    program_id ASC;


-- -----------------------------------------------------------------------------
-- 4. DATA QUALITY BY ISSUE TYPE VIEW (v_data_quality_by_type)
-- -----------------------------------------------------------------------------
-- Exposes distribution across anomaly categories (DUPLICATE, MISSING_VALUE,
-- INVALID_NUMBER, UNMATCHED_REFERENCE, INCONSISTENT_VALUE, INVALID_FORMAT).
CREATE OR REPLACE VIEW v_data_quality_by_type AS
SELECT 
    issue_type,
    COUNT(*) AS total_issues,
    COUNT(*) FILTER (WHERE severity = 'ERROR') AS error_count,
    COUNT(*) FILTER (WHERE severity = 'WARNING') AS warning_count,
    COUNT(*) FILTER (WHERE severity = 'INFO') AS info_count,
    COUNT(*) FILTER (WHERE status = 'OPEN') AS open_count,
    COUNT(*) FILTER (WHERE status = 'RESOLVED') AS resolved_count,
    COUNT(*) FILTER (WHERE status = 'ACCEPTED') AS accepted_count
FROM data_quality_issues
GROUP BY issue_type
ORDER BY total_issues DESC, issue_type ASC;


-- -----------------------------------------------------------------------------
-- 5. BLOCKING DATA QUALITY ISSUES VIEW (v_data_quality_blocking)
-- -----------------------------------------------------------------------------
-- Exposes active blocking issues (severity = 'ERROR' and status = 'OPEN')
-- that quarantined records from domain tables and require triage.
CREATE OR REPLACE VIEW v_data_quality_blocking AS
SELECT 
    dqi.issue_id,
    sf.file_name AS source_file,
    dqi.record_id AS source_record_id,
    dqi.row_number,
    dqi.column_name,
    dqi.issue_type,
    dqi.severity,
    dqi.description AS issue_message,
    dqi.status,
    dqi.program_id,
    COALESCE(p.program_name, 'Unassigned') AS program_name,
    dqi.raw_value,
    dqi.detected_at AS created_at
FROM data_quality_issues dqi
JOIN source_files sf ON dqi.file_id = sf.file_id
LEFT JOIN programs p ON dqi.program_id = p.program_id
WHERE dqi.severity = 'ERROR' AND dqi.status = 'OPEN'
ORDER BY dqi.issue_id ASC;
