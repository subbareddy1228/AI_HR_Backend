from sqlalchemy import Column,Integer,String,Boolean,Float
from core.database import Base

class LeaveType(Base):
    __tablename__ = "leave_types"

    id = Column(Integer, primary_key=True)

    leave_name = Column(String(100))

    paid_leave = Column(Boolean)

    yearly_quota = Column(Float)

    carry_forward = Column(Boolean)

    max_carry_forward = Column(Float)