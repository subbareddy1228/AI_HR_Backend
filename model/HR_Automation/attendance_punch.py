from sqlalchemy import Column,Integer,String,DateTime
from core.database import Base

class AttendancePunch(Base):
    __tablename__ = "attendance_punches"

    id = Column(Integer, primary_key=True)

    employee_id = Column(Integer)

    punch_time = Column(DateTime)

    punch_type = Column(String(10))

    source = Column(String(30))