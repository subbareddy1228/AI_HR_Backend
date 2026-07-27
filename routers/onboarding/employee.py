from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.database import get_db
from model.onboarding.employee import Employee
from schema.onboarding.employee import EmployeeCreate, EmployeeResponse
from services.employee_service import create_employee, get_active_managers

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("/managers", summary="Active employees for Reporting Manager dropdown")
def list_managers(db: Session = Depends(get_db)):

    return get_active_managers(db)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add New Employee — SAVE button",
)
def add_employee(
    payload: EmployeeCreate,
    db: Session = Depends(get_db),
):
    """
    Creates a new employee record from the Add New Employee form.

    - employee_code is auto-generated when not provided (Auto checkbox).
    - confirmation_date defaults to joining_date + 1 month when blank.
    - reporting_manager_id is validated to be an existing active employee.
    """
    return create_employee(db, payload)


@router.get(
    "",
    response_model=list[EmployeeResponse],
    summary="List employees",
)
def list_employees(
    db:     Session = Depends(get_db),
    limit:  int = Query(50, ge=1, le=100),
    offset: int = Query(0,  ge=0),
):
    # NOTE: this whole file (and services/employee_service.py) was written
    # for AsyncSession — `await db.execute(...)` — but the real get_db
    # dependency (core.database) yields a plain sync SQLAlchemy Session.
    # A sync Session's .execute() returns a ChunkedIteratorResult directly,
    # not an awaitable, so every call here crashed in production with
    # "TypeError: 'ChunkedIteratorResult' object can't be awaited" on
    # GET /employees (and would have on POST /employees and
    # GET /employees/managers too, on their own await calls). Converted to
    # plain sync calls throughout — matches the pattern used everywhere
    # else in this codebase (core/database.py's get_db is sync).
    result = db.execute(
        select(Employee)
        .order_by(Employee.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()