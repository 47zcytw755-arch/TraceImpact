"""
World Bank Public Indicators Ingestion Pipeline.
Handles paginated API retrieval, raw bronze response storage, data quality validation,
dimension table population, and idempotent PostgreSQL upserts.
"""

import argparse
import logging
import sys
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from src.database.connection import engine
from src.ingestion.api_client import APIClient
from src.ingestion.ingestion_metadata import (
    create_ingestion_run,
    record_raw_response,
    complete_ingestion_run,
)
from src.quality.world_bank_quality import WorldBankValidator, persist_dq_issues

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Curated global development indicators
CURATED_INDICATORS = {
    "NY.GDP.PCAP.CD": {
        "name": "GDP per capita (current US$)",
        "topic": "Economic Policy & Debt",
        "description": "GDP per capita is gross domestic product divided by midyear population.",
        "unit": "current US$",
    },
    "SP.POP.TOTL": {
        "name": "Population, total",
        "topic": "Health: Population",
        "description": "Total population is based on the de facto definition of population.",
        "unit": "people",
    },
    "SP.DYN.LE00.IN": {
        "name": "Life expectancy at birth, total (years)",
        "topic": "Health",
        "description": "Life expectancy at birth indicates the number of years a newborn infant would live.",
        "unit": "years",
    },
    "SH.H2O.BASW.ZS": {
        "name": "People using at least basic drinking water services (% of population)",
        "topic": "Environment: Water and sanitation",
        "description": "The percentage of people using at least basic water services.",
        "unit": "% of population",
    },
}


class WorldBankIngester:
    """
    Orchestrates the complete World Bank API ingestion pipeline:
    API -> Raw Bronze Staging (JSONB + SHA-256) -> DQ Validation -> Silver PostgreSQL (Upserts).
    """

    BASE_URL = "http://api.worldbank.org/v2"

    def __init__(self, per_page: int = 500, timeout: int = 30):
        self.api_client = APIClient(base_url=self.BASE_URL, timeout=timeout)
        self.per_page = per_page

    def seed_indicators(self) -> None:
        """Seeds curated indicator definitions into world_bank_indicators."""
        sql = text("""
            INSERT INTO world_bank_indicators (
                indicator_code, indicator_name, topic, description, unit_of_measure, source_organization
            ) VALUES (
                :code, :name, :topic, :desc, :unit, 'World Bank World Development Indicators'
            ) ON CONFLICT (indicator_code) DO UPDATE
            SET indicator_name = EXCLUDED.indicator_name,
                topic = EXCLUDED.topic,
                description = EXCLUDED.description,
                unit_of_measure = EXCLUDED.unit_of_measure;
        """)
        with engine.begin() as conn:
            for code, meta in CURATED_INDICATORS.items():
                conn.execute(sql, {
                    "code": code,
                    "name": meta["name"],
                    "topic": meta["topic"],
                    "desc": meta["description"],
                    "unit": meta["unit"],
                })
        logger.info("Seeded %d curated indicator definitions.", len(CURATED_INDICATORS))

    def upsert_country(self, conn, country_code: str, country_name: str, iso3_code: Optional[str] = None) -> None:
        """Idempotently inserts or updates country dimension records."""
        sql = text("""
            INSERT INTO world_bank_countries (
                country_code, country_name, iso3_code, updated_at
            ) VALUES (
                :code, :name, :iso3, CURRENT_TIMESTAMP
            ) ON CONFLICT (country_code) DO UPDATE
            SET country_name = EXCLUDED.country_name,
                iso3_code = COALESCE(EXCLUDED.iso3_code, world_bank_countries.iso3_code),
                updated_at = CURRENT_TIMESTAMP;
        """)
        conn.execute(sql, {
            "code": country_code,
            "name": country_name or country_code,
            "iso3": iso3_code,
        })

    def ingest_indicator(
        self,
        indicator_code: str,
        start_year: int = 2016,
        end_year: int = 2022,
        max_pages: Optional[int] = None,
        run_type: str = "SCHEDULED",
    ) -> Dict[str, Any]:
        """
        Fetches and ingests all pages for a given indicator across countries.
        """
        start_time = time.time()
        endpoint = f"country/all/indicator/{indicator_code}"
        params = {
            "date": f"{start_year}:{end_year}",
            "format": "json",
            "per_page": self.per_page,
            "page": 1,
        }

        run_id = create_ingestion_run(
            source_name="world_bank",
            endpoint_url=f"{self.BASE_URL}/{endpoint}",
            request_params=params,
            run_type=run_type,
        )

        total_pages_fetched = 0
        total_raw_records = 0
        total_inserted = 0
        total_updated = 0
        total_quarantined = 0
        current_page = 1
        total_pages = 1

        try:
            while current_page <= total_pages:
                if max_pages and current_page > max_pages:
                    logger.info("Reached max_pages limit (%d). Stopping pagination.", max_pages)
                    break

                page_params = dict(params, page=current_page)
                status_code, raw_bytes, parsed_json, resp_hash = self.api_client.get(
                    endpoint=endpoint,
                    params=page_params,
                )

                if status_code != 200 or not isinstance(parsed_json, list) or len(parsed_json) < 2:
                    raise RuntimeError(f"Unexpected response structure on page {current_page}: HTTP {status_code}")

                # World Bank returns metadata in parsed_json[0], records in parsed_json[1]
                meta = parsed_json[0]
                records = parsed_json[1]

                total_pages = meta.get("pages", 1)
                page_record_count = len(records)
                total_pages_fetched += 1
                total_raw_records += page_record_count

                # Step 1: Store Bronze Layer Immutable Raw Response
                resp_id = record_raw_response(
                    run_id=run_id,
                    source_name="world_bank",
                    endpoint_url=f"{self.BASE_URL}/{endpoint}",
                    page_number=current_page,
                    per_page=self.per_page,
                    response_hash=resp_hash,
                    raw_payload=parsed_json,
                    record_count=page_record_count,
                )

                # Step 2: Validate, Clean & Persist Observations
                page_issues = []
                valid_observations = []

                for idx, raw_rec in enumerate(records):
                    is_valid, issues, cleaned = WorldBankValidator.validate_observation(raw_rec)
                    if issues:
                        page_issues.extend(issues)

                    if is_valid:
                        valid_observations.append({
                            "cleaned": cleaned,
                            "raw_index": idx,
                        })
                    else:
                        total_quarantined += 1

                # Persist Data Quality issues for this page
                persist_dq_issues(run_id=run_id, raw_response_id=resp_id, issues=page_issues)

                # Step 3: Upsert Cleaned Observations into Silver Layer (PostgreSQL)
                if valid_observations:
                    with engine.begin() as conn:
                        # Ensure countries exist in dimension table
                        for item in valid_observations:
                            c = item["cleaned"]
                            self.upsert_country(
                                conn=conn,
                                country_code=c["country_code"],
                                country_name=c["country_name"],
                                iso3_code=c["iso3_code"],
                            )

                        # Check how many of these (country, indicator, year) combinations already exist
                        existing_count = 0
                        tuples_str = ", ".join(f"('{item['cleaned']['country_code']}', '{item['cleaned']['indicator_code']}', {item['cleaned']['year']})" for item in valid_observations)
                        check_sql = text(f"SELECT count(*) FROM world_bank_observations WHERE (country_code, indicator_code, year) IN ({tuples_str});")
                        existing_count = conn.execute(check_sql).scalar() or 0

                        # Idempotent observation upsert
                        obs_sql = text("""
                            INSERT INTO world_bank_observations (
                                country_code, indicator_code, year, indicator_value,
                                decimal_places, obs_status, unit, raw_response_id, raw_record_index
                            ) VALUES (
                                :country_code, :indicator_code, :year, :indicator_value,
                                :decimal_places, :obs_status, :unit, :raw_response_id, :raw_record_index
                            ) ON CONFLICT (country_code, indicator_code, year) DO UPDATE
                            SET indicator_value = EXCLUDED.indicator_value,
                                raw_response_id = EXCLUDED.raw_response_id,
                                raw_record_index = EXCLUDED.raw_record_index;
                        """)

                        obs_params = [
                            {
                                "country_code": item["cleaned"]["country_code"],
                                "indicator_code": item["cleaned"]["indicator_code"],
                                "year": item["cleaned"]["year"],
                                "indicator_value": item["cleaned"]["indicator_value"],
                                "decimal_places": item["cleaned"]["decimal_places"],
                                "obs_status": item["cleaned"]["obs_status"],
                                "unit": item["cleaned"]["unit"],
                                "raw_response_id": resp_id,
                                "raw_record_index": item["raw_index"],
                            }
                            for item in valid_observations
                        ]
                        conn.execute(obs_sql, obs_params)
                        inserted_count = len(valid_observations) - existing_count
                        updated_count = existing_count
                        total_inserted += inserted_count
                        total_updated += updated_count

                logger.info(
                    "Page %d/%d processed: %d raw, %d valid, %d issues",
                    current_page, total_pages, page_record_count, len(valid_observations), len(page_issues)
                )

                current_page += 1

            duration = time.time() - start_time
            complete_ingestion_run(
                run_id=run_id,
                total_pages=total_pages_fetched,
                total_records=total_raw_records,
                records_inserted=total_inserted,
                records_quarantined=total_quarantined,
                records_updated=total_updated,
                duration_seconds=duration,
            )

            return {
                "run_id": run_id,
                "status": "COMPLETED",
                "pages": total_pages_fetched,
                "total_records": total_raw_records,
                "inserted": total_inserted,
                "updated": total_updated,
                "quarantined": total_quarantined,
                "duration_seconds": round(duration, 2),
            }

        except Exception as e:
            duration = time.time() - start_time
            logger.error("API Ingestion Run #%d failed: %s", run_id, e)
            complete_ingestion_run(
                run_id=run_id,
                total_pages=total_pages_fetched,
                total_records=total_raw_records,
                records_inserted=total_inserted,
                records_quarantined=total_quarantined,
                records_updated=total_updated,
                duration_seconds=duration,
                error_message=str(e),
            )
            raise


def run_pipeline(
    indicators: Optional[List[str]] = None,
    start_year: int = 2018,
    end_year: int = 2021,
    max_pages: Optional[int] = None,
    run_type: str = "SCHEDULED",
) -> Dict[str, Any]:
    """
    CLI/Module entry point for executing the World Bank ingestion pipeline.
    """
    indicators = indicators or list(CURATED_INDICATORS.keys())
    ingester = WorldBankIngester()
    ingester.seed_indicators()

    start_time = time.time()
    results = {}
    total_obs_inserted = 0
    total_obs_updated = 0

    logger.info("Starting World Bank Ingestion for %d indicators (%d-%d, type=%s)...", len(indicators), start_year, end_year, run_type)
    for ind in indicators:
        logger.info(">>> Processing Indicator: %s", ind)
        res = ingester.ingest_indicator(
            indicator_code=ind,
            start_year=start_year,
            end_year=end_year,
            max_pages=max_pages,
            run_type=run_type,
        )
        results[ind] = res
        total_obs_inserted += res["inserted"]
        total_obs_updated += res["updated"]

    # 11. Run ML Anomaly Detection & 12. Generate AI Investigation Candidates
    ml_results = None
    ai_investigations_count = 0
    try:
        from src.ml.anomaly_detector import WorldBankAnomalyDetector
        from src.ai.investigator import WorldBankInvestigator
        detector = WorldBankAnomalyDetector()
        ml_results = detector.detect_and_persist_anomalies()
        logger.info("Automated ML Anomaly Detection executed: %s", ml_results)

        investigator = WorldBankInvestigator()
        inv_results = investigator.batch_investigate_top_anomalies(limit=5)
        ai_investigations_count = len(inv_results)
        logger.info("Automated AI Investigation: %d investigations generated/updated.", ai_investigations_count)
    except Exception as e:
        logger.warning("Post-ingestion ML/AI pipeline encountered non-fatal error: %s", e)

    duration = time.time() - start_time
    logger.info(
        "World Bank Ingestion Complete! Inserted %d, Updated %d observations across %d indicators in %.2fs (%.1f rec/s).",
        total_obs_inserted, total_obs_updated, len(indicators), duration, (total_obs_inserted + total_obs_updated) / max(duration, 0.001)
    )

    return {
        "duration_seconds": round(duration, 2),
        "total_inserted": total_obs_inserted,
        "total_updated": total_obs_updated,
        "indicators": results,
        "ml_anomaly_detection": ml_results,
        "ai_investigations_generated": ai_investigations_count,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TraceImpact 2.0 World Bank Public Data Ingestion Pipeline")
    parser.add_argument("--indicators", nargs="+", default=None, help="Specific indicator codes to ingest")
    parser.add_argument("--start-year", type=int, default=2016, help="Earliest reporting year (default: 2016)")
    parser.add_argument("--end-year", type=int, default=2022, help="Latest reporting year (default: 2022)")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum pages per indicator (for fast test)")
    args = parser.parse_args()

    run_pipeline(
        indicators=args.indicators,
        start_year=args.start_year,
        end_year=args.end_year,
        max_pages=args.max_pages,
    )
