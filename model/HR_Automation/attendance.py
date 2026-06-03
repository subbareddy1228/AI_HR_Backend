from sqlalchemy import Column, Integer, String, Date, DateTime, Float
from core.database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, nullable=False)
    attendance_date = Column(Date, nullable=False)

    check_in = Column(DateTime)
    check_out = Column(DateTime)

    total_hours = Column(Float, default=0)

    status = Column(
        String(30),
        default="Present"
    )

    shift_id = Column(Integer)

    created_at = Column(DateTime)
