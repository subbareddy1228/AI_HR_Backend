from datetime import date
from pydantic import BaseModel


class ShiftRosterCreate(BaseModel):

    employee_id: int

    shift_id: int

    roster_date: date