from __future__ import annotations

import calendar
import csv
import io
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import extract, func, or_
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User, LeaveRequest
from model.onboarding.employee import Employee

from schema.HR_Automation.leave_correction import (
    LeaveCorrectionRow,
    LeaveCorrectionSave,
    LeaveCorrectionBulkSave,
    LeaveTypeOption,
    FilterOptions,
)

router = APIRouter(
    prefix="/correction",
    tags=["Leave Correction"],
)


LEAVE_TYPES: List[LeaveTypeOption] = [
    LeaveTypeOption(code="CASUAL",    label="LV001 - Casual Leave",    short_name="Casual Leave"),
    LeaveTypeOption(code="SICK",      label="LV002 - Sick Leave",      short_name="Sick Leave"),
    LeaveTypeOption(code="EARNED",    label="LV003 - Earned Leave",    short_name="Earned Leave"),
    LeaveTypeOption(code="MATERNITY", label="LV004 - Maternity Leave", short_name="Maternity Leave"),
    LeaveTypeOption(code="PATERNITY", label="LV005 - Paternity Leave", short_name="Paternity Leave"),
    LeaveTypeOption(code="UNPAID",    label="LV006 - Unpaid Leave",    short_name="Unpaid Leave"),
    LeaveTypeOption(code="COMP_OFF",  label="LV458 - Comp Off",        short_name="Comp Off"),
]
LEAVE_CODE_MAP = {lt.code: lt for lt in LEAVE_TYPES}


MONTHLY_ACCRUAL = {
    "CASUAL":    1.5,
    "SICK":      1.0,
    "EARNED":    1.25,
    "MATERNITY": 0.0,
    "PATERNITY": 0.0,
    "UNPAID":    0.0,
    "COMP_OFF":  0.0,
}


CORRECTION_TAG = "__CORRECTION__"



def _emp_name(emp: Employee) -> str:
    return f"{emp.first_name} {emp.last_name or ''}".strip()


def _month_year_from_str(period: str):
    
    MONTHS = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
              "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}
    parts = period.upper().split("-")
    if len(parts) == 2 and parts[0] in MONTHS:
        return MONTHS[parts[0]], int(parts[1])
    raise ValueError(f"Invalid period format: {period}. Use MMM-YYYY e.g. SEP-2025")


def _get_activity(db: Session, employee_id: int, leave_type_code: str,
                  month: int, year: int) -> float:
    
    rows = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.leave_type  == leave_type_code,
        LeaveRequest.status      == "approved",
        extract("month", LeaveRequest.start_date) == month,
        extract("year",  LeaveRequest.start_date) == year,
    ).all()
    total = 0.0
    for r in rows:
        total += (r.end_date - r.start_date).days + 1
    return total


def _get_correction(db: Session, employee_id: int, leave_type_code: str,
                    month: int, year: int) -> float:
    
    tag = f"{CORRECTION_TAG}{leave_type_code}:{month}:{year}:"
    row = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.reason.like(f"{tag}%"),
    ).first()
    if row:
        try:
            return float(row.reason.split(":")[-1])
        except Exception:
            return 0.0
    return 0.0


def _opening_balance(leave_type_code: str, year: int, month: int) -> float:
    
    accrual = MONTHLY_ACCRUAL.get(leave_type_code, 0.0)
    months_elapsed = month - 1          
    return round(accrual * months_elapsed, 2)


def _build_row(
    emp: Employee,
    leave_type_code: str,
    month: int,
    year: int,
    db: Session,
) -> LeaveCorrectionRow:
    lt          = LEAVE_CODE_MAP.get(leave_type_code, LEAVE_TYPES[-1])
    opening     = _opening_balance(leave_type_code, year, month)
    activity    = _get_activity(db, emp.id, leave_type_code, month, year)
    correction  = _get_correction(db, emp.id, leave_type_code, month, year)
    closing     = round(opening + activity + correction, 2)

    return LeaveCorrectionRow(
        employee_id=emp.id,
        employee_code=emp.employee_code,
        employee_name=_emp_name(emp),
        designation=emp.designation,
        business_unit=emp.business_unit,
        location=emp.location,
        cost_center=emp.cost_center,
        department=emp.department,
        leave_type=lt.label,
        leave_type_code=leave_type_code,
        month=month,
        year=year,
        opening=opening,
        activity=activity,
        correction=correction,
        closing=closing,
    )



@router.get("/filter-options", response_model=FilterOptions)
def get_filter_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    def _distinct(col):
        return sorted(set(
            r[0] for r in db.query(col)
            .filter(Employee.is_active == True, col.isnot(None))
            .distinct().all()
        ))

    return FilterOptions(
        business_units=_distinct(Employee.business_unit),
        locations=_distinct(Employee.location),
        cost_centers=_distinct(Employee.cost_center),
        departments=_distinct(Employee.department),
        leave_types=LEAVE_TYPES,
    )


@router.get("/", response_model=List[LeaveCorrectionRow])
def list_leave_corrections(
    period:          str           = Query("SEP-2025",
                         description="MMM-YYYY e.g. SEP-2025"),
    leave_type_code: str           = Query("COMP_OFF",
                         description="CASUAL|SICK|EARNED|COMP_OFF|MATERNITY|PATERNITY|UNPAID"),
    business_unit:   Optional[str] = Query(None),
    location:        Optional[str] = Query(None),
    cost_center:     Optional[str] = Query(None),
    department:      Optional[str] = Query(None),
    search:          Optional[str] = Query(None),
    page:            int           = Query(1, ge=1),
    page_size:       int           = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        month, year = _month_year_from_str(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if leave_type_code not in LEAVE_CODE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid leave_type_code. Valid values: {list(LEAVE_CODE_MAP.keys())}"
        )

    
    emp_q = db.query(Employee).filter(Employee.is_active == True)
    if business_unit: emp_q = emp_q.filter(Employee.business_unit == business_unit)
    if location:      emp_q = emp_q.filter(Employee.location      == location)
    if cost_center:   emp_q = emp_q.filter(Employee.cost_center   == cost_center)
    if department:    emp_q = emp_q.filter(Employee.department     == department)
    if search:
        like = f"%{search}%"
        emp_q = emp_q.filter(or_(
            Employee.first_name.ilike(like),
            Employee.last_name.ilike(like),
            Employee.employee_code.ilike(like),
            Employee.designation.ilike(like),
        ))

    total     = emp_q.count()
    employees = (
        emp_q.order_by(Employee.first_name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [_build_row(emp, leave_type_code, month, year, db) for emp in employees]


@router.post("/save", status_code=200)
def save_leave_correction(
    payload: LeaveCorrectionSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = db.get(Employee, payload.employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if payload.leave_type_code not in LEAVE_CODE_MAP:
        raise HTTPException(status_code=400, detail="Invalid leave type code")

    
    tag    = f"{CORRECTION_TAG}{payload.leave_type_code}:{payload.month}:{payload.year}"
    reason = f"{tag}:{payload.correction}"
    if payload.remarks:
        reason += f" | {payload.remarks}"

    
    existing = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == payload.employee_id,
        LeaveRequest.reason.like(f"{tag}%"),
    ).first()

    
    first_day = date(payload.year, payload.month, 1)
    last_day  = date(payload.year, payload.month,
                     calendar.monthrange(payload.year, payload.month)[1])

    if existing:
        existing.reason    = reason
        existing.leave_type = payload.leave_type_code
        existing.start_date = first_day
        existing.end_date   = last_day
    else:
        db.add(LeaveRequest(
            employee_id = payload.employee_id,
            leave_type  = payload.leave_type_code,
            start_date  = first_day,
            end_date    = last_day,
            reason      = reason,
            status      = "approved",           
        ))

    db.commit()

   
    opening    = _opening_balance(payload.leave_type_code, payload.year, payload.month)
    activity   = _get_activity(db, payload.employee_id, payload.leave_type_code,
                               payload.month, payload.year)
    closing    = round(opening + activity + payload.correction, 2)
    lt         = LEAVE_CODE_MAP[payload.leave_type_code]

    return {
        "message":    f"Correction saved for {_emp_name(emp)}",
        "employee_code": emp.employee_code,
        "leave_type": lt.label,
        "month":      payload.month,
        "year":       payload.year,
        "opening":    opening,
        "activity":   activity,
        "correction": payload.correction,
        "closing":    closing,
    }



@router.post("/bulk-save", status_code=200)
def bulk_save_corrections(
    payload: LeaveCorrectionBulkSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    if payload.leave_type_code not in LEAVE_CODE_MAP:
        raise HTTPException(status_code=400, detail="Invalid leave type code")

    first_day = date(payload.year, payload.month, 1)
    last_day  = date(payload.year, payload.month,
                     calendar.monthrange(payload.year, payload.month)[1])
    tag_base  = f"{CORRECTION_TAG}{payload.leave_type_code}:{payload.month}:{payload.year}"

    saved  = []
    errors = []

    for row in payload.rows:
        emp = db.get(Employee, row.employee_id)
        if not emp:
            errors.append({"employee_id": row.employee_id, "error": "Not found"})
            continue

        reason   = f"{tag_base}:{row.correction}"
        if row.remarks:
            reason += f" | {row.remarks}"

        existing = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == row.employee_id,
            LeaveRequest.reason.like(f"{tag_base}%"),
        ).first()

        if existing:
            existing.reason     = reason
            existing.start_date = first_day
            existing.end_date   = last_day
        else:
            db.add(LeaveRequest(
                employee_id = row.employee_id,
                leave_type  = payload.leave_type_code,
                start_date  = first_day,
                end_date    = last_day,
                reason      = reason,
                status      = "approved",
            ))
        saved.append(emp.employee_code)

    db.commit()
    return {
        "message": f"{len(saved)} corrections saved, {len(errors)} errors",
        "saved":   saved,
        "errors":  errors,
    }



@router.get("/download")
def download_leave_corrections(
    period:          str           = Query("SEP-2025"),
    leave_type_code: str           = Query("COMP_OFF"),
    business_unit:   Optional[str] = Query(None),
    location:        Optional[str] = Query(None),
    cost_center:     Optional[str] = Query(None),
    department:      Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        month, year = _month_year_from_str(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    emp_q = db.query(Employee).filter(Employee.is_active == True)
    if business_unit: emp_q = emp_q.filter(Employee.business_unit == business_unit)
    if location:      emp_q = emp_q.filter(Employee.location      == location)
    if cost_center:   emp_q = emp_q.filter(Employee.cost_center   == cost_center)
    if department:    emp_q = emp_q.filter(Employee.department     == department)
    employees = emp_q.order_by(Employee.first_name).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Sl.No", "Employee Code", "Employee Name", "Designation",
        "Opening", "Activity", "Correction", "Closing"
    ])

    for i, emp in enumerate(employees, 1):
        row = _build_row(emp, leave_type_code, month, year, db)
        writer.writerow([
            i, emp.employee_code, _emp_name(emp), emp.designation or "",
            row.opening, row.activity, row.correction, row.closing,
        ])

    output.seek(0)
    filename = f"leave_correction_{leave_type_code}_{period}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



@router.post("/upload", status_code=200)
def upload_leave_corrections(
    month:           int,
    year:            int,
    leave_type_code: str,
    rows:            List[LeaveCorrectionSave],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if leave_type_code not in LEAVE_CODE_MAP:
        raise HTTPException(status_code=400, detail="Invalid leave type code")

    first_day = date(year, month, 1)
    last_day  = date(year, month, calendar.monthrange(year, month)[1])
    tag_base  = f"{CORRECTION_TAG}{leave_type_code}:{month}:{year}"

    saved  = []
    errors = []

    for row in rows:
        emp = db.get(Employee, row.employee_id)
        if not emp:
            errors.append({"employee_id": row.employee_id, "error": "Not found"})
            continue

        reason   = f"{tag_base}:{row.correction}"
        if row.remarks:
            reason += f" | {row.remarks}"

        existing = db.query(LeaveRequest).filter(
            LeaveRequest.employee_id == row.employee_id,
            LeaveRequest.reason.like(f"{tag_base}%"),
        ).first()

        if existing:
            existing.reason     = reason
            existing.start_date = first_day
            existing.end_date   = last_day
        else:
            db.add(LeaveRequest(
                employee_id = row.employee_id,
                leave_type  = leave_type_code,
                start_date  = first_day,
                end_date    = last_day,
                reason      = reason,
                status      = "approved",
            ))
        saved.append(emp.employee_code)

    db.commit()
    return {
        "message": f"Upload complete — {len(saved)} saved, {len(errors)} errors",
        "saved":   saved,
        "errors":  errors,
    }


