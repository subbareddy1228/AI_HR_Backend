import uuid
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from model.onboarding.employee import Employee
from schema.onboarding.employee import EmployeeCreate


def generate_employee_code() -> str:
    return f"EMP-{uuid.uuid4().hex[:8].upper()}"


async def create_employee(
    db: AsyncSession,
    payload: EmployeeCreate,
) -> Employee:
    employee = Employee(
        **payload.model_dump(),
        employee_code=generate_employee_code(),  # 🔥 FIX
    )

    db.add(employee)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        msg = str(exc)

        if "employees_mobile_number_key" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Employee with this mobile number already exists",
            )

        if "genderenum" in msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid gender value (use: male, female, transgender)",
            )

        if "employees_employee_code_key" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Employee code conflict, retry request",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee data violates database constraints",
        )

    await db.refresh(employee)
    return employee
