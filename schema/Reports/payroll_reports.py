
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
    category: str         
    type: str              
    frequency: str          
    status: str           
    last_generated: Optional[str] = None
 
 
class CategorySummary(BaseModel):

    category: str
    description: str
    count: int
 
 
class RecentActivityItem(BaseModel):

    report_name: str
    action: str            
    time: str
 
 
class MonthlyPayrollSummaryItem(BaseModel):
   
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
  
    department: Optional[str]
    headcount: int
    total_gross: float
    total_deductions: float
    total_net_pay: float
 
 
class GradeSalaryItem(BaseModel):
   
    grade: Optional[str]
    headcount: int
    avg_ctc: float
 
 
class BankTransferSummaryItem(BaseModel):
  
    bank_name: str
    transaction_count: int
    total_amount: float
    failed_count: int
 
 
class LoanOutstandingItem(BaseModel):
 
    employee_id: int
    loan_type: str
    amount: float
    approved_amount: float
    emi_amount: float
    total_installments: Optional[int]
    paid_installments: int
    outstanding: float
 
 
class PFRemittanceItem(BaseModel):
  
    employee_id: int
    employee_name: str
    department: Optional[str]
    basic: float
    pf_employee: float
    pf_employer: float
    total_pf: float
 
 
class TDSReportItem(BaseModel):
    
    employee_id: int
    employee_name: str
    gross_salary: float
    tds_deducted: float
 
 
class PayrollVarianceItem(BaseModel):

    month: int
    year: int
    total_gross: float
    total_net_pay: float
    gross_variance: float
    net_variance: float
    