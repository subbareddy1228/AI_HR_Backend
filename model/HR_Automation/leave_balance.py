class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(Integer, primary_key=True)

    employee_id = Column(Integer)

    leave_type_id = Column(Integer)

    total_leave = Column(Float)

    used_leave = Column(Float)

    balance_leave = Column(Float)