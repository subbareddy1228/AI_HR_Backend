from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    Numeric, Text, ForeignKey
)
from core.database import Base


class AttendanceFreeze(Base):
   
    __tablename__ = "attendance_freezes"

    id            = Column(Integer, primary_key=True, index=True)
    run_month     = Column(Integer, nullable=False)
    run_year      = Column(Integer, nullable=False)

    status        = Column(String(20), nullable=False, default="UNFROZEN")  
    freeze_window_days = Column(Integer, default=3)

    frozen_at     = Column(DateTime, nullable=True)
    frozen_by     = Column(String(255), nullable=True)
    unfrozen_at   = Column(DateTime, nullable=True)

    next_freeze_start = Column(Date, nullable=True)   
    next_freeze_end    = Column(Date, nullable=True)

    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationSyncLog(Base):
    
    __tablename__ = "integration_sync_logs"

    id            = Column(Integer, primary_key=True, index=True)
    sync_type     = Column(String(50), nullable=False)  
    status        = Column(String(20), default="success") 
    duration_minutes = Column(Integer, default=15)
    records_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    synced_at     = Column(DateTime, default=datetime.utcnow)


class SystemHealthIssue(Base):
    
    __tablename__ = "system_health_issues"

    id          = Column(Integer, primary_key=True, index=True)
    severity    = Column(String(20), default="warning")  
    message     = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class PayrollCalculationRule(Base):
    
    __tablename__ = "payroll_calculation_rules"

    id          = Column(Integer, primary_key=True, index=True)
    rule_key    = Column(String(50), unique=True, nullable=False)  
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    formula     = Column(String(255), nullable=True)   
    multiplier  = Column(Float, default=1.0)            
    is_active   = Column(Boolean, default=True)
    icon_color  = Column(String(20), default="red")     

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AttendanceCorrection(Base):
   
    __tablename__ = "attendance_corrections"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    original_date   = Column(Date, nullable=False)
    correction_type = Column(String(50), nullable=False) 

    original_value  = Column(String(255), nullable=True)  
    corrected_value = Column(String(255), nullable=True)   

    payroll_impact  = Column(Numeric(12, 2), default=0)    

    status          = Column(String(20), default="PENDING")  

    requested_by    = Column(String(255), nullable=True)   
    requested_at    = Column(Date, nullable=True)

    reviewed_by     = Column(String(255), nullable=True)
    reviewed_at     = Column(DateTime, nullable=True)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationActionItem(Base):
   
    __tablename__ = "integration_action_items"

    id          = Column(Integer, primary_key=True, index=True)
    category    = Column(String(30), nullable=False)   
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity    = Column(String(20), default="warning")  

    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

    action_label = Column(String(50), nullable=True)   

    created_at  = Column(DateTime, default=datetime.utcnow)


class IntegrationSettings(Base):
    
    __tablename__ = "integration_settings"

    id = Column(Integer, primary_key=True, index=True)

    
    payroll_processing_password = Column(String(255), nullable=True)   
    two_factor_enabled           = Column(Boolean, default=True)
    session_timeout_minutes      = Column(Integer, default=15)

    
    attendance_sync_frequency_minutes = Column(Integer, default=15)
    payroll_sync_frequency_minutes    = Column(Integer, default=30)
    retry_failed_syncs_count          = Column(Integer, default=3)

    
    email_notifications = Column(Boolean, default=True)
    push_notifications   = Column(Boolean, default=True)
    sms_notifications    = Column(Boolean, default=False)
    alert_threshold      = Column(String(50), default="High: Any error")

    
    overtime_multiplier   = Column(Float, default=1.5)
    holiday_pay_multiplier = Column(Float, default=2.0)
    monthly_working_days  = Column(Integer, default=30)
    daily_hours           = Column(Float, default=8.0)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PayrollIntegrationReport(Base):
   
    __tablename__ = "payroll_integration_reports"

    id            = Column(Integer, primary_key=True, index=True)
    report_key    = Column(String(50), unique=True, nullable=False)
    title         = Column(String(255), nullable=False)
    category      = Column(String(30), nullable=False)   
    description   = Column(Text, nullable=True)
    frequency     = Column(String(20), default="monthly")  
    formats       = Column(String(100), default="PDF, Excel")
    column_count  = Column(Integer, default=5)
    last_generated = Column(Date, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)