from sqlalchemy import *

class LeaveApplication(Base):
    __tablename__ = "leave_applications"

    id = Column(Integer, primary_key=True)

    employee_id = Column(Integer)

    leave_type_id = Column(Integer)

    from_date = Column(Date)

    to_date = Column(Date)

    total_days = Column(Float)

    reason = Column(Text)

    attachment = Column(String)

    status = Column(String(30), default="Pending")

    approved_by = Column(Integer)