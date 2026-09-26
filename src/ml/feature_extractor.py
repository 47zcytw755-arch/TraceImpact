"""
Feature Extraction Engine for World Bank Indicators Anomaly Detection.

Transforms raw country-indicator-year observations into statistical features:
1. Time-series features (country-level historical mean, std, z-score, YoY growth rate).
2. Cross-sectional features (year-specific peer group mean, std, peer z-score).
"""

import logging
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class WorldBankFeatureExtractor:
    """
    Computes time-series and peer-group statistical features for World Bank observations.
    """

    FEATURE_COLS = [
        "z_score",
        "yoy_growth_pct",
        "peer_z_score",
        "hist_ratio",
    ]

    def __init__(self):
        pass

    def extract_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract features from a DataFrame of observations.

        Expected columns in df:
            ['observation_id', 'country_code', 'indicator_code', 'year', 'indicator_value']

        Returns:
            Tuple of:
                - feature_matrix (pd.DataFrame with FEATURE_COLS for ML training/inference)
                - metadata_df (pd.DataFrame with observation metadata & feature snapshots)
        """
        if df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # Work on a copy with valid numeric values
        work_df = df.copy()
        work_df["indicator_value"] = pd.to_numeric(work_df["indicator_value"], errors="coerce")
        work_df = work_df.dropna(subset=["indicator_value"]).sort_values(
            by=["country_code", "indicator_code", "year"]
        ).reset_index(drop=True)

        if work_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # 1. Country-level historical baseline (per country & indicator)
        country_stats = work_df.groupby(["country_code", "indicator_code"])["indicator_value"].agg(
            hist_mean="mean",
            hist_std="std"
        ).reset_index()
        # Default std to 0 when count == 1 or variance is 0
        country_stats["hist_std"] = country_stats["hist_std"].fillna(0.0)

        work_df = pd.merge(work_df, country_stats, on=["country_code", "indicator_code"], how="left")

        # Z-score within country history (with small epsilon to avoid div by zero)
        eps = 1e-6
        work_df["z_score"] = (work_df["indicator_value"] - work_df["hist_mean"]) / (
            work_df["hist_std"] + eps
        )

        # Ratio to historical mean
        work_df["hist_ratio"] = work_df["indicator_value"] / (
            work_df["hist_mean"].replace(0, np.nan) + eps
        )
        work_df["hist_ratio"] = work_df["hist_ratio"].fillna(1.0)

        # 2. Time-series Year-over-Year (YoY) Change & Growth %
        work_df["prev_year"] = work_df.groupby(["country_code", "indicator_code"])["year"].shift(1)
        work_df["prev_val"] = work_df.groupby(["country_code", "indicator_code"])["indicator_value"].shift(1)

        # Only compute YoY if consecutive year (current year == prev_year + 1)
        is_consecutive = (work_df["year"] == work_df["prev_year"] + 1)
        work_df["yoy_growth_pct"] = np.where(
            is_consecutive & (work_df["prev_val"] != 0) & work_df["prev_val"].notnull(),
            ((work_df["indicator_value"] - work_df["prev_val"]) / work_df["prev_val"].abs()) * 100.0,
            0.0
        )
        work_df["yoy_growth_pct"] = work_df["yoy_growth_pct"].clip(-500.0, 500.0)  # Clip extreme outliers

        # 3. Cross-sectional Peer Group (per indicator & year across all countries)
        peer_stats = work_df.groupby(["indicator_code", "year"])["indicator_value"].agg(
            peer_mean="mean",
            peer_std="std"
        ).reset_index()
        peer_stats["peer_std"] = peer_stats["peer_std"].fillna(0.0)

        work_df = pd.merge(work_df, peer_stats, on=["indicator_code", "year"], how="left")
        work_df["peer_z_score"] = (work_df["indicator_value"] - work_df["peer_mean"]) / (
            work_df["peer_std"] + eps
        )

        # Fill any remaining NaNs or Infs
        for col in self.FEATURE_COLS:
            work_df[col] = work_df[col].replace([np.inf, -np.inf], 0.0).fillna(0.0)

        # Prepare feature snapshot dictionary for every observation
        def build_snapshot(row):
            return {
                "historical_mean": round(float(row["hist_mean"]), 4) if pd.notnull(row["hist_mean"]) else None,
                "historical_std": round(float(row["hist_std"]), 4) if pd.notnull(row["hist_std"]) else None,
                "z_score": round(float(row["z_score"]), 4),
                "yoy_growth_pct": round(float(row["yoy_growth_pct"]), 2),
                "peer_mean": round(float(row["peer_mean"]), 4) if pd.notnull(row["peer_mean"]) else None,
                "peer_z_score": round(float(row["peer_z_score"]), 4),
                "hist_ratio": round(float(row["hist_ratio"]), 4),
            }

        work_df["feature_snapshot"] = work_df.apply(build_snapshot, axis=1)

        feature_matrix = work_df[self.FEATURE_COLS].copy()
        metadata_cols = [
            "observation_id",
            "country_code",
            "indicator_code",
            "year",
            "indicator_value",
            "feature_snapshot"
        ]
        metadata_df = work_df[metadata_cols].copy()

        return feature_matrix, metadata_df
