# FILE 3 of 12 | model/Employee_Management/org_hierarchy.py
# Model: Department — org hierarchy with nested departments
# Table: departments

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from core.database import Base
from datetime import datetime


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=True)
    parent_department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    head_employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
