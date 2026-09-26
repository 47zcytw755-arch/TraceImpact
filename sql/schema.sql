-- =============================================================================
-- TraceImpact: Traceable Impact Reporting & Data Quality Platform
-- PostgreSQL Relational DDL & Lineage Schema
-- =============================================================================

-- Enable UUID extension if needed in future extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. LINEAGE & AUDIT METADATA TABLES (The Foundation of Traceability)
-- -----------------------------------------------------------------------------

-- SOURCE_FILES:
-- Tracks each physical CSV/Excel file processed by the system.
-- Storing file_hash (SHA-256) guarantees data immutability and detects if a file
-- was modified or re-uploaded.
CREATE TABLE IF NOT EXISTS source_files (
    file_id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    total_rows INTEGER NOT NULL DEFAULT 0,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- SOURCE_RECORDS:
-- Immutable staging table storing raw data as JSONB.
-- Every transformed record in business tables will reference record_id.
-- This enables direct 1-to-1 drilldown from high-level KPIs back to the exact source row.
CREATE TABLE IF NOT EXISTS source_records (
    record_id SERIAL PRIMARY KEY,
    file_id INTEGER NOT NULL REFERENCES source_files(file_id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    raw_data JSONB NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index on file_id and row_index for high-performance lineage lookups
CREATE INDEX IF NOT EXISTS idx_source_records_file ON source_records(file_id, row_index);

-- DATA_QUALITY_ISSUES:
-- Audit log of all detected anomalies (duplicates, missing values, format errors).
-- Critical concept: Dirty data is NOT silently dropped; it is cataloged with severity & status.
CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES source_files(file_id) ON DELETE CASCADE,
    record_id INTEGER REFERENCES source_records(record_id) ON DELETE SET NULL,
    program_id VARCHAR(50) REFERENCES programs(program_id) ON DELETE SET NULL,
    row_number INTEGER,
    column_name VARCHAR(100),
    issue_type VARCHAR(50) NOT NULL,       -- e.g., DUPLICATE, MISSING_VALUE, INVALID_FORMAT, INVALID_NUMBER, UNMATCHED_REFERENCE
    severity VARCHAR(20) NOT NULL DEFAULT 'INFO', -- INFO, WARNING, ERROR
    raw_value TEXT,
    description TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN', -- OPEN, RESOLVED, ACCEPTED
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(100),
    resolution_notes TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dq_issues_type ON data_quality_issues(issue_type);
CREATE INDEX IF NOT EXISTS idx_dq_issues_status ON data_quality_issues(status);
CREATE INDEX IF NOT EXISTS idx_dq_issues_program ON data_quality_issues(program_id);
CREATE INDEX IF NOT EXISTS idx_dq_issues_severity ON data_quality_issues(severity);

-- -----------------------------------------------------------------------------
-- 2. NORMALIZED CORE DOMAIN TABLES (Cleaned & Structured Data)
-- -----------------------------------------------------------------------------

-- PROGRAMS:
-- Master entity representing organization initiatives.
CREATE TABLE IF NOT EXISTS programs (
    program_id VARCHAR(50) PRIMARY KEY,
    source_record_id INTEGER REFERENCES source_records(record_id) ON DELETE SET NULL,
    program_name VARCHAR(255) NOT NULL,
    target_category VARCHAR(100),
    budget_allocated NUMERIC(12, 2) DEFAULT 0.00,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- BENEFICIARIES:
-- Master entity for community members served.
-- Includes anonymized_code (hashed identifier) to satisfy PII privacy requirements.
CREATE TABLE IF NOT EXISTS beneficiaries (
    beneficiary_id VARCHAR(50) PRIMARY KEY,
    source_record_id INTEGER REFERENCES source_records(record_id) ON DELETE SET NULL,
    anonymized_code VARCHAR(64) UNIQUE,
    gender VARCHAR(20),
    age INTEGER,
    city_location VARCHAR(100),
    registration_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_beneficiaries_location ON beneficiaries(city_location);

-- ATTENDANCE:
-- Fact table recording participation in specific program sessions.
-- Composite foreign keys connect back to beneficiaries and programs.
CREATE TABLE IF NOT EXISTS attendance (
    attendance_id VARCHAR(50) PRIMARY KEY,
    source_record_id INTEGER REFERENCES source_records(record_id) ON DELETE SET NULL,
    beneficiary_id VARCHAR(50) REFERENCES beneficiaries(beneficiary_id) ON DELETE CASCADE,
    program_id VARCHAR(50) REFERENCES programs(program_id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    attendance_status VARCHAR(50) DEFAULT 'Present',
    session_hours NUMERIC(4, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(session_date);
CREATE INDEX IF NOT EXISTS idx_attendance_beneficiary ON attendance(beneficiary_id);
CREATE INDEX IF NOT EXISTS idx_attendance_program ON attendance(program_id);

-- EXPENSES:
-- Fact table tracking operational costs linked to specific programs.
CREATE TABLE IF NOT EXISTS expenses (
    expense_id VARCHAR(50) PRIMARY KEY,
    source_record_id INTEGER REFERENCES source_records(record_id) ON DELETE SET NULL,
    program_id VARCHAR(50) REFERENCES programs(program_id) ON DELETE CASCADE,
    expense_category VARCHAR(100) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    incurred_date DATE NOT NULL,
    receipt_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_expenses_program ON expenses(program_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(incurred_date);

-- OUTCOMES:
-- Fact table tracking baseline vs exit evaluations of beneficiaries.
CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id VARCHAR(50) PRIMARY KEY,
    source_record_id INTEGER REFERENCES source_records(record_id) ON DELETE SET NULL,
    beneficiary_id VARCHAR(50) REFERENCES beneficiaries(beneficiary_id) ON DELETE CASCADE,
    program_id VARCHAR(50) REFERENCES programs(program_id) ON DELETE CASCADE,
    indicator_name VARCHAR(255) NOT NULL,
    baseline_score NUMERIC(5, 2),
    exit_score NUMERIC(5, 2),
    evaluation_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outcomes_beneficiary ON outcomes(beneficiary_id);
