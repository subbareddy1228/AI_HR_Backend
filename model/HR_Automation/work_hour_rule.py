from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON
from core.database import Base
from datetime import datetime


class WorkHourRule(Base):

    __tablename__ = "work_hour_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(255), unique=True, nullable=False, default="Default Policy")
    is_active = Column(Boolean, default=True)

    grace_period_minutes = Column(Integer, default=15)         
    min_daily_hours = Column(Float, default=8.0)                
    short_leave_categories_count = Column(Integer, default=4) 
    absence_alert_days = Column(Integer, default=3)             
    weekend_rate_multiplier = Column(Float, default=1.5)       

    late_arrival_rules = Column(JSON, nullable=True, default=dict)
  
    early_departure_rules = Column(JSON, nullable=True, default=dict)

    work_hours_half_day_config = Column(JSON, nullable=True, default=dict)
 
    short_leave_policies = Column(JSON, nullable=True, default=dict)

    continuous_absence_detection = Column(JSON, nullable=True, default=dict)

    weekend_working = Column(JSON, nullable=True, default=dict)

    holiday_working = Column(JSON, nullable=True, default=dict)
    overtime_eligibility = Column(JSON, nullable=True, default=dict)

    overtime_calculation = Column(JSON, nullable=True, default=dict)

    overtime_caps = Column(JSON, nullable=True, default=dict)

    overtime_approval_workflow = Column(JSON, nullable=True, default=dict)

    overtime_compensation_settings = Column(JSON, nullable=True, default=dict)
 
    overtime_reports_settings = Column(JSON, nullable=True, default=dict)

    overtime_categories = Column(JSON, nullable=True, default=list)

    break_configurations = Column(JSON, nullable=True, default=list)

    break_settings = Column(JSON, nullable=True, default=dict)

    break_auto_deduction_rules = Column(JSON, nullable=True, default=dict)

    currency = Column(String(10), default="USD")
    time_format = Column(String(10), default="24-Hour")
    week_start_day = Column(String(15), default="Monday")
    backup_frequency = Column(String(15), default="Daily")
    auto_save = Column(Boolean, default=True)
    email_alerts = Column(Boolean, default=True)
    sms_alerts = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
