from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class WorkHourRuleBase(BaseModel):
    rule_name: str = "Default Policy"
    is_active: Optional[bool] = True

    grace_period_minutes: Optional[int] = 15
    min_daily_hours: Optional[float] = 8.0
    short_leave_categories_count: Optional[int] = 4
    absence_alert_days: Optional[int] = 3
    weekend_rate_multiplier: Optional[float] = 1.5

    late_arrival_rules: Optional[Dict[str, Any]] = Field(default_factory=dict)
    early_departure_rules: Optional[Dict[str, Any]] = Field(default_factory=dict)
    work_hours_half_day_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    short_leave_policies: Optional[Dict[str, Any]] = Field(default_factory=dict)
    continuous_absence_detection: Optional[Dict[str, Any]] = Field(default_factory=dict)
    weekend_working: Optional[Dict[str, Any]] = Field(default_factory=dict)
    holiday_working: Optional[Dict[str, Any]] = Field(default_factory=dict)

    overtime_eligibility: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overtime_calculation: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overtime_caps: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overtime_approval_workflow: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overtime_compensation_settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overtime_reports_settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    overtime_categories: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

    break_configurations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    break_settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    break_auto_deduction_rules: Optional[Dict[str, Any]] = Field(default_factory=dict)

    currency: Optional[str] = "USD"
    time_format: Optional[str] = "24-Hour"
    week_start_day: Optional[str] = "Monday"
    backup_frequency: Optional[str] = "Daily"
    auto_save: Optional[bool] = True
    email_alerts: Optional[bool] = True
    sms_alerts: Optional[bool] = False


class WorkHourRuleCreate(WorkHourRuleBase):
    pass


class WorkHourRuleUpdate(BaseModel):

    rule_name: Optional[str] = None
    is_active: Optional[bool] = None

    grace_period_minutes: Optional[int] = None
    min_daily_hours: Optional[float] = None
    short_leave_categories_count: Optional[int] = None
    absence_alert_days: Optional[int] = None
    weekend_rate_multiplier: Optional[float] = None

    late_arrival_rules: Optional[Dict[str, Any]] = None
    early_departure_rules: Optional[Dict[str, Any]] = None
    work_hours_half_day_config: Optional[Dict[str, Any]] = None
    short_leave_policies: Optional[Dict[str, Any]] = None
    continuous_absence_detection: Optional[Dict[str, Any]] = None
    weekend_working: Optional[Dict[str, Any]] = None
    holiday_working: Optional[Dict[str, Any]] = None

    overtime_eligibility: Optional[Dict[str, Any]] = None
    overtime_calculation: Optional[Dict[str, Any]] = None
    overtime_caps: Optional[Dict[str, Any]] = None
    overtime_approval_workflow: Optional[Dict[str, Any]] = None
    overtime_compensation_settings: Optional[Dict[str, Any]] = None
    overtime_reports_settings: Optional[Dict[str, Any]] = None
    overtime_categories: Optional[List[Dict[str, Any]]] = None

    break_configurations: Optional[List[Dict[str, Any]]] = None
    break_settings: Optional[Dict[str, Any]] = None
    break_auto_deduction_rules: Optional[Dict[str, Any]] = None

    currency: Optional[str] = None
    time_format: Optional[str] = None
    week_start_day: Optional[str] = None
    backup_frequency: Optional[str] = None
    auto_save: Optional[bool] = None
    email_alerts: Optional[bool] = None
    sms_alerts: Optional[bool] = None


class WorkHourRuleResponse(WorkHourRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttendanceStatsResponse(BaseModel):
    active_rules: int
    grace_period_minutes: int
    min_daily_hours: float
    short_leave_categories_count: int
    absence_alert_days: int
    weekend_rate_multiplier: float


class OvertimeStatsResponse(BaseModel):
    avg_overtime_rate: float
    monthly_cap_hours: float
    yearly_cap_hours: float
    approval_type: str
    compensation_types_count: int


class StorageUsageResponse(BaseModel):
    attendance_rules_kb: float
    overtime_management_kb: float
    break_management_kb: float
    system_settings_kb: float
    total_kb: float
