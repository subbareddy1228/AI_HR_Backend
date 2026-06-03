# from fastapi import APIRouter

# router = APIRouter()

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/compliance",
    tags=["Statutory Compliance"]
)

class ComplianceRequest(BaseModel):
    basic: float
    gross_salary: float


@router.post("/calculate")
def calculate_compliance(data: ComplianceRequest):

    pf_employee = data.basic * 0.12

    pf_employer = data.basic * 0.12

    eps = data.basic * 0.0833

    if data.gross_salary <= 21000:
        esi_employee = data.gross_salary * 0.0075
        esi_employer = data.gross_salary * 0.0325
    else:
        esi_employee = 0
        esi_employer = 0

    pt = 200

    annual_income = data.gross_salary * 12

    if annual_income > 700000:
        tds = data.gross_salary * 0.05
    else:
        tds = 0

    return {
        "pf_employee": round(pf_employee, 2),
        "pf_employer": round(pf_employer, 2),
        "eps": round(eps, 2),
        "esi_employee": round(esi_employee, 2),
        "esi_employer": round(esi_employer, 2),
        "professional_tax": pt,
        "tds": round(tds, 2)
    }


@router.get("/pf-report")
def pf_report():

    return {
        "report_name": "PF Monthly Report",
        "status": "Generated"
    }


@router.get("/esi-report")
def esi_report():

    return {
        "report_name": "ESI Monthly Report",
        "status": "Generated"
    }


@router.get("/tds-report")
def tds_report():

    return {
        "report_name": "TDS Quarterly Report",
        "status": "Generated"
    }


@router.get("/form16/{employee_id}")
def generate_form16(employee_id: int):

    return {
        "employee_id": employee_id,
        "message": "Form 16 Generated Successfully"
    }