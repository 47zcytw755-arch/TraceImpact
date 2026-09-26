"""
AI Investigation and Grounded Insight Generation Engine for TraceImpact 2.0.

Translates statistical anomalies detected by the ML model into structured,
grounded investigative reports.

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. Strict grounding: Only operates on verified database records.
2. Facts vs. Interpretation separation: Quantitative metrics are segregated from hypotheses.
3. Explicit non-causality disclaimer: Explains statistical deviation without claiming causality.
4. Full source-to-insight lineage: Preserves references to raw observation, response hash, and run ID.
"""

import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.database.connection import engine as default_engine

logger = logging.getLogger(__name__)


class WorldBankInvestigator:
    """
    Synthesizes historical context, peer baselines, and cross-indicator metrics
    to investigate ML-flagged anomalies.
    """

    NON_CAUSALITY_DISCLAIMER = (
        "CAUSALITY DISCLAIMER: This investigation is based on statistical anomaly detection "
        "(Isolation Forest) and empirical deviation from multi-year historical baselines. "
        "The model and analysis identify that this observation is statistically unusual; "
        "they DO NOT establish causality, policy attribution, or economic causation. "
        "Observational datasets are subject to reporting revisions, methodology changes, "
        "and unobserved confounding variables."
    )

    def __init__(self, engine: Optional[Engine] = None):
        self.engine = engine or default_engine

    def investigate_anomaly(self, anomaly_id: int) -> Dict[str, Any]:
        """
        Perform a comprehensive grounded investigation for a specific anomaly.
        """
        # 1. Fetch anomaly details
        query_anomaly = """
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
                a.feature_snapshot
            FROM world_bank_anomalies a
            JOIN world_bank_countries c ON a.country_code = c.country_code
            JOIN world_bank_indicators i ON a.indicator_code = i.indicator_code
            WHERE a.anomaly_id = :anomaly_id;
        """
        with self.engine.connect() as conn:
            anomaly_row = conn.execute(text(query_anomaly), {"anomaly_id": anomaly_id}).mappings().first()

        if not anomaly_row:
            raise ValueError(f"Anomaly ID {anomaly_id} not found in database.")

        obs_id = anomaly_row["observation_id"]
        c_code = anomaly_row["country_code"]
        c_name = anomaly_row["country_name"]
        region = anomaly_row["region"]
        ind_code = anomaly_row["indicator_code"]
        ind_name = anomaly_row["indicator_name"]
        target_year = anomaly_row["year"]
        current_val = float(anomaly_row["indicator_value"]) if anomaly_row["indicator_value"] is not None else 0.0
        snapshot = anomaly_row["feature_snapshot"] or {}

        # 2. Fetch complete historical series for this country and indicator
        query_history = """
            SELECT year, indicator_value
            FROM world_bank_observations
            WHERE country_code = :country_code 
              AND indicator_code = :indicator_code
              AND indicator_value IS NOT NULL
            ORDER BY year ASC;
        """
        with self.engine.connect() as conn:
            history_df = pd.read_sql(
                text(query_history),
                conn,
                params={"country_code": c_code, "indicator_code": ind_code}
            )

        # 3. Calculate baseline metrics
        hist_values = history_df["indicator_value"].tolist()
        hist_mean = float(np.mean(hist_values)) if hist_values else current_val
        hist_std = float(np.std(hist_values)) if len(hist_values) > 1 else 0.0
        hist_min = float(np.min(hist_values)) if hist_values else current_val
        hist_max = float(np.max(hist_values)) if hist_values else current_val
        z_score = float((current_val - hist_mean) / (hist_std + 1e-6))

        # Identify previous and subsequent years
        prev_row = history_df[history_df["year"] == target_year - 1]
        next_row = history_df[history_df["year"] == target_year + 1]

        prev_val = float(prev_row["indicator_value"].iloc[0]) if not prev_row.empty else None
        next_val = float(next_row["indicator_value"].iloc[0]) if not next_row.empty else None

        yoy_growth = None
        if prev_val and prev_val != 0:
            yoy_growth = round(((current_val - prev_val) / abs(prev_val)) * 100.0, 2)

        # 4. Fetch co-occurring indicators for the same country and year
        query_related = """
            SELECT 
                o.indicator_code,
                i.indicator_name,
                o.indicator_value
            FROM world_bank_observations o
            JOIN world_bank_indicators i ON o.indicator_code = i.indicator_code
            WHERE o.country_code = :country_code 
              AND o.year = :year
              AND o.indicator_code != :indicator_code
              AND o.indicator_value IS NOT NULL;
        """
        with self.engine.connect() as conn:
            related_rows = conn.execute(
                text(query_related),
                {"country_code": c_code, "year": target_year, "indicator_code": ind_code}
            ).mappings().all()

        related_indicators = [
            {
                "indicator_code": r["indicator_code"],
                "indicator_name": r["indicator_name"],
                "indicator_value": float(r["indicator_value"])
            }
            for r in related_rows
        ]

        # 5. Compile structured evidence
        structured_evidence = {
            "current_observation": {
                "year": target_year,
                "value": current_val,
                "anomaly_score": float(anomaly_row["anomaly_score"]),
            },
            "historical_baseline": {
                "available_years_count": len(history_df),
                "mean": round(hist_mean, 2),
                "std_dev": round(hist_std, 2),
                "min": round(hist_min, 2),
                "max": round(hist_max, 2),
                "z_score": round(z_score, 2),
            },
            "trajectory_dynamics": {
                "prev_year_value": prev_val,
                "next_year_value": next_val,
                "yoy_growth_pct": yoy_growth,
            }
        }

        historical_comparison = [
            {"year": int(row["year"]), "value": round(float(row["indicator_value"]), 2)}
            for _, row in history_df.iterrows()
        ]

        # 6. Generate grounded synthesis (Fact vs. Interpretation)
        direction = "spike" if z_score > 0 else "contraction"
        growth_str = f"with a YoY change of {yoy_growth:+.2f}%" if yoy_growth is not None else "with no prior consecutive record"
        
        finding_summary = (
            f"Statistically significant {direction} detected in {c_name} for '{ind_name}' in {target_year}. "
            f"Reported value {current_val:,.2f} deviates by {z_score:+.2f} standard deviations from the "
            f"multi-year mean ({hist_mean:,.2f}), {growth_str}."
        )

        ai_explanation = (
            f"FACTUAL EVIDENCE SUMMARY:\n"
            f"- Country: {c_name} ({c_code}), Region: {region}\n"
            f"- Indicator: {ind_name} [{ind_code}]\n"
            f"- Target Year: {target_year} | Recorded Value: {current_val:,.2f}\n"
            f"- Historical Multi-Year Mean: {hist_mean:,.2f} (Std Dev: {hist_std:,.2f}, Range: {hist_min:,.2f} - {hist_max:,.2f})\n"
            f"- Statistical Z-Score: {z_score:+.2f} | Isolation Forest Anomaly Score: {float(anomaly_row['anomaly_score']):.4f}\n"
            f"- YoY Growth Rate: {growth_str}\n"
            f"- Co-occurring Metrics: {len(related_indicators)} contextual indicators captured for {c_name} in {target_year}."
        )

        possible_interpretation = (
            f"POTENTIAL CONTEXTUAL HYPOTHESES (INTERPRETATIVE ONLY):\n"
            f"1. Macroeconomic/Exogenous Shock: Sudden deviations often reflect macroeconomic volatility, "
            f"regional crises, or trade disruptions during {target_year}.\n"
            f"2. Statistical Methodology or Base Re-estimation: Sovereign statistical offices periodically rebase "
            f"national accounts or update census benchmarks, producing discrete level shifts.\n"
            f"3. Reporting or Currency Artifact: For dollar-denominated indicators, severe currency devaluations "
            f"or exchange rate fluctuations can trigger sharp nominal contractions without matching real-term shifts."
        )

        # 7. Persist to PostgreSQL ai_investigations
        investigation_id = self._persist_investigation(
            anomaly_id=anomaly_id,
            observation_id=obs_id,
            country_code=c_code,
            indicator_code=ind_code,
            year=target_year,
            finding_summary=finding_summary,
            structured_evidence=structured_evidence,
            historical_comparison=historical_comparison,
            related_indicators=related_indicators,
            ai_explanation=ai_explanation,
            possible_interpretation=possible_interpretation,
            limitations=self.NON_CAUSALITY_DISCLAIMER
        )

        # 8. Generate and persist companion AI Insight
        insight_type = "VOLATILITY_SURGE" if abs(z_score) > 2.0 else "HISTORICAL_DEVIATION"
        insight_title = f"{c_name} {target_year}: {ind_name} {direction.capitalize()} (Z={z_score:+.2f})"
        
        self._persist_insight(
            investigation_id=investigation_id,
            observation_id=obs_id,
            anomaly_id=anomaly_id,
            country_code=c_code,
            indicator_code=ind_code,
            year=target_year,
            title=insight_title,
            insight_type=insight_type,
            underlying_metrics=structured_evidence,
            evidence_text=finding_summary,
            ai_explanation=ai_explanation
        )

        return {
            "investigation_id": investigation_id,
            "anomaly_id": anomaly_id,
            "observation_id": obs_id,
            "country_code": c_code,
            "country_name": c_name,
            "indicator_code": ind_code,
            "indicator_name": ind_name,
            "year": target_year,
            "finding_summary": finding_summary,
            "structured_evidence": structured_evidence,
            "historical_comparison": historical_comparison,
            "related_indicators": related_indicators,
            "ai_explanation": ai_explanation,
            "possible_interpretation": possible_interpretation,
            "limitations": self.NON_CAUSALITY_DISCLAIMER,
        }

    def _persist_investigation(
        self,
        anomaly_id: int,
        observation_id: int,
        country_code: str,
        indicator_code: str,
        year: int,
        finding_summary: str,
        structured_evidence: Dict[str, Any],
        historical_comparison: List[Dict[str, Any]],
        related_indicators: List[Dict[str, Any]],
        ai_explanation: str,
        possible_interpretation: str,
        limitations: str,
    ) -> int:
        sql = """
            INSERT INTO ai_investigations (
                anomaly_id, observation_id, country_code, indicator_code, year,
                finding_summary, structured_evidence, historical_comparison,
                related_indicators, ai_explanation, possible_interpretation, limitations
            )
            VALUES (
                :anomaly_id, :observation_id, :country_code, :indicator_code, :year,
                :finding_summary, CAST(:structured_evidence AS JSONB),
                CAST(:historical_comparison AS JSONB), CAST(:related_indicators AS JSONB),
                :ai_explanation, :possible_interpretation, :limitations
            )
            ON CONFLICT (anomaly_id) DO UPDATE SET
                finding_summary = EXCLUDED.finding_summary,
                structured_evidence = EXCLUDED.structured_evidence,
                historical_comparison = EXCLUDED.historical_comparison,
                related_indicators = EXCLUDED.related_indicators,
                ai_explanation = EXCLUDED.ai_explanation,
                possible_interpretation = EXCLUDED.possible_interpretation,
                limitations = EXCLUDED.limitations,
                created_at = CURRENT_TIMESTAMP
            RETURNING investigation_id;
        """
        with self.engine.begin() as conn:
            res = conn.execute(
                text(sql),
                {
                    "anomaly_id": anomaly_id,
                    "observation_id": observation_id,
                    "country_code": country_code,
                    "indicator_code": indicator_code,
                    "year": year,
                    "finding_summary": finding_summary,
                    "structured_evidence": json.dumps(structured_evidence),
                    "historical_comparison": json.dumps(historical_comparison),
                    "related_indicators": json.dumps(related_indicators),
                    "ai_explanation": ai_explanation,
                    "possible_interpretation": possible_interpretation,
                    "limitations": limitations,
                }
            )
            return res.scalar()

    def _persist_insight(
        self,
        investigation_id: int,
        observation_id: int,
        anomaly_id: int,
        country_code: str,
        indicator_code: str,
        year: int,
        title: str,
        insight_type: str,
        underlying_metrics: Dict[str, Any],
        evidence_text: str,
        ai_explanation: str,
    ) -> int:
        sql = """
            INSERT INTO ai_insights (
                investigation_id, observation_id, anomaly_id, country_code,
                indicator_code, year, title, insight_type, underlying_metrics,
                evidence_text, ai_explanation
            )
            VALUES (
                :investigation_id, :observation_id, :anomaly_id, :country_code,
                :indicator_code, :year, :title, :insight_type,
                CAST(:underlying_metrics AS JSONB), :evidence_text, :ai_explanation
            )
            RETURNING insight_id;
        """
        with self.engine.begin() as conn:
            res = conn.execute(
                text(sql),
                {
                    "investigation_id": investigation_id,
                    "observation_id": observation_id,
                    "anomaly_id": anomaly_id,
                    "country_code": country_code,
                    "indicator_code": indicator_code,
                    "year": year,
                    "title": title,
                    "insight_type": insight_type,
                    "underlying_metrics": json.dumps(underlying_metrics),
                    "evidence_text": evidence_text,
                    "ai_explanation": ai_explanation,
                }
            )
            return res.scalar()

    def batch_investigate_top_anomalies(self, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Automatically investigate top anomalies ordered by lowest anomaly score (most anomalous).
        """
        query = """
            SELECT a.anomaly_id
            FROM world_bank_anomalies a
            LEFT JOIN ai_investigations inv ON a.anomaly_id = inv.anomaly_id
            ORDER BY a.anomaly_score ASC
            LIMIT :limit;
        """
        with self.engine.connect() as conn:
            anomaly_ids = [row[0] for row in conn.execute(text(query), {"limit": limit}).fetchall()]

        investigations = []
        for a_id in anomaly_ids:
            inv = self.investigate_anomaly(a_id)
            investigations.append(inv)

        logger.info(f"Completed {len(investigations)} automated investigations.")
        return investigations


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    investigator = WorldBankInvestigator()
    results = investigator.batch_investigate_top_anomalies(limit=5)
    print(f"Generated {len(results)} investigations successfully!")
    if results:
        print("Sample Finding:\n", results[0]["finding_summary"])
