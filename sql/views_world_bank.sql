-- =============================================================================
-- TraceImpact 2.0: World Bank Public Indicators Analytical Views (Gold Layer)
-- =============================================================================

-- View 1: Latest Indicator Values per Country
-- Uses PostgreSQL DISTINCT ON to retrieve the most recent reported observation
CREATE OR REPLACE VIEW v_world_bank_latest_indicators AS
SELECT DISTINCT ON (o.country_code, o.indicator_code)
    o.country_code,
    c.country_name,
    c.region,
    c.income_level,
    o.indicator_code,
    i.indicator_name,
    i.topic,
    o.year AS latest_year,
    o.indicator_value AS latest_value,
    o.unit,
    o.raw_response_id
FROM world_bank_observations o
JOIN world_bank_countries c ON o.country_code = c.country_code
JOIN world_bank_indicators i ON o.indicator_code = i.indicator_code
WHERE o.indicator_value IS NOT NULL
ORDER BY o.country_code, o.indicator_code, o.year DESC;

-- View 2: Multi-Year Country Indicator Trends & Deltas
-- Uses LAG window function to compute year-over-year change and % growth
CREATE OR REPLACE VIEW v_world_bank_country_trends AS
WITH ranked_obs AS (
    SELECT
        o.country_code,
        c.country_name,
        c.region,
        c.income_level,
        o.indicator_code,
        i.indicator_name,
        o.year,
        o.indicator_value,
        LAG(o.indicator_value) OVER (
            PARTITION BY o.country_code, o.indicator_code 
            ORDER BY o.year ASC
        ) AS prev_year_value,
        LAG(o.year) OVER (
            PARTITION BY o.country_code, o.indicator_code 
            ORDER BY o.year ASC
        ) AS prev_year
    FROM world_bank_observations o
    JOIN world_bank_countries c ON o.country_code = c.country_code
    JOIN world_bank_indicators i ON o.indicator_code = i.indicator_code
    WHERE o.indicator_value IS NOT NULL
)
SELECT
    country_code,
    country_name,
    region,
    income_level,
    indicator_code,
    indicator_name,
    year,
    indicator_value,
    prev_year,
    prev_year_value,
    ROUND(indicator_value - prev_year_value, 4) AS yoy_change,
    ROUND(
        (indicator_value - prev_year_value) * 100.0 / NULLIF(ABS(prev_year_value), 0),
        2
    ) AS yoy_growth_pct
FROM ranked_obs;

-- View 3: Indicator Global Summary Statistics
-- Aggregates distribution across countries: min, max, avg, standard deviation, country count
CREATE OR REPLACE VIEW v_world_bank_indicator_summary AS
SELECT
    o.indicator_code,
    i.indicator_name,
    i.topic,
    o.year,
    COUNT(DISTINCT o.country_code) AS countries_reporting,
    ROUND(AVG(o.indicator_value), 2) AS avg_value,
    ROUND(MIN(o.indicator_value), 2) AS min_value,
    ROUND(MAX(o.indicator_value), 2) AS max_value,
    ROUND(STDDEV(o.indicator_value), 2) AS stddev_value
FROM world_bank_observations o
JOIN world_bank_indicators i ON o.indicator_code = i.indicator_code
WHERE o.indicator_value IS NOT NULL
GROUP BY o.indicator_code, i.indicator_name, i.topic, o.year;

-- View 4: Regional Indicator Comparison
-- Compares average indicator values across world regions
CREATE OR REPLACE VIEW v_world_bank_regional_comparison AS
SELECT
    COALESCE(c.region, 'Aggregates & Others') AS region,
    o.indicator_code,
    i.indicator_name,
    o.year,
    COUNT(DISTINCT o.country_code) AS countries_count,
    ROUND(AVG(o.indicator_value), 2) AS regional_avg,
    ROUND(MIN(o.indicator_value), 2) AS regional_min,
    ROUND(MAX(o.indicator_value), 2) AS regional_max
FROM world_bank_observations o
JOIN world_bank_countries c ON o.country_code = c.country_code
JOIN world_bank_indicators i ON o.indicator_code = i.indicator_code
WHERE o.indicator_value IS NOT NULL
GROUP BY c.region, o.indicator_code, i.indicator_name, o.year;

-- View 5: Public API Ingestion & Data Quality Scorecard
-- Summarizes data quality issues and clean observation rate for World Bank data
CREATE OR REPLACE VIEW v_world_bank_data_quality_summary AS
WITH run_stats AS (
    SELECT
        COUNT(*) AS total_runs,
        MAX(completed_at) AS last_ingestion_at,
        SUM(records_inserted) AS total_observations_loaded
    FROM api_ingestion_runs
    WHERE status = 'COMPLETED'
),
issue_stats AS (
    SELECT
        COUNT(*) AS total_issues,
        COUNT(*) FILTER (WHERE severity = 'ERROR') AS error_count,
        COUNT(*) FILTER (WHERE severity = 'WARNING') AS warning_count,
        COUNT(*) FILTER (WHERE severity = 'INFO') AS info_count,
        COUNT(*) FILTER (WHERE status = 'QUARANTINED') AS quarantined_count
    FROM world_bank_data_quality_issues
),
total_obs AS (
    SELECT COUNT(*) AS total_obs_count FROM world_bank_observations
)
SELECT
    r.total_runs,
    r.last_ingestion_at,
    o.total_obs_count AS valid_observations_count,
    i.total_issues,
    i.error_count,
    i.warning_count,
    i.info_count,
    i.quarantined_count,
    ROUND(
        o.total_obs_count * 100.0 / NULLIF(o.total_obs_count + i.quarantined_count, 0),
        2
    ) AS observation_clean_rate_pct
FROM run_stats r
CROSS JOIN issue_stats i
CROSS JOIN total_obs o;
