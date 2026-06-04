from datetime import date
from pydantic import BaseModel


class ShiftSwapCreate(BaseModel):

    requester_employee_id: int

    target_employee_id: int

    swap_date: date

class ShiftSwapApproval(BaseModel):
    comments: str | None = None