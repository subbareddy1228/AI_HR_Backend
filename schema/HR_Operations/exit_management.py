# from pydantic import BaseModel, ConfigDict
# from datetime import date, datetime
# from typing import Optional


# class ExitManagementCreate(BaseModel):
#     employee_id: int
#     resignation_date: date
#     last_working_date: Optional[date] = None
#     exit_type: str          # RESIGNATION | TERMINATION | RETIREMENT | ABSCONDING
#     reason: Optional[str] = None
#     remarks: Optional[str] = None


# class ExitManagementUpdate(BaseModel):
#     last_working_date: Optional[date] = None
#     status: Optional[str] = None
#     exit_interview_done: Optional[str] = None
#     clearance_status: Optional[str] = None
#     remarks: Optional[str] = None


# class ExitManagementResponse(BaseModel):
#     id: int
#     employee_id: int
#     resignation_date: date
#     last_working_date: Optional[date]
#     exit_type: str
#     reason: Optional[str]
#     status: str
#     exit_interview_done: str
#     clearance_status: str
#     remarks: Optional[str]
#     created_at: datetime
#     updated_at: datetime

#     model_config = ConfigDict(from_attributes=True)
