# FILE 2 of 12 | model/Employee_Management/employee_document.py
# Model: EmployeeDocument — document vault
# Table: employee_documents

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from core.database import Base
from datetime import datetime


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    document_type = Column(String(100), nullable=False)  # Aadhaar/PAN/Passport/Offer Letter/Relieving Letter/Payslip/Other
    document_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_verified = Column(Boolean, default=False)
    verified_by = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
