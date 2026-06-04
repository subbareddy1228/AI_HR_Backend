# schema/Reports/compliance_reports.py
 
from pydantic import BaseModel, ConfigDict

from typing import List, Optional

from datetime import date
 
 
class ComplianceDashboardStats(BaseModel):

    """Top 4 stat cards on Compliance Dashboard."""

    total_reports: int

    compliant: int

    non_compliant: int

    pending: int

    compliance_rate_pct: float
 
 
class ComplianceReportItem(BaseModel):

    """One row in the compliance report table."""

    sn: int

    report_name: str

    category: str                   # Statutory | Document | Policy

    employee_name: Optional[str] = None

    department: Optional[str] = None

    designation: Optional[str] = None

    location: Optional[str] = None

    state: Optional[str] = None

    reason: Optional[str] = None

    date_of_issue: Optional[date] = None

    resolve_date: Optional[date] = None

    comments: Optional[str] = None

    additional_notes: Optional[str] = None

    salary: Optional[float] = None

    bonus: Optional[float] = None

    deduction: Optional[float] = None

    last_updated: Optional[date] = None

    status: str                     # Compliant | Non-Compliant | Pending | Alert | In Progress | Expired | Missing
 
 
class ComplianceReportList(BaseModel):

    """Full compliance report table response."""

    total: int

    compliant: int

    non_compliant: int

    pending: int

    items: List[ComplianceReportItem]
 
 
class PFComplianceItem(BaseModel):

    """PF compliance row."""

    employee_id: int

    employee_name: str

    department: Optional[str] = None

    basic: float

    pf_employee: float

    pf_employer: float

    total_pf: float

    status: str
 
 
class ESIComplianceItem(BaseModel):

    """ESI compliance row."""

    employee_id: int

    employee_name: str

    gross_salary: float

    esi_employee: float

    esi_eligible: bool

    status: str
 
 
class PTComplianceItem(BaseModel):

    """Professional Tax compliance row."""

    employee_id: int

    employee_name: str

    department: Optional[str] = None

    professional_tax: float

    status: str
 
 
class TDSComplianceItem(BaseModel):

    """TDS compliance row."""

    employee_id: int

    employee_name: str

    gross_salary: float

    tds_deducted: float

    status: str
 
 
class GratuityComplianceItem(BaseModel):

    """Gratuity compliance row."""

    employee_id: int

    last_working_date: str

    gratuity_amount: float

    settlement_status: str
 