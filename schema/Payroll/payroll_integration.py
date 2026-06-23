from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal




class IntegrationFilter(BaseModel):
    month:      Optional[int] = None
    year:       Optional[int] = None
    department: Optional[str] = None
    location:   Optional[str] = None
    status:     Optional[str] = None




class DashboardSummary(BaseModel):
    real_time_sync_hours: float         
    last_sync_label:      str            
    data_status:          str            
    total_loss_of_pay:     Decimal
    loss_of_pay_employee_count: int
    overtime_pay:          Decimal
    overtime_avg_per_employee: float
    holiday_pay:           Decimal
    leave_without_pay_days: int
    leave_without_pay_deduction: Decimal
    pending_corrections:   int
    processed_payroll:     Decimal
    processed_employee_count: int




class FreezeStatusOut(BaseModel):
    id:                  int
    run_month:           int
    run_year:            int
    status:              str           
    freeze_window_days:  int
    frozen_at:           Optional[datetime]
    frozen_by:           Optional[str]
    next_freeze_start:   Optional[date]
    next_freeze_end:     Optional[date]

    model_config = ConfigDict(from_attributes=True)


class FreezeAction(BaseModel):
    requested_by: str = "Payroll Admin"




class PipelineStep(BaseModel):
    step_number: int
    title:       str
    subtitle:    str
    status:      str   


class PayrollProcessingStatus(BaseModel):
    current_period_start: date
    current_period_end:   date
    next_run_date:         date
    steps:                List[PipelineStep]




class ImpactAnalysisPoint(BaseModel):
    label:         str    
    basic_salary:  Decimal
    net_pay:       Decimal
    loss_of_pay:   Decimal


class PayrollImpactAnalysis(BaseModel):
    period:  str
    points:  List[ImpactAnalysisPoint]




class DeductionAdditionItem(BaseModel):
    label:       str
    amount:      Decimal
    pct_change:  Optional[float] = None   


class TopDeductionsAdditions(BaseModel):
    deductions: List[DeductionAdditionItem]
    additions:  List[DeductionAdditionItem]




class SyncStatusCard(BaseModel):
    label:        str          
    last_sync_at: Optional[datetime]
    sync_frequency_minutes: int
    is_healthy:   bool


class DataFreshnessCard(BaseModel):
    hours_ago: float
    latency_minutes: int


class SystemHealthCard(BaseModel):
    issues_found: int
    warnings: int


class IntegrationStatusOut(BaseModel):
    attendance_sync: SyncStatusCard
    payroll_sync:    SyncStatusCard
    data_freshness:  DataFreshnessCard
    system_health:   SystemHealthCard




class ActionItemOut(BaseModel):
    id:           int
    category:     str       
    title:        str
    description:  Optional[str]
    severity:     str
    action_label: Optional[str]
    is_resolved:  bool
    created_at:   datetime

    model_config = ConfigDict(from_attributes=True)


class ActionResolve(BaseModel):
    resolved_by: Optional[str] = None




class RealtimeDataFlowOut(BaseModel):
    sync_frequency_minutes: int
    success_rate_pct:       float
    last_sync_at:           Optional[datetime]


class SyncNowRequest(BaseModel):
    triggered_by: str = "Payroll Admin"




class CalculationRuleOut(BaseModel):
    id:          int
    rule_key:    str
    title:       str
    description: Optional[str]
    formula:     Optional[str]
    multiplier:  float
    is_active:   bool
    icon_color:  str

    model_config = ConfigDict(from_attributes=True)


class CalculationRuleUpdate(BaseModel):
    title:       Optional[str]   = None
    description: Optional[str]   = None
    formula:     Optional[str]   = None
    multiplier:  Optional[float] = None
    is_active:   Optional[bool]  = None




class PayrollCalculationRow(BaseModel):
    employee_id:    int
    employee_name:  str
    department:     Optional[str]
    present_days:   int
    absent_days:    int
    overtime_hours: float
    holiday_work_days: int
    basic_salary:   Decimal
    loss_of_pay:    Decimal
    overtime_pay:   Decimal
    net_pay:        Decimal
    status:         str   


class PayrollCalculationOut(BaseModel):
    rows:            List[PayrollCalculationRow]
    total_employees: int
    total_net_pay:   Decimal


class RunPayrollRequest(BaseModel):
    month: int
    year:  int
    department: Optional[str] = None
    location:   Optional[str] = None




class CorrectionCreate(BaseModel):
    employee_id:     int
    original_date:   date
    correction_type: str            
    original_value:  Optional[str] = None
    corrected_value: Optional[str] = None
    payroll_impact:  Decimal = Decimal("0.00")
    requested_by:    str


class CorrectionUpdate(BaseModel):
    corrected_value: Optional[str]    = None
    payroll_impact:  Optional[Decimal] = None
    status:          Optional[str]     = None   
    reviewed_by:     Optional[str]     = None


class CorrectionOut(BaseModel):
    id:              int
    employee_id:     int
    employee_name:   Optional[str] = None
    employee_code:   Optional[str] = None
    original_date:   date
    correction_type: str
    original_value:  Optional[str]
    corrected_value: Optional[str]
    payroll_impact:  Decimal
    status:          str
    requested_by:    Optional[str]
    requested_at:    Optional[date]

    model_config = ConfigDict(from_attributes=True)




class ReportOut(BaseModel):
    id:             int
    report_key:     str
    title:          str
    category:       str
    description:    Optional[str]
    frequency:      str
    formats:        str
    column_count:   int
    last_generated: Optional[date]

    model_config = ConfigDict(from_attributes=True)




class IntegrationSettingsOut(BaseModel):
    id: int
    payroll_processing_password: str = "********"   
    two_factor_enabled: bool
    session_timeout_minutes: int
    attendance_sync_frequency_minutes: int
    payroll_sync_frequency_minutes: int
    retry_failed_syncs_count: int
    email_notifications: bool
    push_notifications: bool
    sms_notifications: bool
    alert_threshold: str
    overtime_multiplier: float
    holiday_pay_multiplier: float
    monthly_working_days: int
    daily_hours: float

    model_config = ConfigDict(from_attributes=True)


class IntegrationSettingsUpdate(BaseModel):
    payroll_processing_password:       Optional[str]  = None   
    two_factor_enabled:                Optional[bool] = None
    session_timeout_minutes:           Optional[int]  = None
    attendance_sync_frequency_minutes: Optional[int]  = None
    payroll_sync_frequency_minutes:    Optional[int]  = None
    retry_failed_syncs_count:          Optional[int]  = None
    email_notifications:               Optional[bool] = None
    push_notifications:                Optional[bool] = None
    sms_notifications:                 Optional[bool] = None
    alert_threshold:                   Optional[str]  = None
    overtime_multiplier:               Optional[float] = None
    holiday_pay_multiplier:            Optional[float] = None
    monthly_working_days:              Optional[int]  = None
    daily_hours:                       Optional[float] = None