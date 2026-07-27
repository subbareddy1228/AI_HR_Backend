import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from model.onboarding.employee import Employee
from schema.onboarding.employee import EmployeeCreate


def _generate_code() -> str:
    return f"EMP-{uuid.uuid4().hex[:8].upper()}"


def create_employee(db: Session, payload: EmployeeCreate) -> Employee:

    if payload.reporting_manager_id is not None:
        result = db.execute(
            select(Employee).where(Employee.id == payload.reporting_manager_id)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reporting manager with id {payload.reporting_manager_id} not found.",
            )

    code = payload.employee_code or _generate_code()

    employee = Employee(
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        joining_date=payload.joining_date,
        confirmation_date=payload.confirmation_date,
        gender=payload.gender,
        employee_code=code,
        biometric_code=payload.biometric_code,
        mobile_number=payload.mobile_number,
        personal_email=str(payload.personal_email) if payload.personal_email else None,
        official_email=str(payload.official_email) if payload.official_email else None,
        designation=payload.designation,
        department=payload.department,
        business_unit=payload.business_unit,
        location=payload.location,
        grade=payload.grade,
        cost_center=payload.cost_center,
        reporting_manager_id=payload.reporting_manager_id,
        shift_policy=payload.shift_policy,
        week_off_policy=payload.week_off_policy,
        overtime_policy=payload.overtime_policy,
        send_mobile_login=payload.send_mobile_login,
        send_web_login=payload.send_web_login,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(employee)

    for attempt in range(2):
        try:
            db.commit()
            break
        except IntegrityError as exc:
            db.rollback()
            msg = str(exc).lower()

            if "mobile_number" in msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An employee with this mobile number already exists.",
                )
            if "employee_code" in msg:
                if attempt == 0 and not payload.employee_code:
                    # Regenerate and retry once
                    employee.employee_code = _generate_code()
                    db.add(employee)
                    continue
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Employee code conflict. Provide a custom code or retry.",
                )
            if "official_email" in msg:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An employee with this official email already exists.",
                )
            if "genderenum" in msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid gender value. Use: male, female, transgender.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee data violates a database constraint.",
            )

    db.refresh(employee)
    return employee


def get_active_managers(db: Session) -> list[dict]:

    result = db.execute(
        select(Employee.id, Employee.first_name, Employee.last_name, Employee.employee_code)
        .where(Employee.is_active == True)
        .order_by(Employee.first_name)
    )
    return [
        {
            "id": row.id,
            "name": f"{row.first_name} {row.last_name or ''}".strip(),
            "employee_code": row.employee_code,
        }
        for row in result.all()
    ]