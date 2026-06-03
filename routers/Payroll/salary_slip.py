# from fastapi import APIRouter

# router = APIRouter()

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(
    prefix="/salary-slip",
    tags=["Salary Slip"]
)

class SalarySlipRequest(BaseModel):
    employee_id: int
    employee_name: str
    month: str
    basic: float
    hra: float
    special_allowance: float


@router.post("/generate")
def generate_salary_slip(data: SalarySlipRequest):

    gross_salary = (python -m pip install uvicorn
        data.basic
        + data.hra
        + data.special_allowance
    )

    pf = data.basic * 0.12

    if gross_salary <= 21000:
        esi = gross_salary * 0.0075
    else:
        esi = 0

    pt = 200

    annual_salary = gross_salary * 12

    if annual_salary > 700000:
        tds = gross_salary * 0.05
    else:
        tds = 0

    deductions = pf + esi + pt + tds

    net_salary = gross_salary - deductions

    return {
        "employee_id": data.employee_id,
        "employee_name": data.employee_name,
        "month": data.month,
        "gross_salary": gross_salary,
        python -m venv venv
        "pf": pf,
        "esi": esi,
        "pt": pt,
        "tds": tds,
        "total_deductions": deductions,
        "net_salary": net_salary
    }


@router.get("/{employee_id}")
def get_salary_slip(employee_id: int):

    return {
        "message": f"Salary Slip Details for Employee {employee_id}"
    }


@router.get("/history/{employee_id}")
def salary_history(employee_id: int):

    return {
        "employee_id": employee_id,
        "salary_slips": []
    }


@router.get("/download/{employee_id}")
def download_salary_slip(employee_id: int):

    return {
        "message": f"PDF Download for Employee {employee_id}"
    }