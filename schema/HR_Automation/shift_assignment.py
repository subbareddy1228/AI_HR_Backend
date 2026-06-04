# schema/HR_Automation/shift_assignment.py

from datetime import date
from pydantic import BaseModel


class ShiftAssignmentCreate(BaseModel):

    employee_id: int

    shift_id: int

    effective_from: date

    effective_to: date | None = None