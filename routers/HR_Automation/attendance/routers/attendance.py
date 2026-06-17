from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from schema.HR_Automation.attendance import AttendanceCreate, AttendanceOut
from routers.HR_Automation.attendance.crud import create_attendance, get_attendance
from typing import List

router = APIRouter(tags=["Attendance"])

@router.post("/", response_model=AttendanceOut, status_code=201)
def mark_attendance(payload: AttendanceCreate, db: Session = Depends(get_db)):
    return create_attendance(db, payload)

@router.get("/", response_model=List[AttendanceOut])
def list_attendance(db: Session = Depends(get_db)):
    return get_attendance(db)
