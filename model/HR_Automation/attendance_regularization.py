class AttendanceRegularization(Base):
    __tablename__ = "attendance_regularizations"

    id = Column(Integer, primary_key=True)

    employee_id = Column(Integer)

    request_type = Column(String(50))

    attendance_date = Column(Date)

    original_time = Column(DateTime)

    corrected_time = Column(DateTime)

    reason = Column(Text)

    attachment = Column(String)

    status = Column(String(30), default="Pending")