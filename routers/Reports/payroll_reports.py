# routers/Reports/payroll_reports.py
 
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
 
from core.database import get_db
from core.dependencies import get_current_user
from model.models import User
from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from model.Payroll.bank_transfer import BankTransfer
from model.Payroll.loan_advance import LoanAdvance
from model.Payroll.salary_structure import EmployeeSalaryMapping
from model.onboarding.employee import Employee
 
from schema.Reports.payroll_reports import (
    PayrollReportStats,
    PayrollReportItem,
    CategorySummary,
    RecentActivityItem,
    MonthlyPayrollSummaryItem,
    DepartmentPayrollItem,
    GradeSalaryItem,
    BankTransferSummaryItem,
    LoanOutstandingItem,
    PFRemittanceItem,
    TDSReportItem,
    PayrollVarianceItem,
)
 
router = APIRouter(prefix="/api/reports/payroll", tags=["Payroll Reports"])
 
 
# ══════════════════════════════════════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════════════════════════════════════
 
@router.get("/stats", response_model=PayrollReportStats)
def get_payroll_report_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Top 4 stat cards: Total Reports | Filtered | Selected | Active Filters"""
    return PayrollReportStats(
        total_reports=25,
        filtered=25,
        selected=0,
        active_filters=0,
    )
 
 
# ══════════════════════════════════════════════════════════════════════════════
# REPORT LIST
# ══════════════════════════════════════════════════════════════════════════════
 
@router.get("/list", response_model=List[PayrollReportItem])
def get_payroll_report_list(
    category: Optional[str] = Query(None, description="Salary | Statutory | Deduction | Bank Transfer"),
    report_type: Optional[str] = Query(None, description="Summary | Analysis | Trend | Detailed | Statutory"),
    frequency: Optional[str] = Query(None, description="Monthly | Quarterly | Annual"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full payroll report list — 25 reports as shown in screenshot."""
    reports = [
        {"name": "Monthly Payroll Summary",           "desc": "Comprehensive summary of all payroll transactions",          "category": "Salary",        "type": "Summary",   "frequency": "Monthly"},
        {"name": "Department-wise Payroll Cost",       "desc": "Breakdown of payroll expenses by department with cost alloc","category": "Salary",        "type": "Analysis",  "frequency": "Monthly"},
        {"name": "Location-wise Payroll Cost",         "desc": "Payroll analysis by geographical location",                  "category": "Salary",        "type": "Analysis",  "frequency": "Monthly"},
        {"name": "Grade-wise Salary Analysis",         "desc": "Detailed salary analysis by employee grade levels",          "category": "Salary",        "type": "Analysis",  "frequency": "Monthly"},
        {"name": "Payroll Cost Trends",                "desc": "Historical trend analysis of payroll costs with forecasting","category": "Salary",        "type": "Trend",     "frequency": "Quarterly"},
        {"name": "Salary Component Breakdown",         "desc": "Detailed breakdown of salary components including basic HRA","category": "Salary",        "type": "Detailed",  "frequency": "Monthly"},
        {"name": "Gross vs Net Salary Analysis",       "desc": "Comparative analysis of gross salary versus net salary",     "category": "Salary",        "type": "Analysis",  "frequency": "Monthly"},
        {"name": "Cost to Company (CTC) Reports",      "desc": "Comprehensive CTC analysis including all cost components",   "category": "Salary",        "type": "Summary",   "frequency": "Monthly"},
        {"name": "Average Salary by Department/Grade", "desc": "Average salary calculations grouped by department and grade","category": "Salary",        "type": "Analysis",  "frequency": "Monthly"},
        {"name": "PF Remittance Report",               "desc": "Provident Fund contribution details including employee",     "category": "Statutory",     "type": "Statutory", "frequency": "Monthly"},
        {"name": "ESI Remittance Report",              "desc": "Employee State Insurance contributions and remittance",      "category": "Statutory",     "type": "Statutory", "frequency": "Monthly"},
        {"name": "PT Deduction Report",                "desc": "Professional Tax deductions state-wise",                     "category": "Statutory",     "type": "Statutory", "frequency": "Monthly"},
        {"name": "TDS Deduction Report",               "desc": "Tax Deducted at Source monthly summary",                     "category": "Statutory",     "type": "Statutory", "frequency": "Monthly"},
        {"name": "Form 24Q",                           "desc": "Quarterly TDS return for salary payments",                   "category": "Statutory",     "type": "Statutory", "frequency": "Quarterly"},
        {"name": "ECR (PF Return)",                    "desc": "Electronic Challan cum Return for Provident Fund",           "category": "Statutory",     "type": "Statutory", "frequency": "Monthly"},
        {"name": "Form 16",                            "desc": "Annual TDS certificate for employees",                       "category": "Statutory",     "type": "Statutory", "frequency": "Annual"},
        {"name": "Loan Outstanding Report",            "desc": "Pending loan balances and EMI schedules",                    "category": "Deduction",     "type": "Detailed",  "frequency": "Monthly"},
        {"name": "Advance Recovery Report",            "desc": "Salary advance recovery tracking",                           "category": "Deduction",     "type": "Detailed",  "frequency": "Monthly"},
        {"name": "Other Deduction Summary",            "desc": "Miscellaneous deductions including reimbursements",          "category": "Deduction",     "type": "Summary",   "frequency": "Monthly"},
        {"name": "Arrear Payment Report",              "desc": "Arrear salary payments and adjustments",                     "category": "Deduction",     "type": "Detailed",  "frequency": "Monthly"},
        {"name": "Bank-wise Payment Summary",          "desc": "Salary payment breakdown by bank",                           "category": "Bank Transfer", "type": "Summary",   "frequency": "Monthly"},
        {"name": "Payment File Generation Log",        "desc": "Log of all payment files generated for bank transfer",       "category": "Bank Transfer", "type": "Detailed",  "frequency": "Monthly"},
        {"name": "Failed Payment Tracking",            "desc": "Track failed bank transfer transactions",                    "category": "Bank Transfer", "type": "Detailed",  "frequency": "Monthly"},
        {"name": "Payment Reconciliation Report",      "desc": "Reconcile salary payments with bank statements",             "category": "Bank Transfer", "type": "Analysis",  "frequency": "Monthly"},
        {"name": "Payroll Variance Report",            "desc": "Month-over-month payroll variance analysis",                 "category": "Salary",        "type": "Analysis",  "frequency": "Monthly"},
    ]
 
    result = []
    for r in reports:
        if category and r["category"] != category:
            continue
        if report_type and r["type"] != report_type:
            continue
        if frequency and r["frequency"] != frequency:
            continue
        result.append(PayrollReportItem(
            report_name=r["name"],
            description=r["desc"],
            category=r["category"],
            type=r["type"],
            frequency=r["frequency"],
            status="New",
            last_generated="2024-01-15",
        ))
    return result
 
 
# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY SUMMARY + RECENT ACTIVITY
# ══════════════════════════════════════════════════════════════════════════════
 
@router.get("/category-summary", response_model=List[CategorySummary])
def get_category_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bottom 4 category boxes."""
    return [
        CategorySummary(category="Salary Reports",    description="Monthly payroll, cost analysis, salary breakdowns",   count=9),
        CategorySummary(category="Statutory Reports", description="PF, ESI, PT, IT returns and compliance forms",        count=7),
        CategorySummary(category="Deduction Reports", description="Loan, advances, arrears and other deductions",        count=4),
        CategorySummary(category="Bank Transfers",    description="Payment summaries, reconciliation, failed payments",  count=4),
    ]
 
 
@router.get("/recent-activity", response_model=List[RecentActivityItem])
def get_recent_activity(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recent activity list."""
    return [
        RecentActivityItem(report_name="Monthly Payroll Summary",  action="Generated",  time="10:30 AM"),
        RecentActivityItem(report_name="TDS Deduction Report",     action="Generated",  time="09:15 AM"),
        RecentActivityItem(report_name="PF Remittance Report",     action="Downloaded", time="Yesterday"),
        RecentActivityItem(report_name="Bank-wise Payment Summary",action="Generated",  time="Yesterday"),
    ]
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ACTUAL DATA ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
 
@router.get("/monthly-payroll-summary", response_model=List[MonthlyPayrollSummaryItem])
def monthly_payroll_summary(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Monthly Payroll Summary."""
    stmt = select(PayrollRun)
    if month:
        stmt = stmt.where(PayrollRun.run_month == month)
    if year:
        stmt = stmt.where(PayrollRun.run_year == year)
    runs = db.execute(stmt).scalars().all()
    return [
        MonthlyPayrollSummaryItem(
            run_id=r.id,
            month=r.run_month,
            year=r.run_year,
            total_employees=r.total_employees,
            total_gross=float(r.total_gross),
            total_deductions=float(r.total_deductions),
            total_net_pay=float(r.total_net_pay),
            status=r.status,
            run_date=str(r.run_date),
        )
        for r in runs
    ]
 
 
@router.get("/department-wise-payroll", response_model=List[DepartmentPayrollItem])
def department_wise_payroll(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Department-wise Payroll Cost."""
    results = db.execute(
        select(
            PayrollRunDetail.department,
            func.count(PayrollRunDetail.employee_id).label("headcount"),
            func.sum(PayrollRunDetail.gross_salary).label("total_gross"),
            func.sum(PayrollRunDetail.total_deductions).label("total_deductions"),
            func.sum(PayrollRunDetail.net_pay).label("total_net_pay"),
        ).group_by(PayrollRunDetail.department)
    ).all()
    return [
        DepartmentPayrollItem(
            department=r.department,
            headcount=r.headcount,
            total_gross=float(r.total_gross or 0),
            total_deductions=float(r.total_deductions or 0),
            total_net_pay=float(r.total_net_pay or 0),
        )
        for r in results
    ]
 
 
@router.get("/grade-wise-salary", response_model=List[GradeSalaryItem])
def grade_wise_salary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Grade-wise Salary Analysis."""
    results = db.execute(
        select(
            Employee.grade,
            func.count(Employee.id).label("headcount"),
            func.avg(EmployeeSalaryMapping.annual_ctc).label("avg_ctc"),
        ).join(EmployeeSalaryMapping, EmployeeSalaryMapping.employee_id == Employee.id, isouter=True)
        .group_by(Employee.grade)
    ).all()
    return [
        GradeSalaryItem(
            grade=r.grade,
            headcount=r.headcount,
            avg_ctc=float(r.avg_ctc or 0),
        )
        for r in results
    ]
 
 
@router.get("/bank-transfer-summary", response_model=List[BankTransferSummaryItem])
def bank_transfer_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bank-wise Payment Summary."""
    results = db.execute(
        select(
            BankTransfer.bank_name,
            func.count(BankTransfer.id).label("transaction_count"),
            func.sum(BankTransfer.transfer_amount).label("total_amount"),
            func.sum(func.case((BankTransfer.status == "Failed", 1), else_=0)).label("failed_count"),
        ).group_by(BankTransfer.bank_name)
    ).all()
    return [
        BankTransferSummaryItem(
            bank_name=r.bank_name,
            transaction_count=r.transaction_count,
            total_amount=float(r.total_amount or 0),
            failed_count=r.failed_count,
        )
        for r in results
    ]
 
 
@router.get("/loan-outstanding", response_model=List[LoanOutstandingItem])
def loan_outstanding_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Loan Outstanding Report."""
    loans = db.execute(
        select(LoanAdvance).where(LoanAdvance.status == "Active")
    ).scalars().all()
    return [
        LoanOutstandingItem(
            employee_id=l.employee_id,
            loan_type=l.loan_type,
            amount=float(l.amount),
            approved_amount=float(l.approved_amount or 0),
            emi_amount=float(l.emi_amount or 0),
            total_installments=l.total_installments,
            paid_installments=l.paid_installments,
            outstanding=float((l.approved_amount or 0) - ((l.emi_amount or 0) * l.paid_installments)),
        )
        for l in loans
    ]
 
 
@router.get("/pf-remittance", response_model=List[PFRemittanceItem])
def pf_remittance_report(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """PF Remittance Report."""
    stmt = select(PayrollRunDetail)
    if month or year:
        stmt = stmt.join(PayrollRun, PayrollRun.id == PayrollRunDetail.payroll_run_id)
        if month:
            stmt = stmt.where(PayrollRun.run_month == month)
        if year:
            stmt = stmt.where(PayrollRun.run_year == year)
    details = db.execute(stmt).scalars().all()
    return [
        PFRemittanceItem(
            employee_id=d.employee_id,
            employee_name=d.employee_name,
            department=d.department,
            basic=float(d.basic),
            pf_employee=float(d.pf_employee),
            pf_employer=float(d.pf_employee),
            total_pf=float(d.pf_employee) * 2,
        )
        for d in details
    ]
 
 
@router.get("/tds-report", response_model=List[TDSReportItem])
def tds_report(
    month: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """TDS Deduction Report."""
    stmt = select(PayrollRunDetail)
    if month or year:
        stmt = stmt.join(PayrollRun, PayrollRun.id == PayrollRunDetail.payroll_run_id)
        if month:
            stmt = stmt.where(PayrollRun.run_month == month)
        if year:
            stmt = stmt.where(PayrollRun.run_year == year)
    details = db.execute(stmt).scalars().all()
    return [
        TDSReportItem(
            employee_id=d.employee_id,
            employee_name=d.employee_name,
            gross_salary=float(d.gross_salary),
            tds_deducted=float(d.tds),
        )
        for d in details
    ]
 
 
@router.get("/payroll-variance", response_model=List[PayrollVarianceItem])
def payroll_variance_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Month-over-month Payroll Variance."""
    runs = db.execute(
        select(PayrollRun).order_by(PayrollRun.run_year, PayrollRun.run_month)
    ).scalars().all()
    result = []
    for i, run in enumerate(runs):
        prev = runs[i - 1] if i > 0 else None
        result.append(PayrollVarianceItem(
            month=run.run_month,
            year=run.run_year,
            total_gross=float(run.total_gross),
            total_net_pay=float(run.total_net_pay),
            gross_variance=float(run.total_gross - prev.total_gross) if prev else 0,
            net_variance=float(run.total_net_pay - prev.total_net_pay) if prev else 0,
        ))
    return result