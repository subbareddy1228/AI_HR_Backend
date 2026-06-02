# model/HRMS/employee_reports.py

import enum
from datetime import date, datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Enum as SAEnum
from core.database import Base


class EmploymentTypeEnum(str, enum.Enum):
    permanent = "Permanent"
    contract = "Contract"
    intern = "Intern"


class EmployeeStatusEnum(str, enum.Enum):
    active = "Active"
    on_notice = "On Notice"
    resigned = "Resigned"
    terminated = "Terminated"


class MovementTypeEnum(str, enum.Enum):
    promotion = "Promotion"
    transfer = "Transfer"
    designation_change = "Designation Change"
    department_change = "Department Change"
    inter_location_transfer = "Inter-location Transfer"


class HREmployee(Base):
    """
    Core HRMS Employee table.
    Links to existing Employee (onboarding) via employee_code.
    """
    __tablename__ = "hrms_employees"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    employee_code = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=False)
    official_email = Column(String(255), nullable=True)
    mobile_number = Column(String(15), nullable=True)

    # Org structure
    department = Column(String(100), nullable=True, index=True)
    designation = Column(String(100), nullable=True)
    grade = Column(String(20), nullable=True, index=True)
    location = Column(String(100), nullable=True, index=True)
    business_unit = Column(String(100), nullable=True)

    # Employment
    employment_type = Column(
        SAEnum(EmploymentTypeEnum, name="employment_type_enum"),
        default=EmploymentTypeEnum.permanent,
        nullable=False
    )
    status = Column(
        SAEnum(EmployeeStatusEnum, name="employee_status_enum"),
        default=EmployeeStatusEnum.active,
        index=True
    )

    # Demographics
    gender = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)

    # Dates
    joining_date = Column(Date, nullable=False)
    confirmation_date = Column(Date, nullable=True)
    resignation_date = Column(Date, nullable=True)
    last_working_date = Column(Date, nullable=True)

    # Salary
    current_salary = Column(Float, nullable=True)

    # Manager link
    manager_id = Column(Integer, ForeignKey("hrms_employees.id"), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmployeeMovement(Base):
    """
    Tracks promotions, transfers, designation/department changes.
    """
    __tablename__ = "hrms_employee_movements"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("hrms_employees.id"), nullable=False, index=True)
    employee_code = Column(String(50), nullable=False)
    employee_name = Column(String(200), nullable=False)

    movement_type = Column(
        SAEnum(MovementTypeEnum, name="movement_type_enum"),
        nullable=False,
        index=True
    )

    # From → To fields (populated based on movement_type)
    from_value = Column(String(200), nullable=True)   # from designation / department / location
    to_value = Column(String(200), nullable=True)     # to designation / department / location
    department = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)

    # Salary impact
    old_salary = Column(Float, nullable=True)
    new_salary = Column(Float, nullable=True)
    salary_change_pct = Column(Float, nullable=True)  # e.g. 15.0 means +15%

    movement_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=False)

    remarks = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
