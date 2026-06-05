# # FILE 9 (3/8) | schema/Payroll/salary_slip.py
# # Schemas: SalarySlipBase/Create/Update/Response

# from pydantic import BaseModel, ConfigDict
# from typing import Optional
# from datetime import datetime
# from decimal import Decimal


# class SalarySlipBase(BaseModel):
#     employee_id: int
#     payroll_run_id: Optional[int] = None
#     slip_month: int
#     slip_year: int
#     employee_code: str
#     employee_name: str
#     department: Optional[str] = None
#     designation: Optional[str] = None
#     bank_account: Optional[str] = None
#     bank_name: Optional[str] = None
#     gross_salary: Decimal
#     total_deductions: Decimal
#     net_pay: Decimal
#     earnings_json: Optional[str] = None
#     deductions_json: Optional[str] = None
#     is_published: Optional[bool] = False


# class SalarySlipCreate(SalarySlipBase):
#     pass


# class SalarySlipUpdate(BaseModel):
#     bank_account: Optional[str] = None
#     bank_name: Optional[str] = None
#     gross_salary: Optional[Decimal] = None
#     total_deductions: Optional[Decimal] = None
#     net_pay: Optional[Decimal] = None
#     earnings_json: Optional[str] = None
#     deductions_json: Optional[str] = None
#     is_published: Optional[bool] = None


# class SalarySlipResponse(SalarySlipBase):
#     id: int
#     generated_at: Optional[datetime] = None

#     model_config = ConfigDict(from_attributes=True)




from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal


class SalarySlipBase(BaseModel):

    employee_id: int
    payroll_run_id: Optional[int] = None

    slip_month: int
    slip_year: int

    employee_code: str
    employee_name: str

    department: Optional[str] = None
    designation: Optional[str] = None

    bank_account: Optional[str] = None
    bank_name: Optional[str] = None

    gross_salary: Decimal
    total_deductions: Decimal
    net_pay: Decimal

    earnings_json: Optional[str] = None
    deductions_json: Optional[str] = None

    is_published: Optional[bool] = False

    is_distributed: Optional[bool] = False
    distribution_method: Optional[str] = None

    password_protected: Optional[bool] = False
    email_sent: Optional[bool] = False

    pdf_path: Optional[str] = None


class SalarySlipCreate(SalarySlipBase):
    pass


class SalarySlipUpdate(BaseModel):

    bank_account: Optional[str] = None
    bank_name: Optional[str] = None

    gross_salary: Optional[Decimal] = None
    total_deductions: Optional[Decimal] = None
    net_pay: Optional[Decimal] = None

    earnings_json: Optional[str] = None
    deductions_json: Optional[str] = None

    is_published: Optional[bool] = None
    is_distributed: Optional[bool] = None


class SalarySlipResponse(SalarySlipBase):

    id: int
    generated_at: Optional[datetime] = None
    distributed_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True
    )