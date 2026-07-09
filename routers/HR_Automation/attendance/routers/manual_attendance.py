from __future__ import annotations

import calendar
import csv
import io
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, extract, or_
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from model.models import User, AttendanceRecord
from model.onboarding.employee import Employee

from schema.HR_Automation.manual_attendance import (
    ManualAttendanceRow,
    ManualAttendanceSave,
    ManualAttendanceBulkSave,
    ManualAttendanceUpload,
    FilterOptions,
)

router = APIRouter(
    prefix="/manual",
    tags=["Manual Attendance"],
)


COL_TO_STATUS = {
    "P":  "Present",
    "A":  "Absent",
    "H":  "Holiday",
    "W":  "WeekOff",
    "CO": "CompOff",
    "CL": "CasualLeave",
    "LW": "LossOfWeek",
}
STATUS_TO_COL = {v: k for k, v in COL_TO_STATUS.items()}
ALL_COLS      = list(COL_TO_STATUS.keys())   # ["P","A","H","W","CO","CL","LW"]


def _emp_name(emp: Employee) -> str:
    return f"{emp.first_name} {emp.last_name or ''}".strip()


def _month_year_from_str(period: str):
    
    MONTHS = {"JAN":1,"FEB":2,"MAR":3,"APR":4,"MAY":5,"JUN":6,
              "JUL":7,"AUG":8,"SEP":9,"OCT":10,"NOV":11,"DEC":12}
    parts = period.upper().split("-")
    if len(parts) == 2:
        if parts[0] in MONTHS:                  # SEP-2025
            return MONTHS[parts[0]], int(parts[1])
        else:                                    # 2025-09
            return int(parts[1]), int(parts[0])
    raise ValueError(f"Invalid period format: {period}")


def _build_row(emp: Employee, records: List[AttendanceRecord]) -> ManualAttendanceRow:
    
    counts = {c: 0 for c in ALL_COLS}
    for rec in records:
        col = STATUS_TO_COL.get(rec.status)
        if col:
            counts[col] += 1

    return ManualAttendanceRow(
        employee_id=emp.id,
        employee_code=emp.employee_code,
        employee_name=_emp_name(emp),
        business_unit=emp.business_unit,
        location=emp.location,
        cost_center=emp.cost_center,
        department=emp.department,
        **counts,
    )


def _upsert_day_records(
    db: Session,
    employee_id: int,
    month: int,
    year: int,
    col: str,
    target_count: int,
):
    status = COL_TO_STATUS[col]
    existing = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == employee_id,
        AttendanceRecord.status      == status,
        extract("month", AttendanceRecord.date) == month,
        extract("year",  AttendanceRecord.date) == year,
    ).order_by(AttendanceRecord.date).all()

    current_count = len(existing)

    if current_count < target_count:
       
        used_dates = set(r.date for r in db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == employee_id,
            extract("month", AttendanceRecord.date) == month,
            extract("year",  AttendanceRecord.date) == year,
        ).all())

        num_days = calendar.monthrange(year, month)[1]
        to_add   = target_count - current_count
        for day in range(1, num_days + 1):
            if to_add <= 0:
                break
            d = date(year, month, day)
            if d not in used_dates:
                db.add(AttendanceRecord(
                    employee_id=employee_id,
                    date=d,
                    status=status,
                ))
                used_dates.add(d)
                to_add -= 1

    elif current_count > target_count:
        
        to_delete = existing[target_count:]
        for rec in to_delete:
            db.delete(rec)



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
    )



@router.get("/", response_model=List[ManualAttendanceRow])
def list_manual_attendance(
    period:        str           = Query("SEP-2025",
                       description="Month period in MMM-YYYY format, e.g. SEP-2025"),
    business_unit: Optional[str] = Query(None),
    location:      Optional[str] = Query(None),
    cost_center:   Optional[str] = Query(None),
    department:    Optional[str] = Query(None),
    search:        Optional[str] = Query(None,
                       description="Search by employee name or code"),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        month, year = _month_year_from_str(period)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

   
    emp_q = db.query(Employee).filter(Employee.is_active == True)
    if business_unit:
        emp_q = emp_q.filter(Employee.business_unit == business_unit)
    if location:
        emp_q = emp_q.filter(Employee.location == location)
    if cost_center:
        emp_q = emp_q.filter(Employee.cost_center == cost_center)
    if department:
        emp_q = emp_q.filter(Employee.department == department)
    if search:
        like = f"%{search}%"
        emp_q = emp_q.filter(or_(
            Employee.first_name.ilike(like),
            Employee.last_name.ilike(like),
            Employee.employee_code.ilike(like),
        ))

   
    total      = emp_q.count()
    employees  = emp_q.order_by(Employee.first_name).offset((page - 1) * page_size).limit(page_size).all()
    emp_ids    = [e.id for e in employees]

    
    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id.in_(emp_ids),
        extract("month", AttendanceRecord.date) == month,
        extract("year",  AttendanceRecord.date) == year,
    ).all()

  
    emp_records: dict = {e.id: [] for e in employees}
    for rec in records:
        if rec.employee_id in emp_records:
            emp_records[rec.employee_id].append(rec)

    return [_build_row(emp, emp_records[emp.id]) for emp in employees]


@router.post("/save", status_code=200)
def save_manual_attendance(
    payload: ManualAttendanceSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = db.get(Employee, payload.employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    num_days = calendar.monthrange(payload.year, payload.month)[1]
    total    = payload.P + payload.A + payload.H + payload.W + payload.CO + payload.CL + payload.LW

    if total > num_days:
        raise HTTPException(
            status_code=400,
            detail=f"Total days ({total}) exceeds days in month ({num_days})"
        )

    db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id == payload.employee_id,
        extract("month", AttendanceRecord.date) == payload.month,
        extract("year",  AttendanceRecord.date) == payload.year,
    ).delete(synchronize_session=False)
    db.flush()

   
    col_plan = [
        ("P",  payload.P),
        ("A",  payload.A),
        ("H",  payload.H),
        ("W",  payload.W),
        ("CO", payload.CO),
        ("CL", payload.CL),
        ("LW", payload.LW),
    ]

    day = 1
    for col, count in col_plan:
        status = COL_TO_STATUS[col]
        for _ in range(count):
            if day > num_days:
                break
            db.add(AttendanceRecord(
                employee_id=payload.employee_id,
                date=date(payload.year, payload.month, day),
                status=status,
                remarks=payload.remarks,
            ))
            day += 1

    db.commit()

    return {
        "message": f"Attendance saved for {_emp_name(emp)}",
        "employee_code": emp.employee_code,
        "month": payload.month,
        "year": payload.year,
        "summary": {c: getattr(payload, c) for c in ALL_COLS},
    }


@router.post("/bulk-save", status_code=200)
def bulk_save_manual_attendance(
    payload: ManualAttendanceBulkSave,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    num_days = calendar.monthrange(payload.year, payload.month)[1]
    saved = []
    errors = []

    for row in payload.rows:
        emp = db.get(Employee, row.employee_id)
        if not emp:
            errors.append({"employee_id": row.employee_id, "error": "Not found"})
            continue

        total = row.P + row.A + row.H + row.W + row.CO + row.CL + row.LW
        if total > num_days:
            errors.append({
                "employee_code": emp.employee_code,
                "error": f"Total {total} exceeds {num_days} days in month"
            })
            continue

        # Delete existing and recreate
        db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == row.employee_id,
            extract("month", AttendanceRecord.date) == payload.month,
            extract("year",  AttendanceRecord.date) == payload.year,
        ).delete(synchronize_session=False)
        db.flush()

        day = 1
        for col in ALL_COLS:
            count  = getattr(row, col)
            status = COL_TO_STATUS[col]
            for _ in range(count):
                if day > num_days:
                    break
                db.add(AttendanceRecord(
                    employee_id=row.employee_id,
                    date=date(payload.year, payload.month, day),
                    status=status,
                    remarks=row.remarks,
                ))
                day += 1

        saved.append(emp.employee_code)

    db.commit()
    return {"saved": saved, "errors": errors}


@router.get("/download")
def download_attendance_template(
    period:        str           = Query("SEP-2025"),
    business_unit: Optional[str] = Query(None),
    location:      Optional[str] = Query(None),
    cost_center:   Optional[str] = Query(None),
    department:    Optional[str] = Query(None),
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
    emp_ids   = [e.id for e in employees]

    records = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_id.in_(emp_ids),
        extract("month", AttendanceRecord.date) == month,
        extract("year",  AttendanceRecord.date) == year,
    ).all()

    emp_records: dict = {e.id: [] for e in employees}
    for rec in records:
        if rec.employee_id in emp_records:
            emp_records[rec.employee_id].append(rec)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Sl.No", "Employee Code", "Employee Name",
                     "P", "A", "H", "W", "CO", "CL", "LW"])

    for i, emp in enumerate(employees, 1):
        row_data = _build_row(emp, emp_records[emp.id])
        writer.writerow([
            i, emp.employee_code, _emp_name(emp),
            row_data.P, row_data.A, row_data.H, row_data.W,
            row_data.CO, row_data.CL, row_data.LW,
        ])

    output.seek(0)
    filename = f"manual_attendance_{period}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/upload", status_code=200)
def upload_attendance(
    payload: ManualAttendanceUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    num_days = calendar.monthrange(payload.year, payload.month)[1]
    saved  = []
    errors = []

    for row in payload.rows:
        emp = db.query(Employee).filter(
            Employee.employee_code == row.employee_code
        ).first()

        if not emp:
            errors.append({"employee_code": row.employee_code, "error": "Employee not found"})
            continue

        total = row.P + row.A + row.H + row.W + row.CO + row.CL + row.LW
        if total > num_days:
            errors.append({
                "employee_code": row.employee_code,
                "error": f"Total {total} exceeds {num_days} days",
            })
            continue

        
        db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_id == emp.id,
            extract("month", AttendanceRecord.date) == payload.month,
            extract("year",  AttendanceRecord.date) == payload.year,
        ).delete(synchronize_session=False)
        db.flush()

        day = 1
        for col in ALL_COLS:
            count  = getattr(row, col)
            status = COL_TO_STATUS[col]
            for _ in range(count):
                if day > num_days:
                    break
                db.add(AttendanceRecord(
                    employee_id=emp.id,
                    date=date(payload.year, payload.month, day),
                    status=status,
                    remarks=row.remarks,
                ))
                day += 1

        saved.append(row.employee_code)

    db.commit()
    return {
        "message": f"Upload complete — {len(saved)} saved, {len(errors)} errors",
        "saved": saved,
        "errors": errors,
    }

