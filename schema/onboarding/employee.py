from datetime import date, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, model_validator
from model.onboarding.employee import GenderEnum


class EmployeeCreate(BaseModel):

   
    first_name:  str            = Field(..., min_length=1)
    middle_name: Optional[str]  = None
    last_name:   Optional[str]  = None

    
    joining_date:      date                = Field(..., description="Required")
    confirmation_date: Optional[date]      = Field(None, description="Defaults to joining_date + 1 month if blank")
    date_of_birth:     Optional[date]      = Field(None, description="Optional but recommended")

    
    gender: GenderEnum

  
    employee_code:  Optional[str] = Field(None, description="Leave blank to auto-generate")
    biometric_code: Optional[str] = None

    
    mobile_number:  str                = Field(..., pattern=r"^[0-9]{10}$")
    personal_email: Optional[EmailStr] = Field(None, description="Personal Email — Optional")
    official_email: Optional[EmailStr] = Field(None, description="Company email address")

    
    designation:          Optional[str] = None
    department:           Optional[str] = None
    business_unit:        Optional[str] = None
    location:             Optional[str] = None
    location_id:          Optional[int] = Field(None, description="Branch/office (CompanyLocation) this employee belongs to")
    grade:                Optional[str] = None
    cost_center:          Optional[str] = None
    reporting_manager_id: Optional[int] = Field(None, description="Employee ID of reporting manager")

    
    shift_policy:    Optional[str] = None
    week_off_policy: Optional[str] = None
    overtime_policy: Optional[str] = None

    
    send_mobile_login: bool = True
    send_web_login:    bool = True

    
    @model_validator(mode="after")
    def default_confirmation_date(self) -> "EmployeeCreate":
        if self.confirmation_date is None:
            
            jd = self.joining_date
            
            month = jd.month + 1
            year  = jd.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            self.confirmation_date = date(year, month, min(jd.day, last_day))
        return self


class EmployeeResponse(BaseModel):
    id:             int
    employee_code:  str
    first_name:     str
    middle_name:    Optional[str]
    last_name:      Optional[str]
    date_of_birth:  Optional[date]
    joining_date:   date
    confirmation_date: Optional[date]
    gender:         GenderEnum
    biometric_code: Optional[str]
    mobile_number:  str
    personal_email: Optional[str]
    official_email: Optional[str]
    designation:    Optional[str]
    department:     Optional[str]
    business_unit:  Optional[str]
    location:       Optional[str]
    location_id:    Optional[int] = None
    branch_name:    Optional[str] = Field(None, description="Resolved name of the assigned CompanyLocation, if any")
    grade:          Optional[str]
    cost_center:    Optional[str]
    reporting_manager_id: Optional[int]
    shift_policy:    Optional[str]
    week_off_policy: Optional[str]
    overtime_policy: Optional[str]
    send_mobile_login: bool
    send_web_login:    bool
    is_active:         bool

    class Config:
        from_attributes = True