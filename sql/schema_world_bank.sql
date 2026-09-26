-- =============================================================================
-- TraceImpact 2.0: World Bank Public Indicators Schema DDL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. API Lineage & Staging (Bronze Layer)
-- -----------------------------------------------------------------------------

-- api_ingestion_runs: Tracks each API ingestion batch/run metadata
CREATE TABLE IF NOT EXISTS api_ingestion_runs (
    run_id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,            -- 'world_bank'
    endpoint_url TEXT NOT NULL,
    request_params JSONB NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'STARTED',-- 'STARTED', 'COMPLETED', 'FAILED'
    total_pages INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    records_inserted INTEGER DEFAULT 0,
    records_quarantined INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_runs_source ON api_ingestion_runs(source_name);
CREATE INDEX IF NOT EXISTS idx_api_runs_status ON api_ingestion_runs(status);

-- api_raw_responses: Immutable raw bronze storage for API page payloads
CREATE TABLE IF NOT EXISTS api_raw_responses (
    response_id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES api_ingestion_runs(run_id) ON DELETE CASCADE,
    source_name VARCHAR(100) NOT NULL,
    endpoint_url TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    per_page INTEGER NOT NULL,
    response_hash VARCHAR(64) NOT NULL,            -- SHA-256 of raw response bytes
    raw_payload JSONB NOT NULL,                   -- Complete JSON response from World Bank
    record_count INTEGER NOT NULL DEFAULT 0,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_api_raw_run_page ON api_raw_responses(run_id, page_number);
CREATE INDEX IF NOT EXISTS idx_api_raw_hash ON api_raw_responses(response_hash);

-- -----------------------------------------------------------------------------
-- 2. World Bank Domain Tables (Silver Layer)
-- -----------------------------------------------------------------------------

-- world_bank_countries: Dimension table of sovereign nations & regional aggregates
CREATE TABLE IF NOT EXISTS world_bank_countries (
    country_code VARCHAR(10) PRIMARY KEY,          -- ISO2 or region code (e.g. 'IN', 'US', 'WLD')
    iso3_code VARCHAR(10),                         -- ISO3 code (e.g. 'IND', 'USA')
    country_name VARCHAR(255) NOT NULL,
    region VARCHAR(100),
    income_level VARCHAR(100),
    lending_type VARCHAR(100),
    capital_city VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wb_countries_iso3 ON world_bank_countries(iso3_code);

-- world_bank_indicators: Dimension table of standard development indicators
CREATE TABLE IF NOT EXISTS world_bank_indicators (
    indicator_code VARCHAR(50) PRIMARY KEY,        -- e.g. 'NY.GDP.PCAP.CD'
    indicator_name VARCHAR(255) NOT NULL,
    topic VARCHAR(100),
    description TEXT,
    unit_of_measure VARCHAR(50),
    source_organization VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- world_bank_observations: Normalized fact table of country-year observations
CREATE TABLE IF NOT EXISTS world_bank_observations (
    observation_id SERIAL PRIMARY KEY,
    country_code VARCHAR(10) NOT NULL REFERENCES world_bank_countries(country_code) ON DELETE CASCADE,
    indicator_code VARCHAR(50) NOT NULL REFERENCES world_bank_indicators(indicator_code) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    indicator_value NUMERIC(20, 4),
    decimal_places INTEGER DEFAULT 0,
    obs_status VARCHAR(50),
    unit VARCHAR(50),
    raw_response_id INTEGER REFERENCES api_raw_responses(response_id) ON DELETE SET NULL,
    raw_record_index INTEGER,                     -- Offset index within raw_payload JSON array
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_wb_obs_country_indicator_year UNIQUE (country_code, indicator_code, year)
);

CREATE INDEX IF NOT EXISTS idx_wb_obs_country ON world_bank_observations(country_code);
CREATE INDEX IF NOT EXISTS idx_wb_obs_indicator ON world_bank_observations(indicator_code);
CREATE INDEX IF NOT EXISTS idx_wb_obs_year ON world_bank_observations(year);
CREATE INDEX IF NOT EXISTS idx_wb_obs_lineage ON world_bank_observations(raw_response_id);

-- -----------------------------------------------------------------------------
-- 3. World Bank Data Quality Issues (Observability Extension)
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS world_bank_data_quality_issues (
    issue_id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES api_ingestion_runs(run_id) ON DELETE CASCADE,
    raw_response_id INTEGER REFERENCES api_raw_responses(response_id) ON DELETE SET NULL,
    country_code VARCHAR(10),
    indicator_code VARCHAR(50),
    year INTEGER,
    issue_type VARCHAR(50) NOT NULL,              -- MISSING_VALUE, INVALID_NUMBER, UNKNOWN_COUNTRY, DUPLICATE_OBSERVATION
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO',  -- INFO, WARNING, ERROR
    raw_value TEXT,
    description TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',   -- OPEN, RESOLVED, QUARANTINED
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wb_dq_type ON world_bank_data_quality_issues(issue_type);
CREATE INDEX IF NOT EXISTS idx_wb_dq_severity ON world_bank_data_quality_issues(severity);
CREATE INDEX IF NOT EXISTS idx_wb_dq_status ON world_bank_data_quality_issues(status);
