from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from model.onboarding.employee import Employee
from schema.onboarding.employee import EmployeeCreate, EmployeeResponse
from services.employee_service import create_employee

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED
)
async def add_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
):
    return await create_employee(db, payload)


@router.get(
    "",
    response_model=list[EmployeeResponse]
)
async def list_employees(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    stmt = (
        select(Employee)
        .order_by(Employee.id.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    return result.scalars().all()
