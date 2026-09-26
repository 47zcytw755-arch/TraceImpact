"""
Day 1 Verification Script for TraceImpact.

Performs end-to-end health and consistency checks on:
1. PostgreSQL database connectivity.
2. Table schema existence in PostgreSQL information schema.
3. Immutability validation: raw CSV file existence and hash matching.
4. Record staging counts in `source_files` and `source_records`.
5. Traceability drilldown proof (source_records -> source_files).
"""

import sys
import logging
from sqlalchemy import text
from src.database.connection import SessionLocal, test_connection
from src.database.models import SourceFile, SourceRecord, Program
from src.config import DATA_RAW_DIR
from src.ingestion.ingest_raw import compute_file_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_verification() -> bool:
    print("=" * 70)
    print(" TRACEIMPACT — DAY 1 VERIFICATION & HEALTH CHECK")
    print("=" * 70)

    # 1. Connection Check
    print("\n[1/5] Testing PostgreSQL Connection...")
    if not test_connection():
        print("❌ FAIL: Could not connect to PostgreSQL database.")
        return False
    print("✅ PASS: PostgreSQL connection established.")

    db = SessionLocal()
    try:
        # 2. Schema / Table Existence Check
        print("\n[2/5] Checking Database Tables...")
        expected_tables = [
            "source_files",
            "source_records",
            "data_quality_issues",
            "programs",
            "beneficiaries",
            "attendance",
            "expenses",
            "outcomes"
        ]
        
        with db.bind.connect() as conn:
            query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            existing_tables = [r[0] for r in conn.execute(query).fetchall()]

        missing_tables = [t for t in expected_tables if t not in existing_tables]
        if missing_tables:
            print(f"❌ FAIL: Missing tables in PostgreSQL: {missing_tables}")
            return False
        print(f"✅ PASS: All {len(expected_tables)} required tables exist in database:")
        for t in expected_tables:
            print(f"       • {t}")

        # 3. Raw Files & Immutability / Hash Verification
        print("\n[3/5] Verifying Raw Files & Immutability Hashes...")
        raw_files = sorted(list(DATA_RAW_DIR.glob("*.csv")))
        if len(raw_files) != 5:
            print(f"❌ FAIL: Expected 5 CSV files in data/raw/, found {len(raw_files)}")
            return False
        
        for fpath in raw_files:
            computed_hash = compute_file_hash(fpath)
            db_file = db.query(SourceFile).filter(SourceFile.file_name == fpath.name).first()
            if not db_file:
                print(f"❌ FAIL: File '{fpath.name}' not registered in source_files table.")
                return False
            if db_file.file_hash != computed_hash:
                print(f"❌ FAIL: File '{fpath.name}' hash mismatch! Raw file has been altered.")
                return False
            print(f"✅ PASS: '{fpath.name}' verified (Hash: {computed_hash[:16]}..., Staged Rows: {db_file.total_rows})")

        # 4. Staging Record Integrity Check
        print("\n[4/5] Verifying Staged Records Count...")
        total_source_records = db.query(SourceRecord).count()
        total_expected_records = sum(f.total_rows for f in db.query(SourceFile).all())
        
        if total_source_records != total_expected_records:
            print(f"❌ FAIL: Expected {total_expected_records} staged records, found {total_source_records}")
            return False
        print(f"✅ PASS: Staging table contains {total_source_records} records with full JSONB payloads.")

        # 5. Traceability Drilldown Proof
        print("\n[5/5] Demonstrating Lineage Traceback Proof...")
        sample_record = db.query(SourceRecord).first()
        if sample_record:
            source_file = sample_record.source_file
            print(f"       • Sample Record ID : {sample_record.record_id}")
            print(f"       • Origin File      : {source_file.file_name} (File ID: {source_file.file_id})")
            print(f"       • Source Row Index : Row #{sample_record.row_index}")
            print(f"       • Staged Raw JSON  : {sample_record.raw_data}")
            print("✅ PASS: Traceability link intact from database record -> source file & row index.")

        print("\n" + "=" * 70)
        print("🎉 ALL DAY 1 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 70)
        return True

    finally:
        db.close()


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
