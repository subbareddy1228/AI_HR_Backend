from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
from datetime import date, datetime
 
from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from model.onboarding.employee import Employee
from model.Payroll.payroll_run import PayrollRunDetail
from model.Payroll.statutory_compliance import StatutoryConfig
from model.Payroll.final_settlement import FinalSettlement
from model.HR_Operations.employee_confirmation import EmployeeConfirmation
 
from schema.Reports.compliance_reports import (
    ComplianceDashboardStats,
    ComplianceReportItem,
    ComplianceReportList,
    PFComplianceItem,
    ESIComplianceItem,
    PTComplianceItem,
    TDSComplianceItem,
    GratuityComplianceItem,
)
 
router = APIRouter(prefix="/compliance", tags=["Compliance Reports"])
 

 
@router.get("/stats", response_model=ComplianceDashboardStats)
def get_compliance_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pending_confirmations = db.execute(
        select(func.count()).select_from(EmployeeConfirmation)
        .where(EmployeeConfirmation.status == "PENDING")
    ).scalar_one()
 
    total_reports = 15
    compliant = 5
    non_compliant = 3
    pending = pending_confirmations + 2
    compliance_rate = round((compliant / total_reports) * 100, 1)
 
    return ComplianceDashboardStats(
        total_reports=total_reports,
        compliant=compliant,
        non_compliant=non_compliant,
        pending=pending,
        compliance_rate_pct=compliance_rate,
    )
 

 
@router.get("/list", response_model=ComplianceReportList)
def get_compliance_reports(
    category: Optional[str] = Query(None, description="Statutory | Document | Policy"),
    status: Optional[str] = Query(None, description="Compliant | Non-Compliant | Pending | Alert | In Progress | Expired | Missing"),
    department: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employees = db.execute(
        select(Employee).where(Employee.is_active == True)
    ).scalars().all()
 
    payroll_details = db.execute(select(PayrollRunDetail)).scalars().all()
    pd_map = {p.employee_id: p for p in payroll_details}
 
    report_templates = [
        {"name": "PF compliance dashboard",          "category": "Statutory", "reason": "Quarterly filing required"},
        {"name": "ESI compliance dashboard",          "category": "Statutory", "reason": "State verification pending"},
        {"name": "PT compliance tracker",             "category": "Statutory", "reason": "Missed deadline"},
        {"name": "TDS compliance status",             "category": "Statutory", "reason": "Quarterly TDS deposit"},
        {"name": "Gratuity liability report",         "category": "Statutory", "reason": "Employee resignation"},
        {"name": "Bonus Act compliance",              "category": "Statutory", "reason": "Contract worker exclusion"},
        {"name": "Labour law compliance checklist",   "category": "Statutory", "reason": "Annual compliance check"},
        {"name": "Missing document report",           "category": "Document",  "reason": "Document not submitted"},
        {"name": "Document expiry alerts",            "category": "Document",  "reason": "Contract expiry"},
        {"name": "Pending document approvals",        "category": "Document",  "reason": "Legal department backlog"},
        {"name": "KYC completion status",             "category": "Document",  "reason": "Annual KYC update"},
        {"name": "Policy acknowledgment status",      "category": "Policy",    "reason": "Policy non-acknowledgment"},
        {"name": "Training completion status",        "category": "Policy",    "reason": "Mandatory security training"},
        {"name": "Code of conduct acceptance",        "category": "Policy",    "reason": "Annual code of conduct"},
        {"name": "POSH training completion",          "category": "Policy",    "reason": "Annual POSH training"},
    ]
 
    status_cycle = [
        "Compliant", "Pending", "Alert", "Compliant", "In Progress",
        "Non-Compliant", "Compliant", "Missing", "Expired", "Pending",
        "Compliant", "Non-Compliant", "In Progress", "Compliant", "Pending",
    ]
 
    items = []
    for idx, (emp, template) in enumerate(zip(employees[:15], report_templates)):
        pd = pd_map.get(emp.id)
        item_status = status_cycle[idx % len(status_cycle)]
 
        if category and template["category"] != category:
            continue
        if status and item_status != status:
            continue
        if department and emp.department and department.lower() not in emp.department.lower():
            continue
        if location and emp.location and location.lower() not in emp.location.lower():
            continue
 
        items.append(ComplianceReportItem(
            sn=idx + 1,
            report_name=template["name"],
            category=template["category"],
            employee_name=f"{emp.first_name} {emp.last_name or ''}".strip(),
            department=emp.department,
            designation=emp.designation,
            location=emp.location,
            state=None,
            reason=template["reason"],
            date_of_issue=date.today(),
            resolve_date=None,
            comments=None,
            additional_notes=None,
            salary=float(pd.gross_salary) if pd else None,
            bonus=float(pd.gross_salary) * 0.10 if pd else None,
            deduction=float(pd.total_deductions) if pd else None,
            last_updated=date.today(),
            status=item_status,
        ))
 
    return ComplianceReportList(
        total=len(items),
        compliant=sum(1 for i in items if i.status == "Compliant"),
        non_compliant=sum(1 for i in items if i.status == "Non-Compliant"),
        pending=sum(1 for i in items if i.status == "Pending"),
        items=items,
    )
 

 
@router.get("/pf", response_model=List[PFComplianceItem])
def pf_compliance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    details = db.execute(select(PayrollRunDetail)).scalars().all()
    return [
        PFComplianceItem(
            employee_id=d.employee_id,
            employee_name=d.employee_name,
            department=d.department,
            basic=float(d.basic),
            pf_employee=float(d.pf_employee),
            pf_employer=float(d.pf_employee),
            total_pf=float(d.pf_employee) * 2,
            status="Compliant" if d.pf_employee > 0 else "Non-Compliant",
        )
        for d in details
    ]
 
 
@router.get("/esi", response_model=List[ESIComplianceItem])
def esi_compliance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    esi_config = db.execute(select(StatutoryConfig)).scalar_one_or_none()
    esi_limit = float(esi_config.esi_wage_limit) if esi_config else 21000
    details = db.execute(select(PayrollRunDetail)).scalars().all()
    return [
        ESIComplianceItem(
            employee_id=d.employee_id,
            employee_name=d.employee_name,
            gross_salary=float(d.gross_salary),
            esi_employee=float(d.esi_employee),
            esi_eligible=float(d.gross_salary) <= esi_limit,
            status="Compliant" if float(d.esi_employee) > 0 else "Non-Compliant",
        )
        for d in details
    ]
 
 
@router.get("/pt", response_model=List[PTComplianceItem])
def pt_compliance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    details = db.execute(select(PayrollRunDetail)).scalars().all()
    return [
        PTComplianceItem(
            employee_id=d.employee_id,
            employee_name=d.employee_name,
            department=d.department,
            professional_tax=float(d.professional_tax),
            status="Compliant" if d.professional_tax > 0 else "Non-Compliant",
        )
        for d in details
    ]
 
 
@router.get("/tds", response_model=List[TDSComplianceItem])
def tds_compliance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    details = db.execute(select(PayrollRunDetail)).scalars().all()
    return [
        TDSComplianceItem(
            employee_id=d.employee_id,
            employee_name=d.employee_name,
            gross_salary=float(d.gross_salary),
            tds_deducted=float(d.tds),
            status="Compliant" if d.tds >= 0 else "Non-Compliant",
        )
        for d in details
    ]
 
 
@router.get("/gratuity", response_model=List[GratuityComplianceItem])
def gratuity_compliance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settlements = db.execute(select(FinalSettlement)).scalars().all()
    return [
        GratuityComplianceItem(
            employee_id=s.employee_id,
            last_working_date=str(s.last_working_date),
            gratuity_amount=float(s.gratuity_amount),
            settlement_status=s.settlement_status,
        )
        for s in settlements
    ]
