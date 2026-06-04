# schema/Reports/payroll_reports.py
 
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from decimal import Decimal
 
 
class PayrollReportStats(BaseModel):
    """Top 4 stat cards on Payroll Reports page."""
    total_reports: int
    filtered: int
    selected: int
    active_filters: int
 
 
class PayrollReportItem(BaseModel):
    """One row in the payroll report list."""
    report_name: str
    description: str
    category: str           # Salary | Statutory | Deduction | Bank Transfer
    type: str               # Summary | Analysis | Trend | Detailed | Statutory
    frequency: str          # Monthly | Quarterly | Annual
    status: str             # New | Generated | Downloaded
    last_generated: Optional[str] = None
 
 
class CategorySummary(BaseModel):
    """Bottom 4 category boxes."""
    category: str
    description: str
    count: int
 
 
class RecentActivityItem(BaseModel):
    """Recent activity list."""
    report_name: str
    action: str             # Generated | Downloaded | Viewed
    time: str
 
 
class MonthlyPayrollSummaryItem(BaseModel):
    """Monthly Payroll Summary row."""
    run_id: int
    month: int
    year: int
    total_employees: int
    total_gross: float
    total_deductions: float
    total_net_pay: float
    status: str
    run_date: str
 
 
class DepartmentPayrollItem(BaseModel):
    """Department-wise Payroll Cost row."""
    department: Optional[str]
    headcount: int
    total_gross: float
    total_deductions: float
    total_net_pay: float
 
 
class GradeSalaryItem(BaseModel):
    """Grade-wise Salary Analysis row."""
    grade: Optional[str]
    headcount: int
    avg_ctc: float
 
 
class BankTransferSummaryItem(BaseModel):
    """Bank-wise Payment Summary row."""
    bank_name: str
    transaction_count: int
    total_amount: float
    failed_count: int
 
 
class LoanOutstandingItem(BaseModel):
    """Loan Outstanding Report row."""
    employee_id: int
    loan_type: str
    amount: float
    approved_amount: float
    emi_amount: float
    total_installments: Optional[int]
    paid_installments: int
    outstanding: float
 
 
class PFRemittanceItem(BaseModel):
    """PF Remittance Report row."""
    employee_id: int
    employee_name: str
    department: Optional[str]
    basic: float
    pf_employee: float
    pf_employer: float
    total_pf: float
 
 
class TDSReportItem(BaseModel):
    """TDS Deduction Report row."""
    employee_id: int
    employee_name: str
    gross_salary: float
    tds_deducted: float
 
 
class PayrollVarianceItem(BaseModel):
    """Month-over-month Payroll Variance row."""
    month: int
    year: int
    total_gross: float
    total_net_pay: float
    gross_variance: float
    net_variance: float
    