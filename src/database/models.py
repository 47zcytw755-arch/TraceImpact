"""
SQLAlchemy ORM Data Models for TraceImpact.

Concepts:
- Base: The declarative base class that maps Python classes to PostgreSQL relational tables.
- Column, Integer, String, Date, Numeric: Map Python attributes to SQL data types.
- ForeignKey: Enforces referential integrity at the database layer.
- relationship: Provides high-level Python navigation between related rows (e.g. file.records).
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database.connection import Base


class SourceFile(Base):
    """
    Tracks metadata of raw input files (CSV/Excel).
    Primary Key: file_id (auto-incrementing serial)
    """
    __tablename__ = "source_files"

    file_id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, unique=True)
    total_rows = Column(Integer, nullable=False, default=0)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    records = relationship("SourceRecord", back_populates="source_file", cascade="all, delete-orphan")
    dq_issues = relationship("DataQualityIssue", back_populates="source_file", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SourceFile(id={self.file_id}, name='{self.file_name}', rows={self.total_rows})>"


class SourceRecord(Base):
    """
    Immutable raw staging record. Stores verbatim JSON representation of source CSV row.
    Acts as the source anchor for every cleaned record.
    """
    __tablename__ = "source_records"

    record_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("source_files.file_id", ondelete="CASCADE"), nullable=False)
    row_index = Column(Integer, nullable=False)
    raw_data = Column(JSONB, nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source_file = relationship("SourceFile", back_populates="records")
    dq_issues = relationship("DataQualityIssue", back_populates="source_record")

    __table_args__ = (
        Index("idx_source_records_file", "file_id", "row_index"),
    )

    def __repr__(self):
        return f"<SourceRecord(id={self.record_id}, file_id={self.file_id}, row={self.row_index})>"


class DataQualityIssue(Base):
    """
    Audit log of all detected anomalies and transformation reasons.
    """
    __tablename__ = "data_quality_issues"

    issue_id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("source_files.file_id", ondelete="CASCADE"), nullable=True)
    record_id = Column(Integer, ForeignKey("source_records.record_id", ondelete="SET NULL"), nullable=True)
    row_number = Column(Integer, nullable=True)
    column_name = Column(String(100), nullable=True)
    issue_type = Column(String(50), nullable=False)  # DUPLICATE_RECORD, MISSING_VALUE, etc.
    severity = Column(String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    raw_value = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="OPEN")  # OPEN, RESOLVED, ACCEPTED
    program_id = Column(String(50), ForeignKey("programs.program_id", ondelete="SET NULL"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source_file = relationship("SourceFile", back_populates="dq_issues")
    source_record = relationship("SourceRecord", back_populates="dq_issues")
    program = relationship("Program", backref="dq_issues")


class Program(Base):
    """
    Normalized core table: Community initiatives and programs.
    """
    __tablename__ = "programs"

    program_id = Column(String(50), primary_key=True)
    source_record_id = Column(Integer, ForeignKey("source_records.record_id", ondelete="SET NULL"), nullable=True)
    program_name = Column(String(255), nullable=False)
    target_category = Column(String(100), nullable=True)
    budget_allocated = Column(Numeric(12, 2), default=0.00)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    attendance_records = relationship("Attendance", back_populates="program")
    expenses = relationship("Expense", back_populates="program")
    outcomes = relationship("Outcome", back_populates="program")


class Beneficiary(Base):
    """
    Normalized core table: Community participants with anonymized privacy code.
    """
    __tablename__ = "beneficiaries"

    beneficiary_id = Column(String(50), primary_key=True)
    source_record_id = Column(Integer, ForeignKey("source_records.record_id", ondelete="SET NULL"), nullable=True)
    anonymized_code = Column(String(64), unique=True, nullable=True)
    gender = Column(String(20), nullable=True)
    age = Column(Integer, nullable=True)
    city_location = Column(String(100), nullable=True)
    registration_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    attendance_records = relationship("Attendance", back_populates="beneficiary")
    outcomes = relationship("Outcome", back_populates="beneficiary")


class Attendance(Base):
    """
    Normalized fact table: Program session attendance logs.
    """
    __tablename__ = "attendance"

    attendance_id = Column(String(50), primary_key=True)
    source_record_id = Column(Integer, ForeignKey("source_records.record_id", ondelete="SET NULL"), nullable=True)
    beneficiary_id = Column(String(50), ForeignKey("beneficiaries.beneficiary_id", ondelete="CASCADE"), nullable=True)
    program_id = Column(String(50), ForeignKey("programs.program_id", ondelete="CASCADE"), nullable=True)
    session_date = Column(Date, nullable=False)
    attendance_status = Column(String(50), default="Present")
    session_hours = Column(Numeric(4, 2), default=0.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    beneficiary = relationship("Beneficiary", back_populates="attendance_records")
    program = relationship("Program", back_populates="attendance_records")


class Expense(Base):
    """
    Normalized fact table: Financial expenditures incurred by programs.
    """
    __tablename__ = "expenses"

    expense_id = Column(String(50), primary_key=True)
    source_record_id = Column(Integer, ForeignKey("source_records.record_id", ondelete="SET NULL"), nullable=True)
    program_id = Column(String(50), ForeignKey("programs.program_id", ondelete="CASCADE"), nullable=True)
    expense_category = Column(String(100), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    incurred_date = Column(Date, nullable=False)
    receipt_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    program = relationship("Program", back_populates="expenses")


class Outcome(Base):
    """
    Normalized fact table: Baseline vs exit score evaluations.
    """
    __tablename__ = "outcomes"

    outcome_id = Column(String(50), primary_key=True)
    source_record_id = Column(Integer, ForeignKey("source_records.record_id", ondelete="SET NULL"), nullable=True)
    beneficiary_id = Column(String(50), ForeignKey("beneficiaries.beneficiary_id", ondelete="CASCADE"), nullable=True)
    program_id = Column(String(50), ForeignKey("programs.program_id", ondelete="CASCADE"), nullable=True)
    indicator_name = Column(String(255), nullable=False)
    baseline_score = Column(Numeric(5, 2), nullable=True)
    exit_score = Column(Numeric(5, 2), nullable=True)
    evaluation_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    beneficiary = relationship("Beneficiary", back_populates="outcomes")
    program = relationship("Program", back_populates="outcomes")
