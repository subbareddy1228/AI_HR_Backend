from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from model.onboarding.employee import Employee
from schema.onboarding.employee import EmployeeCreate, EmployeeResponse
from services.employee_service import create_employee, get_active_managers

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("/managers", summary="Active employees for Reporting Manager dropdown")
async def list_managers(db: AsyncSession = Depends(get_db)):
    
    return await get_active_managers(db)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add New Employee — SAVE button",
)
async def add_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new employee record from the Add New Employee form.

    - employee_code is auto-generated when not provided (Auto checkbox).
    - confirmation_date defaults to joining_date + 1 month when blank.
    - reporting_manager_id is validated to be an existing active employee.
    """
    return await create_employee(db, payload)


@router.get(
    "",
    response_model=list[EmployeeResponse],
    summary="List employees",
)
async def list_employees(
    db:     AsyncSession = Depends(get_db),
    limit:  int = Query(50, ge=1, le=100),
    offset: int = Query(0,  ge=0),
):
    result = await db.execute(
        select(Employee)
        .order_by(Employee.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()