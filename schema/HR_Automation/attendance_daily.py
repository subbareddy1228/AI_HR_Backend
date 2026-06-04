from datetime import date
from datetime import datetime

from pydantic import BaseModel


class AttendanceDailyCreate(
    BaseModel
):
    employee_id: int

    attendance_date: date

    attendance_status: str = "P"

    remarks: str | None = None


class AttendanceDailyResponse(
    BaseModel
):
    id: int

    employee_id: int

    attendance_date: date

    first_in: datetime | None

    last_out: datetime | None

    work_minutes: int

    break_minutes: int

    overtime_minutes: int

    late_minutes: int

    attendance_status: str

    class Config:
        from_attributes = True