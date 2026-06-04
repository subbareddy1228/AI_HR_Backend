# schema/HR_Automation/shift.py

from datetime import time
from pydantic import BaseModel


class ShiftCreate(BaseModel):
    shift_name: str
    shift_code: str
    start_time: time
    end_time: time
    grace_minutes: int = 15



class ShiftUpdate(BaseModel):
    shift_name: str | None = None
    shift_code: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    grace_minutes: int | None = None
    is_active: bool | None = None