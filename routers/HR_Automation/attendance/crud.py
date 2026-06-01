from sqlalchemy.orm import Session
import model.models
from schema import schemas


# Attendance CRUD
def create_attendance(db: Session, attendance: schemas.AttendanceCreate):
    db_att = model.models.Attendance(**attendance.dict())
    db.add(db_att)
    db.commit()
    db.refresh(db_att)
    return db_att

def get_attendance(db: Session):
    return db.query(model.models.Attendance).all()

# Leave CRUD
def create_leave_request(db: Session, leave: schemas.LeaveRequestCreate):
    db_leave = model.models.LeaveRequest(**leave.dict())
    db.add(db_leave)
    db.commit()
    db.refresh(db_leave)
    return db_leave

def get_leave_requests(db: Session):
    return db.query(model.models.LeaveRequest).all()
