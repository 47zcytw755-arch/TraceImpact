"""
Raw Data Ingestion and Source Metadata Staging.

Concepts:
- Pandas DataFrame (`df`): A two-dimensional, size-mutable, tabular data structure in memory.
  `pd.read_csv(...)` parses the CSV bytes into memory, handling delimiters and headers.
- SHA-256 Hashing: A cryptographic hash computed on file bytes. If even one character in a raw file changes,
  the hash changes completely. This guarantees immutability tracking in data engineering pipelines.
- JSONB Staging (`source_records`): PostgreSQL's binary JSON format. By storing the unparsed dictionary
  of each raw CSV row into JSONB, we preserve 100% of the original inputs without schema loss or destructive truncation.
"""

import hashlib
import logging
from pathlib import Path
import pandas as pd
from sqlalchemy.orm import Session
from src.config import DATA_RAW_DIR
from src.database.connection import SessionLocal
from src.database.models import SourceFile, SourceRecord, Program

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def compute_file_hash(file_path: Path) -> str:
    """Computes SHA-256 hash of a file to guarantee data immutability and provenance."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def ingest_raw_csv_files(db: Session):
    """
    Ingests all raw CSV files into `source_files` and `source_records` staging tables.
    """
    raw_files = sorted(list(DATA_RAW_DIR.glob("*.csv")))
    if not raw_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_RAW_DIR}")

    logger.info("Found %d raw CSV files in %s for ingestion.", len(raw_files), DATA_RAW_DIR)

    total_ingested_records = 0

    for file_path in raw_files:
        file_name = file_path.name
        file_hash = compute_file_hash(file_path)

        # 1. Read CSV into Pandas DataFrame
        # df acts as a structured in-memory table
        df = pd.read_csv(file_path, dtype=str)  # Read all as strings to avoid premature type casting/corruption
        row_count = len(df)

        logger.info("--> Processing '%s' (%d rows, hash: %s...)", file_name, row_count, file_hash[:12])

        # 2. Check if this file hash was already ingested
        existing_file = db.query(SourceFile).filter(SourceFile.file_hash == file_hash).first()
        if existing_file:
            logger.info("    File '%s' already staged (file_id=%d). Updating existing record count.", file_name, existing_file.file_id)
            source_file_entry = existing_file
            # Remove previous staged records for clean idempotency
            db.query(SourceRecord).filter(SourceRecord.file_id == existing_file.file_id).delete()
        else:
            source_file_entry = SourceFile(
                file_name=file_name,
                file_hash=file_hash,
                total_rows=row_count
            )
            db.add(source_file_entry)
            db.flush()  # Flushes to get generated auto-increment file_id without committing transaction yet

        # 3. Convert DataFrame rows into clean JSON-serializable dictionaries
        # Any missing / NaN value becomes Python None (which maps to SQL NULL / JSON null)
        source_record_objects = []
        for idx, row in enumerate(df.itertuples(index=False), start=1):
            row_dict = {
                col: (None if (pd.isna(val) or val == "nan") else str(val).strip())
                for col, val in zip(df.columns, row)
            }
            source_rec = SourceRecord(
                file_id=source_file_entry.file_id,
                row_index=idx,
                raw_data=row_dict
            )
            source_record_objects.append(source_rec)

        # Insert staged records
        db.add_all(source_record_objects)
        db.commit()
        total_ingested_records += len(source_record_objects)
        logger.info("    Successfully staged %d records for '%s' (file_id=%d).", len(source_record_objects), file_name, source_file_entry.file_id)

    # 4. For Day 1 baseline, populate master programs catalog if empty
    # This establishes foundational foreign key targets for upcoming day milestones
    programs_file = db.query(SourceFile).filter(SourceFile.file_name == "programs.csv").first()
    if programs_file:
        existing_programs = db.query(Program).count()
        if existing_programs == 0:
            program_records = db.query(SourceRecord).filter(SourceRecord.file_id == programs_file.file_id).all()
            for rec in program_records:
                data = rec.raw_data
                prog = Program(
                    program_id=data.get("program_id"),
                    source_record_id=rec.record_id,
                    program_name=data.get("program_name"),
                    target_category=data.get("target_category"),
                    budget_allocated=float(data.get("budget_allocated", 0.0)),
                    start_date=data.get("start_date"),
                    end_date=data.get("end_date")
                )
                db.add(prog)
            db.commit()
            logger.info("Loaded %d master programs into core 'programs' table.", len(program_records))

    logger.info("Raw Ingestion Complete! Total %d records staged in PostgreSQL with full lineage metadata.", total_ingested_records)


def run_ingestion():
    db = SessionLocal()
    try:
        ingest_raw_csv_files(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_ingestion()
