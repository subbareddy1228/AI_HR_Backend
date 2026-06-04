# # services/Payroll/slip_service.py
# # Service layer for SalarySlip operations

# from sqlalchemy.orm import Session
# from sqlalchemy import select
# from typing import Optional, List
# from fastapi import HTTPException, status

# from model.Payroll.salary_slip import SalarySlip
# from schema.Payroll.salary_slip import SalarySlipCreate, SalarySlipUpdate


# def create_salary_slip(db: Session, payload: SalarySlipCreate) -> SalarySlip:
#     """Create a new salary slip."""
#     obj = SalarySlip(**payload.model_dump())
#     db.add(obj)
#     db.commit()
#     db.refresh(obj)
#     return obj


# def list_salary_slips(
#     db: Session,
#     employee_id: Optional[int] = None,
#     slip_month: Optional[int] = None,
#     slip_year: Optional[int] = None,
# ) -> List[SalarySlip]:
#     """List salary slips with optional filters."""
#     stmt = select(SalarySlip)
#     if employee_id:
#         stmt = stmt.where(SalarySlip.employee_id == employee_id)
#     if slip_month:
#         stmt = stmt.where(SalarySlip.slip_month == slip_month)
#     if slip_year:
#         stmt = stmt.where(SalarySlip.slip_year == slip_year)
#     return db.execute(stmt).scalars().all()


# def get_salary_slip(db: Session, slip_id: int) -> SalarySlip:
#     """Fetch a salary slip by ID. Raises 404 if not found."""
#     obj = db.execute(
#         select(SalarySlip).where(SalarySlip.id == slip_id)
#     ).scalar_one_or_none()

#     if not obj:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salary slip not found")
#     return obj


# def get_slips_by_employee(db: Session, employee_id: int) -> List[SalarySlip]:
#     """Get all salary slips for an employee, most recent first."""
#     return db.execute(
#         select(SalarySlip)
#         .where(SalarySlip.employee_id == employee_id)
#         .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
#     ).scalars().all()


# def publish_salary_slip(db: Session, slip_id: int) -> SalarySlip:
#     """Mark a salary slip as published (visible to employee)."""
#     obj = get_salary_slip(db, slip_id)
#     obj.is_published = True
#     db.commit()
#     db.refresh(obj)
#     return obj


# def update_salary_slip(db: Session, slip_id: int, payload: SalarySlipUpdate) -> SalarySlip:
#     """Update a salary slip's fields."""
#     obj = get_salary_slip(db, slip_id)
#     for key, value in payload.model_dump(exclude_unset=True).items():
#         setattr(obj, key, value)
#     db.commit()
#     db.refresh(obj)
#     return obj


# def delete_salary_slip(db: Session, slip_id: int) -> None:
#     """Delete a salary slip. Raises 404 if not found."""
#     obj = get_salary_slip(db, slip_id)
#     db.delete(obj)
#     db.commit()




from sqlalchemy.orm import Session
from sqlalchemy import select

from typing import List

from fastapi import HTTPException, status

from model.Payroll.salary_slip import SalarySlip

from schema.Payroll.salary_slip import (
    SalarySlipCreate,
    SalarySlipUpdate
)

from datetime import datetime


def create_salary_slip(
    db: Session,
    payload: SalarySlipCreate
):

    obj = SalarySlip(
        **payload.model_dump()
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)

    return obj


def list_salary_slips(
    db: Session
):

    return db.execute(
        select(SalarySlip)
    ).scalars().all()


def get_salary_slip(
    db: Session,
    slip_id: int
):

    obj = db.execute(
        select(SalarySlip).where(
            SalarySlip.id == slip_id
        )
    ).scalar_one_or_none()

    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salary Slip Not Found"
        )

    return obj


def get_employee_salary_slips(
    db: Session,
    employee_id: int
):

    return db.execute(
        select(SalarySlip).where(
            SalarySlip.employee_id == employee_id
        )
    ).scalars().all()


def update_salary_slip(
    db: Session,
    slip_id: int,
    payload: SalarySlipUpdate
):

    obj = get_salary_slip(
        db,
        slip_id
    )

    for key, value in payload.model_dump(
        exclude_unset=True
    ).items():

        setattr(
            obj,
            key,
            value
        )

    db.commit()
    db.refresh(obj)

    return obj


def publish_salary_slip(
    db: Session,
    slip_id: int
):

    obj = get_salary_slip(
        db,
        slip_id
    )

    obj.is_published = True

    db.commit()
    db.refresh(obj)

    return obj


def distribute_salary_slip(
    db: Session,
    slip_id: int,
    method: str
):

    obj = get_salary_slip(
        db,
        slip_id
    )

    obj.is_distributed = True
    obj.distribution_method = method
    obj.distributed_at = datetime.utcnow()

    db.commit()
    db.refresh(obj)

    return obj


def delete_salary_slip(
    db: Session,
    slip_id: int
):

    obj = get_salary_slip(
        db,
        slip_id
    )

    db.delete(obj)
    db.commit()


def get_dashboard_data(
    db: Session
):

    slips = list_salary_slips(db)

    return {
        "total_slips": len(slips),
        "distributed_slips": len(
            [s for s in slips if s.is_distributed]
        ),
        "total_payout": sum(
            float(s.net_pay)
            for s in slips
        )
    }