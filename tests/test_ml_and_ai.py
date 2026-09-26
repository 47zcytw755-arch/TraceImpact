"""
Comprehensive Test Suite for TraceImpact 2.0 ML Anomaly Detection and AI Investigation.

Tests:
1. Feature Extractor (time-series, growth, cross-sectional peer features, edge cases).
2. Isolation Forest Anomaly Detector (training, persistence, scoring, idempotency).
3. AI Investigation Engine (grounded evidence, fact vs interpretation, non-causality notice).
4. AI Insights Generation & Persistence.
5. End-to-End Lineage Traceability (`v_world_bank_ai_lineage`).
6. Security controls and read-only constraints on ML/AI queries.
"""

import os
import json
import pytest
import pandas as pd
import numpy as np
from sqlalchemy import text

from src.database.connection import engine
from src.ml.feature_extractor import WorldBankFeatureExtractor
from src.ml.anomaly_detector import WorldBankAnomalyDetector
from src.ai.investigator import WorldBankInvestigator
from src.dashboard.queries import (
    get_ml_anomaly_models,
    get_world_bank_anomalies,
    get_anomaly_investigation,
    get_ai_insights,
    get_ai_lineage_trace,
)
from src.dashboard.ai_assistant import AIAssistantEngine


# -----------------------------------------------------------------------------
# 1. Feature Extraction Tests
# -----------------------------------------------------------------------------

def test_feature_extractor_basic_and_shapes():
    """Verifies feature extraction shapes, columns, and snapshot structure."""
    extractor = WorldBankFeatureExtractor()
    
    # Mock observation series with a known extreme jump
    mock_data = pd.DataFrame([
        {"observation_id": 1, "country_code": "TST", "indicator_code": "IND.1", "year": 2018, "indicator_value": 100.0},
        {"observation_id": 2, "country_code": "TST", "indicator_code": "IND.1", "year": 2019, "indicator_value": 105.0},
        {"observation_id": 3, "country_code": "TST", "indicator_code": "IND.1", "year": 2020, "indicator_value": 110.0},
        {"observation_id": 4, "country_code": "TST", "indicator_code": "IND.1", "year": 2021, "indicator_value": 250.0}, # Spike
    ])
    
    X, meta = extractor.extract_features(mock_data)
    
    assert len(X) == 4
    assert len(meta) == 4
    for col in WorldBankFeatureExtractor.FEATURE_COLS:
        assert col in X.columns
    
    # 2021 spike should have positive YoY growth and high z-score
    row_spike = meta[meta["year"] == 2021].iloc[0]
    snap = row_spike["feature_snapshot"]
    assert snap["yoy_growth_pct"] > 100.0
    assert snap["z_score"] > 1.0


def test_feature_extractor_empty_and_nan_handling():
    """Verifies graceful handling of empty inputs and non-numeric values."""
    extractor = WorldBankFeatureExtractor()
    
    X_empty, meta_empty = extractor.extract_features(pd.DataFrame())
    assert X_empty.empty
    assert meta_empty.empty
    
    # Non-numeric indicator values
    bad_data = pd.DataFrame([
        {"observation_id": 1, "country_code": "X", "indicator_code": "I", "year": 2020, "indicator_value": "NOT_A_NUM"},
    ])
    X_bad, meta_bad = extractor.extract_features(bad_data)
    assert X_bad.empty
    assert meta_bad.empty


# -----------------------------------------------------------------------------
# 2. ML Anomaly Detection Tests
# -----------------------------------------------------------------------------

def test_anomaly_detector_training_and_db_registration():
    """Tests fitting IsolationForest and registering metadata in ml_anomaly_models."""
    detector = WorldBankAnomalyDetector(model_version="v_test_suite", contamination=0.1)
    
    # Train on existing database records
    result = detector.train_and_register()
    assert result["status"] == "SUCCESS"
    assert result["model_version"] == "v_test_suite"
    assert "metrics" in result
    assert result["metrics"]["total_evaluated"] > 0
    
    # Verify entry in PostgreSQL ml_anomaly_models
    models = get_ml_anomaly_models()
    assert not models.empty
    assert "v_test_suite" in models["model_version"].values


def test_anomaly_detector_detect_and_persist_idempotency():
    """Verifies that running detect_and_persist_anomalies twice does not produce duplicates."""
    detector = WorldBankAnomalyDetector(model_version="v_test_suite", contamination=0.05)
    
    res1 = detector.detect_and_persist_anomalies()
    assert res1["status"] == "SUCCESS"
    count1 = res1["anomalies_persisted"]
    
    # Second execution should update in-place via ON CONFLICT DO UPDATE
    res2 = detector.detect_and_persist_anomalies()
    assert res2["status"] == "SUCCESS"
    assert res2["anomalies_persisted"] == count1


# -----------------------------------------------------------------------------
# 3. AI Investigation Engine Tests
# -----------------------------------------------------------------------------

def test_ai_investigator_generates_grounded_finding_and_evidence():
    """Verifies that investigation outputs facts, historical baseline, and non-causality disclaimer."""
    anomalies = get_world_bank_anomalies(limit=1)
    assert not anomalies.empty, "Database must have at least 1 anomaly to test investigation."
    
    target_anomaly_id = int(anomalies.iloc[0]["anomaly_id"])
    investigator = WorldBankInvestigator()
    inv = investigator.investigate_anomaly(target_anomaly_id)
    
    assert inv["investigation_id"] > 0
    assert inv["anomaly_id"] == target_anomaly_id
    assert len(inv["finding_summary"]) > 20
    assert "structured_evidence" in inv
    assert "historical_baseline" in inv["structured_evidence"]
    assert "z_score" in inv["structured_evidence"]["historical_baseline"]
    
    # Verify strict non-causality disclaimer presence
    assert "CAUSALITY DISCLAIMER" in inv["limitations"]
    assert "DO NOT establish causality" in inv["limitations"]


def test_ai_investigator_creates_companion_insight():
    """Verifies that an AI insight is persisted and discoverable via get_ai_insights."""
    anomalies = get_world_bank_anomalies(limit=1)
    target_anomaly_id = int(anomalies.iloc[0]["anomaly_id"])
    
    investigator = WorldBankInvestigator()
    inv = investigator.investigate_anomaly(target_anomaly_id)
    
    insights = get_ai_insights(limit=10)
    assert not insights.empty
    assert target_anomaly_id in insights["anomaly_id"].values


# -----------------------------------------------------------------------------
# 4. End-to-End Lineage Traceability Tests
# -----------------------------------------------------------------------------

def test_v_world_bank_ai_lineage_trace():
    """Verifies complete 7-step lineage linking insight to raw SHA-256 API response."""
    insights = get_ai_insights(limit=1)
    assert not insights.empty
    
    insight_id = int(insights.iloc[0]["insight_id"])
    lineage = get_ai_lineage_trace(insight_id=insight_id)
    
    assert lineage is not None
    assert lineage["insight_id"] == insight_id
    assert lineage["observation_id"] is not None
    assert lineage["anomaly_score"] is not None
    assert lineage["response_hash"] is not None
    assert len(lineage["response_hash"]) == 64  # SHA-256 hex string length
    assert lineage["run_id"] is not None


# -----------------------------------------------------------------------------
# 5. Security & Read-Only Constraints Tests
# -----------------------------------------------------------------------------

def test_ai_security_rejects_dml_and_ddl_on_world_bank():
    """Ensures AI Assistant validator rejects any write/drop attempts on World Bank schema."""
    malicious_queries = [
        "DROP TABLE world_bank_anomalies;",
        "DELETE FROM world_bank_observations WHERE year = 2020;",
        "UPDATE world_bank_indicators SET indicator_name = 'Hacked';",
        "INSERT INTO ai_insights (title) VALUES ('Fake');",
        "ALTER TABLE world_bank_countries DROP COLUMN region;",
        "TRUNCATE TABLE api_ingestion_runs;",
        "SELECT * FROM world_bank_observations; DROP TABLE users; --",
        "SELECT * FROM world_bank_observations /* bypass */ WHERE 1=1;",
    ]
    for q in malicious_queries:
        assert not AIAssistantEngine.validate_sql(q), f"Security bypass detected for query: {q}"


def test_ai_security_allows_approved_world_bank_views():
    """Ensures AI Assistant validator permits read-only SELECT queries on approved views."""
    safe_queries = [
        "SELECT country_name, region FROM world_bank_countries LIMIT 5;",
        "SELECT * FROM v_world_bank_anomalies_summary WHERE is_anomaly = TRUE;",
        "SELECT * FROM v_world_bank_ai_lineage LIMIT 10;",
        "SELECT * FROM v_world_bank_latest_indicators;",
    ]
    for q in safe_queries:
        assert AIAssistantEngine.validate_sql(q), f"Valid read-only query rejected: {q}"
