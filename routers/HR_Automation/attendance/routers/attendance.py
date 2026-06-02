# routers/HR_Automation/attendance/routers/attendance.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from core.database import get_db  
from schema import schemas
from crud_ops import crud     

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/", response_model=list[schemas.AttendanceOut])
def get_attendance_records(db: Session = Depends(get_db)):
    return crud.get_attendance(db)

@router.post("/", response_model=schemas.AttendanceOut)
def mark_attendance(attendance: schemas.AttendanceCreate, db: Session = Depends(get_db)):
    return crud.create_attendance(db, attendance)

@router.get("/today")
def get_today_attendance(db: Session = Depends(get_db)):
    record = crud.get_attendance_by_date(db, date.today())
    if not record:
        raise HTTPException(status_code=404, detail="No attendance found for today")
    return record
