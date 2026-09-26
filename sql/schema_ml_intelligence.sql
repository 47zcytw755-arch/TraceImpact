-- =============================================================================
-- TraceImpact 2.0: ML Anomaly Detection & AI Investigation Schema DDL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. ML Model Registry & Metadata
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ml_anomaly_models (
    model_id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,              -- e.g. 'IsolationForest_WorldBank'
    model_version VARCHAR(50) NOT NULL,           -- e.g. 'v1.0.0'
    algorithm VARCHAR(100) NOT NULL,              -- 'sklearn.ensemble.IsolationForest'
    hyperparameters JSONB NOT NULL,               -- {"contamination": 0.04, "n_estimators": 100, ...}
    features_used JSONB NOT NULL,                 -- ["val_norm", "z_score", "yoy_growth_pct", "hist_ratio"]
    training_sample_count INTEGER NOT NULL DEFAULT 0,
    contamination_rate NUMERIC(6, 4) DEFAULT 0.04,
    metrics_summary JSONB,                        -- {"total_evaluated": ..., "anomalies_flagged": ...}
    is_active BOOLEAN DEFAULT TRUE,
    trained_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ml_model_name_version UNIQUE (model_name, model_version)
);

CREATE INDEX IF NOT EXISTS idx_ml_models_active ON ml_anomaly_models(is_active);

-- -----------------------------------------------------------------------------
-- 2. ML Anomaly Detections Fact Table
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS world_bank_anomalies (
    anomaly_id SERIAL PRIMARY KEY,
    observation_id INTEGER NOT NULL REFERENCES world_bank_observations(observation_id) ON DELETE CASCADE,
    model_id INTEGER REFERENCES ml_anomaly_models(model_id) ON DELETE SET NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    country_code VARCHAR(10) NOT NULL,
    indicator_code VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    indicator_value NUMERIC(20, 4),
    anomaly_score NUMERIC(10, 6) NOT NULL,        -- Decision function score (lower = more anomalous)
    is_anomaly BOOLEAN NOT NULL DEFAULT TRUE,
    feature_snapshot JSONB NOT NULL,              -- Historical baseline stats, z-scores, growth rates
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_wb_anomalies_obs_version UNIQUE (observation_id, model_version)
);

CREATE INDEX IF NOT EXISTS idx_wb_anomalies_obs ON world_bank_anomalies(observation_id);
CREATE INDEX IF NOT EXISTS idx_wb_anomalies_country ON world_bank_anomalies(country_code);
CREATE INDEX IF NOT EXISTS idx_wb_anomalies_indicator ON world_bank_anomalies(indicator_code);
CREATE INDEX IF NOT EXISTS idx_wb_anomalies_year ON world_bank_anomalies(year);
CREATE INDEX IF NOT EXISTS idx_wb_anomalies_score ON world_bank_anomalies(anomaly_score);

-- -----------------------------------------------------------------------------
-- 3. AI Investigations Table
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_investigations (
    investigation_id SERIAL PRIMARY KEY,
    anomaly_id INTEGER NOT NULL REFERENCES world_bank_anomalies(anomaly_id) ON DELETE CASCADE,
    observation_id INTEGER NOT NULL REFERENCES world_bank_observations(observation_id) ON DELETE CASCADE,
    country_code VARCHAR(10) NOT NULL,
    indicator_code VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    finding_summary TEXT NOT NULL,
    structured_evidence JSONB NOT NULL,           -- Quantitative facts & statistical deviations
    historical_comparison JSONB NOT NULL,         -- Multi-year historical baseline comparison
    related_indicators JSONB NOT NULL,            -- Co-occurring indicator values for context
    ai_explanation TEXT NOT NULL,                 -- Synthesized narrative grounded in evidence
    possible_interpretation TEXT NOT NULL,        -- Plausible domain context explicitly marked as interpretation
    limitations TEXT NOT NULL,                    -- Strict non-causality statement & data boundaries
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_ai_investigations_anomaly UNIQUE (anomaly_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_inv_obs ON ai_investigations(observation_id);
CREATE INDEX IF NOT EXISTS idx_ai_inv_country ON ai_investigations(country_code);
CREATE INDEX IF NOT EXISTS idx_ai_inv_indicator ON ai_investigations(indicator_code);

-- -----------------------------------------------------------------------------
-- 4. AI Insights Table
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ai_insights (
    insight_id SERIAL PRIMARY KEY,
    investigation_id INTEGER REFERENCES ai_investigations(investigation_id) ON DELETE SET NULL,
    observation_id INTEGER NOT NULL REFERENCES world_bank_observations(observation_id) ON DELETE CASCADE,
    anomaly_id INTEGER REFERENCES world_bank_anomalies(anomaly_id) ON DELETE SET NULL,
    country_code VARCHAR(10) NOT NULL,
    indicator_code VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    insight_type VARCHAR(50) NOT NULL,            -- 'SHARP_DEVIATION', 'HISTORICAL_OUTLIER', 'VOLATILITY_SURGE'
    underlying_metrics JSONB NOT NULL,
    evidence_text TEXT NOT NULL,
    ai_explanation TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ai_insights_country ON ai_insights(country_code);
CREATE INDEX IF NOT EXISTS idx_ai_insights_indicator ON ai_insights(indicator_code);
CREATE INDEX IF NOT EXISTS idx_ai_insights_type ON ai_insights(insight_type);

-- -----------------------------------------------------------------------------
-- 5. Analytical Views for Intelligence & Full Lineage
-- -----------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_world_bank_anomalies_summary AS
SELECT 
    a.anomaly_id,
    a.observation_id,
    a.model_name,
    a.model_version,
    a.country_code,
    c.country_name,
    c.region,
    a.indicator_code,
    i.indicator_name,
    a.year,
    a.indicator_value,
    a.anomaly_score,
    a.is_anomaly,
    a.feature_snapshot,
    a.detected_at,
    CASE WHEN inv.investigation_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_investigation,
    inv.investigation_id
FROM world_bank_anomalies a
JOIN world_bank_countries c ON a.country_code = c.country_code
JOIN world_bank_indicators i ON a.indicator_code = i.indicator_code
LEFT JOIN ai_investigations inv ON a.anomaly_id = inv.anomaly_id;

CREATE OR REPLACE VIEW v_world_bank_ai_lineage AS
SELECT 
    ins.insight_id,
    ins.title AS insight_title,
    ins.insight_type,
    inv.investigation_id,
    inv.finding_summary,
    anom.anomaly_id,
    anom.model_name,
    anom.model_version,
    anom.anomaly_score,
    obs.observation_id,
    obs.country_code,
    c.country_name,
    obs.indicator_code,
    ind.indicator_name,
    obs.year,
    obs.indicator_value,
    raw.response_id,
    raw.page_number,
    raw.response_hash,
    raw.endpoint_url,
    run.run_id,
    run.source_name,
    run.status AS ingestion_status,
    run.started_at AS ingestion_started_at
FROM ai_insights ins
JOIN world_bank_observations obs ON ins.observation_id = obs.observation_id
JOIN world_bank_countries c ON obs.country_code = c.country_code
JOIN world_bank_indicators ind ON obs.indicator_code = ind.indicator_code
LEFT JOIN ai_investigations inv ON ins.investigation_id = inv.investigation_id
LEFT JOIN world_bank_anomalies anom ON ins.anomaly_id = anom.anomaly_id
LEFT JOIN api_raw_responses raw ON obs.raw_response_id = raw.response_id
LEFT JOIN api_ingestion_runs run ON raw.run_id = run.run_id;
