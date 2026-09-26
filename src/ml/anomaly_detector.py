"""
ML Anomaly Detection Service for World Bank Indicators.

Uses scikit-learn's Isolation Forest to identify statistical anomalies in country-year
indicator trajectories and cross-country peer baselines.

IMPORTANT ARCHITECTURAL RULE:
The model detects statistical anomalies based strictly on multi-year baselines and
peer distributions. It DOES NOT determine causality or ascribe historical causes.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import engine as default_engine
from src.ml.feature_extractor import WorldBankFeatureExtractor

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")


class WorldBankAnomalyDetector:
    """
    Trains, manages, and executes Isolation Forest anomaly detection on World Bank indicators.
    """

    MODEL_NAME = "IsolationForest_WorldBank"
    DEFAULT_VERSION = "v1.0.0"

    def __init__(
        self,
        engine: Optional[Engine] = None,
        model_version: str = DEFAULT_VERSION,
        contamination: float = 0.04,
        n_estimators: int = 100,
        random_state: int = 42,
    ):
        self.engine = engine or default_engine
        self.model_version = model_version
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model: Optional[IsolationForest] = None
        self.feature_extractor = WorldBankFeatureExtractor()
        os.makedirs(MODEL_DIR, exist_ok=True)

    def _get_model_file_path(self) -> str:
        return os.path.join(MODEL_DIR, f"{self.MODEL_NAME}_{self.model_version}.joblib")

    def train_and_register(self, df_observations: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Extract features, fit Isolation Forest, save weights to disk, and register in PostgreSQL.
        """
        if df_observations is None:
            query = """
                SELECT observation_id, country_code, indicator_code, year, indicator_value
                FROM world_bank_observations
                WHERE indicator_value IS NOT NULL
            """
            with self.engine.connect() as conn:
                df_observations = pd.read_sql(text(query), conn)

        if df_observations.empty:
            logger.warning("No observations found for training anomaly detector.")
            return {"status": "SKIPPED", "reason": "No data"}

        logger.info(f"Extracting features for {len(df_observations)} observations...")
        X, meta = self.feature_extractor.extract_features(df_observations)

        if X.empty:
            return {"status": "SKIPPED", "reason": "Empty feature matrix"}

        logger.info(f"Training IsolationForest with contamination={self.contamination}, n_estimators={self.n_estimators}...")
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=1
        )
        self.model.fit(X)

        # Save model weights to disk
        model_path = self._get_model_file_path()
        joblib.dump(self.model, model_path)
        logger.info(f"Model saved to {model_path}")

        # Compute initial training metrics
        scores = self.model.decision_function(X)
        preds = self.model.predict(X)
        anomaly_count = int((preds == -1).sum())

        metrics = {
            "total_evaluated": len(X),
            "anomalies_flagged": anomaly_count,
            "anomaly_rate_pct": round((anomaly_count / len(X)) * 100.0, 2),
            "min_score": round(float(scores.min()), 5),
            "mean_score": round(float(scores.mean()), 5),
            "max_score": round(float(scores.max()), 5),
        }

        # Register or update in PostgreSQL ml_anomaly_models
        model_id = self._register_model_in_db(metrics, len(X))

        return {
            "status": "SUCCESS",
            "model_id": model_id,
            "model_name": self.MODEL_NAME,
            "model_version": self.model_version,
            "training_samples": len(X),
            "metrics": metrics,
        }

    def _register_model_in_db(self, metrics: Dict[str, Any], sample_count: int) -> int:
        """
        Record model metadata and hyperparameter tracking in PostgreSQL.
        """
        hyperparams = {
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "random_state": self.random_state,
        }
        features_json = json.dumps(self.feature_extractor.FEATURE_COLS)
        hyperparams_json = json.dumps(hyperparams)
        metrics_json = json.dumps(metrics)

        sql = """
            INSERT INTO ml_anomaly_models (
                model_name, model_version, algorithm, hyperparameters,
                features_used, training_sample_count, contamination_rate,
                metrics_summary, is_active
            )
            VALUES (
                :model_name, :model_version, :algorithm, CAST(:hyperparameters AS JSONB),
                CAST(:features_used AS JSONB), :sample_count, :contamination,
                CAST(:metrics_summary AS JSONB), TRUE
            )
            ON CONFLICT (model_name, model_version) DO UPDATE SET
                hyperparameters = EXCLUDED.hyperparameters,
                features_used = EXCLUDED.features_used,
                training_sample_count = EXCLUDED.training_sample_count,
                contamination_rate = EXCLUDED.contamination_rate,
                metrics_summary = EXCLUDED.metrics_summary,
                trained_at = CURRENT_TIMESTAMP
            RETURNING model_id;
        """

        with self.engine.begin() as conn:
            result = conn.execute(
                text(sql),
                {
                    "model_name": self.MODEL_NAME,
                    "model_version": self.model_version,
                    "algorithm": "sklearn.ensemble.IsolationForest",
                    "hyperparameters": hyperparams_json,
                    "features_used": features_json,
                    "sample_count": sample_count,
                    "contamination": self.contamination,
                    "metrics_summary": metrics_json,
                }
            )
            model_id = result.scalar()
        return model_id

    def load_model(self) -> bool:
        """
        Load persisted model from disk if available.
        """
        model_path = self._get_model_file_path()
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                logger.info(f"Loaded existing model from {model_path}")
                return True
            except Exception as e:
                logger.warning(f"Could not load model from {model_path}: {e}")
        return False

    def detect_and_persist_anomalies(self, df_observations: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Extract features, run inference using current model, and persist anomalous
        observations to PostgreSQL world_bank_anomalies table.
        """
        if self.model is None and not self.load_model():
            logger.info("No persisted model found. Training fresh model...")
            train_res = self.train_and_register(df_observations)
            if train_res.get("status") != "SUCCESS":
                return train_res

        if df_observations is None:
            query = """
                SELECT observation_id, country_code, indicator_code, year, indicator_value
                FROM world_bank_observations
                WHERE indicator_value IS NOT NULL
            """
            with self.engine.connect() as conn:
                df_observations = pd.read_sql(text(query), conn)

        if df_observations.empty:
            return {"status": "SKIPPED", "anomalies_detected": 0}

        X, meta = self.feature_extractor.extract_features(df_observations)
        if X.empty:
            return {"status": "SKIPPED", "anomalies_detected": 0}

        # Predict anomaly scores (decision_function) and anomaly flags (-1 is anomaly)
        scores = self.model.decision_function(X)
        preds = self.model.predict(X)

        meta["anomaly_score"] = scores
        meta["is_anomaly"] = (preds == -1)

        anomalies_df = meta[meta["is_anomaly"]].copy()
        logger.info(f"Detected {len(anomalies_df)} anomalies out of {len(meta)} observations.")

        # Persist anomalies to database
        saved_count = self._persist_anomalies(anomalies_df)

        return {
            "status": "SUCCESS",
            "total_evaluated": len(meta),
            "anomalies_detected": len(anomalies_df),
            "anomalies_persisted": saved_count,
            "model_name": self.MODEL_NAME,
            "model_version": self.model_version,
        }

    def _persist_anomalies(self, df: pd.DataFrame) -> int:
        """
        Batch insert or update detected anomalies in world_bank_anomalies table.
        """
        if df.empty:
            return 0

        # Fetch active model_id
        model_id = None
        with self.engine.connect() as conn:
            res = conn.execute(
                text("SELECT model_id FROM ml_anomaly_models WHERE model_name = :name AND model_version = :ver"),
                {"name": self.MODEL_NAME, "ver": self.model_version}
            ).scalar()
            if res:
                model_id = res

        sql = """
            INSERT INTO world_bank_anomalies (
                observation_id, model_id, model_name, model_version,
                country_code, indicator_code, year, indicator_value,
                anomaly_score, is_anomaly, feature_snapshot
            )
            VALUES (
                :observation_id, :model_id, :model_name, :model_version,
                :country_code, :indicator_code, :year, :indicator_value,
                :anomaly_score, :is_anomaly, CAST(:feature_snapshot AS JSONB)
            )
            ON CONFLICT (observation_id, model_version) DO UPDATE SET
                anomaly_score = EXCLUDED.anomaly_score,
                is_anomaly = EXCLUDED.is_anomaly,
                feature_snapshot = EXCLUDED.feature_snapshot,
                detected_at = CURRENT_TIMESTAMP;
        """

        records = []
        for _, row in df.iterrows():
            records.append({
                "observation_id": int(row["observation_id"]),
                "model_id": model_id,
                "model_name": self.MODEL_NAME,
                "model_version": self.model_version,
                "country_code": str(row["country_code"]),
                "indicator_code": str(row["indicator_code"]),
                "year": int(row["year"]),
                "indicator_value": float(row["indicator_value"]) if pd.notnull(row["indicator_value"]) else None,
                "anomaly_score": round(float(row["anomaly_score"]), 6),
                "is_anomaly": bool(row["is_anomaly"]),
                "feature_snapshot": json.dumps(row["feature_snapshot"]),
            })

        with self.engine.begin() as conn:
            conn.execute(text(sql), records)

        return len(records)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    detector = WorldBankAnomalyDetector()
    train_res = detector.train_and_register()
    print("Train result:", train_res)
    detect_res = detector.detect_and_persist_anomalies()
    print("Detection result:", detect_res)
