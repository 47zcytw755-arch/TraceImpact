"""
Ingestion Metadata and Provenance Logging for External APIs.
Tracks runs, endpoints, parameters, row counts, and error states.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import text
from src.database.connection import engine

logger = logging.getLogger(__name__)


def create_ingestion_run(
    source_name: str,
    endpoint_url: str,
    request_params: Dict[str, Any],
    run_type: str = "SCHEDULED",
) -> int:
    """
    Initializes a new API ingestion run record in api_ingestion_runs.
    Returns: run_id
    """
    sql = text("""
        INSERT INTO api_ingestion_runs (
            source_name, endpoint_url, request_params, run_type, status, started_at
        ) VALUES (
            :source_name, :endpoint_url, :params, :run_type, 'STARTED', CURRENT_TIMESTAMP
        ) RETURNING run_id;
    """)
    with engine.begin() as conn:
        run_id = conn.execute(sql, {
            "source_name": source_name,
            "endpoint_url": endpoint_url,
            "params": json.dumps(request_params),
            "run_type": run_type,
        }).scalar()

    logger.info("Created API Ingestion Run #%d (%s) for %s", run_id, run_type, source_name)
    return run_id


def record_raw_response(
    run_id: int,
    source_name: str,
    endpoint_url: str,
    page_number: int,
    per_page: int,
    response_hash: str,
    raw_payload: Any,
    record_count: int,
) -> int:
    """
    Persists immutable raw bronze response payload and SHA-256 hash.
    Returns: response_id
    """
    sql = text("""
        INSERT INTO api_raw_responses (
            run_id, source_name, endpoint_url, page_number, per_page,
            response_hash, raw_payload, record_count, ingested_at
        ) VALUES (
            :run_id, :source_name, :endpoint_url, :page_number, :per_page,
            :response_hash, :payload, :record_count, CURRENT_TIMESTAMP
        ) RETURNING response_id;
    """)
    with engine.begin() as conn:
        resp_id = conn.execute(sql, {
            "run_id": run_id,
            "source_name": source_name,
            "endpoint_url": endpoint_url,
            "page_number": page_number,
            "per_page": per_page,
            "response_hash": response_hash,
            "payload": json.dumps(raw_payload),
            "record_count": record_count,
        }).scalar()

    return resp_id


def complete_ingestion_run(
    run_id: int,
    total_pages: int,
    total_records: int,
    records_inserted: int,
    records_quarantined: int,
    records_updated: int = 0,
    duration_seconds: Optional[float] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Marks an API ingestion run as COMPLETED or FAILED with final execution tallies.
    """
    status = "FAILED" if error_message else "COMPLETED"
    sql = text("""
        UPDATE api_ingestion_runs
        SET
            status = :status,
            total_pages = :total_pages,
            total_records = :total_records,
            records_inserted = :records_inserted,
            records_quarantined = :records_quarantined,
            records_updated = :records_updated,
            duration_seconds = :duration_seconds,
            completed_at = CURRENT_TIMESTAMP,
            error_message = :error_message
        WHERE run_id = :run_id;
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "status": status,
            "total_pages": total_pages,
            "total_records": total_records,
            "records_inserted": records_inserted,
            "records_quarantined": records_quarantined,
            "records_updated": records_updated,
            "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
            "error_message": error_message,
            "run_id": run_id,
        })

    logger.info(
        "Run #%d finalized: status=%s, pages=%d, records=%d, inserted=%d, updated=%d, quarantined=%d, duration=%.2fs",
        run_id, status, total_pages, total_records, records_inserted, records_updated, records_quarantined,
        duration_seconds or 0.0
    )
