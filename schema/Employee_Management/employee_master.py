
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional
from decimal import Decimal
from datetime import date, datetime



VALID_EMPLOYMENT_TYPES = {"Full-Time", "Part-Time", "Contract", "Intern"}
VALID_STATUSES = {"Active", "Inactive", "On Leave", "Resigned", "Terminated"}


class EmployeeMasterCreate(BaseModel):

    employee_id: int


    salary: Optional[Decimal] = None
    currency: Optional[str] = "USD"

 
    employment_type: str = "Full-Time"


    employment_status: Optional[str] = "Active"


    probation_end_date: Optional[date] = None
    confirmed_date: Optional[date] = None
    reporting_manager_id: Optional[int] = None
    work_location: Optional[str] = None
    notice_period_days: Optional[int] = 30

    @field_validator("employment_type")
    @classmethod
    def validate_type(cls, v):
        if v not in VALID_EMPLOYMENT_TYPES:
            raise ValueError(f"employment_type must be one of: {', '.join(VALID_EMPLOYMENT_TYPES)}")
        return v

    @field_validator("employment_status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"employment_status must be one of: {', '.join(VALID_STATUSES)}")
        return v


class EmployeeMasterUpdate(BaseModel):
    """
    Used by: PUT /api/employees/master/{employee_id}
    Partial update — only fields you send will change.
    Common use: change status (Active → On Leave), update salary, change type.
    """
    salary: Optional[Decimal] = None
    currency: Optional[str] = None
    employment_type: Optional[str] = None
    employment_status: Optional[str] = None
    probation_end_date: Optional[date] = None
    confirmed_date: Optional[date] = None
    reporting_manager_id: Optional[int] = None
    work_location: Optional[str] = None
    notice_period_days: Optional[int] = None

    @field_validator("employment_type")
    @classmethod
    def validate_type(cls, v):
        if v and v not in VALID_EMPLOYMENT_TYPES:
            raise ValueError(f"employment_type must be one of: {', '.join(VALID_EMPLOYMENT_TYPES)}")
        return v

    @field_validator("employment_status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"employment_status must be one of: {', '.join(VALID_STATUSES)}")
        return v


class EmployeeMasterResponse(BaseModel):

    id: int
    employee_id: int
    salary: Optional[Decimal]
    currency: str
    employment_type: str
    employment_status: str
    probation_end_date: Optional[date]
    confirmed_date: Optional[date]
    reporting_manager_id: Optional[int]
    work_location: Optional[str]
    notice_period_days: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class EmployeeTableRow(BaseModel):
  
    id: int
    employee_code: str
    name: str
    designation: str

  
    department: str
    location: str

  
    email: str
    phone: str

   
    salary: Optional[Decimal]
    currency: str
    employment_type: str    

  
    employment_status: str   


    joining_date: Optional[str]
    grade: Optional[str]
    work_location: Optional[str]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class EmployeeTableResponse(BaseModel):
 
    employees: list[EmployeeTableRow]
    total: int
    page: int
    page_size: int
    total_pages: int
    showing_from: int
    showing_to: int


class EmployeeDetailResponse(BaseModel):

    id: int
    employee_code: str
    name: str
    first_name: str
    last_name: Optional[str]
    date_of_birth: Optional[str]
    gender: Optional[str]
    official_email: Optional[str]
    mobile_number: str
    designation: Optional[str]
    department: Optional[str]
    grade: Optional[str]
    location: Optional[str]
    business_unit: Optional[str]
    cost_center: Optional[str]
    joining_date: Optional[str]
    confirmation_date: Optional[str]
    is_active: bool

    # From EmployeeMaster table
    salary: Optional[Decimal]
    currency: Optional[str]
    employment_type: Optional[str]
    employment_status: Optional[str]
    work_location: Optional[str]
    probation_end_date: Optional[str]
    confirmed_date: Optional[str]
    reporting_manager_id: Optional[int]
    notice_period_days: Optional[int]


class StatsResponse(BaseModel):
  
    total_employees: int        # "Total Employees — 8"
    active_employees: int       # "Active Employees — 6"
    departments: int            # "Departments — 7"
    avg_salary: Optional[float] # "Avg. Salary — $70,750"
