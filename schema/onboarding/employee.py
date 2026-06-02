from datetime import date
from pydantic import BaseModel, EmailStr
from model.onboarding.employee import GenderEnum


class EmployeeCreate(BaseModel):
    first_name: str
    middle_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: GenderEnum

    joining_date: date
    confirmation_date: date | None = None

    biometric_code: str | None = None
    mobile_number: str
    official_email: EmailStr | None = None

    business_unit: str | None = None
    location: str | None = None
    cost_center: str | None = None
    department: str | None = None
    designation: str | None = None
    grade: str | None = None

    shift_policy: str | None = None
    week_off_policy: str | None = None
    overtime_policy: str | None = None

    send_mobile_login: bool = True
    send_web_login: bool = True


class EmployeeResponse(EmployeeCreate):
    id: int
    employee_code: str

    class Config:
        from_attributes = True
