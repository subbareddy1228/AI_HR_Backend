from fastapi import APIRouter
from pydantic import BaseModel
from trio import TaskStatus
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

    gross_salary = (
        data.basic
        + data.hra
        + data.special_allowance
    )

    # PF Calculation (12% of Basic)
    pf = data.basic * 0.12

    # ESI Calculation
    esi = gross_salary * 0.0075 if gross_salary <= 21000 else 0

    # Professional Tax
    pt = 200

    # Annual Salary
    annual_salary = gross_salary * 12

    # TDS Calculation
    tds = gross_salary * 0.05 if annual_salary > 700000 else 0

    # Total Deductions
    total_deductions = pf + esi + pt + tds

    # Net Salary
    net_salary = gross_salary - total_deductions

    return {
        "employee_id": data.employee_id,
        "employee_name": data.employee_name,
        "month": data.month,
        "basic": data.basic,
        "hra": data.hra,
        "special_allowance": data.special_allowance,
        "gross_salary": round(gross_salary, 2),
        "pf": round(pf, 2),
        "esi": round(esi, 2),
        "pt": round(pt, 2),
        "tds": round(tds, 2),
        "total_deductions": round(total_deductions, 2),
        "net_salary": round(net_salary, 2)
    }


@router.get("/{employee_id}")
def get_salary_slip(employee_id: int):
    return {
        "employee_id": employee_id,
        "message": f"Salary Slip Details for Employee {employee_id}"
    }


@router.get("/history/{employee_id}")
def salary_history(employee_id: int):
    return {
        "employee_id": employee_id,
        "salary_slips": [
            {
                "month": "January",
                "net_salary": 45000
            },
            {
                "month": "February",
                "net_salary": 46000
            }
        ]
    }


@router.get("/download/{employee_id}")
def download_salary_slip(employee_id: int):
    return {
        "employee_id": employee_id,
        "message": f"Salary Slip PDF Download for Employee {employee_id}"
    }