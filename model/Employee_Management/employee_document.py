# model/Employee_Management/employee_document.py
# Table: employee_documents
# Matches: Document Vault & Management UI
# Fields cover: category, version, expiry_date, status (Approved/Pending/Rejected),
#               file_size, file_format, is_mandatory, checklist flags

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean,
    Text, ForeignKey, Date, Numeric
)
from core.database import Base
from datetime import datetime


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True)

    # ── Core ownership ──────────────────────────────────────────────
    employee_id   = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # ── Document identity ───────────────────────────────────────────
    document_name = Column(String(255), nullable=False)                 # "Aadhaar Card"
    document_type = Column(String(100), nullable=False)                 # "Aadhaar / PAN / Passport / …"

    # ── Category (shown as coloured badge in UI) ────────────────────
    # KYC | Educational | Employment | Medical | Legal | Other
    category      = Column(String(50), nullable=False, server_default="Other")

    # ── Mandatory flag (red "Mandatory" badge) ──────────────────────
    is_mandatory  = Column(Boolean, nullable=False, default=False)

    # ── File metadata ───────────────────────────────────────────────
    file_path     = Column(String(500), nullable=False)
    file_format   = Column(String(20),  nullable=True)    # PDF / DOCX / JPG …
    file_size_mb  = Column(Numeric(6, 2), nullable=True)  # e.g. 2.4

    # ── Versioning ──────────────────────────────────────────────────
    version       = Column(String(20), nullable=False, server_default="v1.0")  # v1.0, v2.1 …
    version_notes = Column(Text, nullable=True)

    # ── Dates ───────────────────────────────────────────────────────
    upload_date   = Column(Date, nullable=True)           # "Upload Date" column
    expiry_date   = Column(Date, nullable=True)           # NULL → "No Expiry"
    uploaded_at   = Column(DateTime, default=datetime.utcnow)

    # ── Approval / Status workflow ──────────────────────────────────
    # PENDING | APPROVED | REJECTED
    status        = Column(String(30), nullable=False, server_default="PENDING")
    reviewed_by   = Column(Integer, ForeignKey("employees.id"), nullable=True)
    reviewed_at   = Column(DateTime, nullable=True)
    review_notes  = Column(Text, nullable=True)

    # ── Legacy verify flag (kept for backward compat) ───────────────
    is_verified   = Column(Boolean, default=False)
    verified_by   = Column(String(255), nullable=True)

    # ── Soft notes ──────────────────────────────────────────────────
    notes         = Column(Text, nullable=True)

    # ── Timestamps ──────────────────────────────────────────────────
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
