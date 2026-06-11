

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel



class EmailNotificationSettings(BaseModel):
    system_alerts:          bool = True
    payroll_updates:        bool = True
    leave_approvals:        bool = True
    attendance_reminders:   bool = True
    policy_updates:         bool = True
    security_alerts:        bool = True
    weekly_reports:         bool = False
    monthly_summaries:      bool = True



class PushNotificationSettings(BaseModel):
    mobile_alerts:      bool = True
    desktop_alerts:     bool = False
    instant_updates:    bool = True
    scheduled_summary:  bool = False



class SMSNotificationSettings(BaseModel):
    urgent_alerts:          bool = True
    otp_verification:       bool = True
    payroll_credits:        bool = False
    attendance_reminders:   bool = False



class NotificationPreferenceCreate(BaseModel):
    email:  EmailNotificationSettings = EmailNotificationSettings()
    push:   PushNotificationSettings  = PushNotificationSettings()
    sms:    SMSNotificationSettings   = SMSNotificationSettings()



class NotificationPreferenceResponse(BaseModel):
    id:         int
    tenant_id:  int

    # Email
    email_system_alerts:        bool
    email_payroll_updates:      bool
    email_leave_approvals:      bool
    email_attendance_reminders: bool
    email_policy_updates:       bool
    email_security_alerts:      bool
    email_weekly_reports:       bool
    email_monthly_summaries:    bool

    
    push_mobile_alerts:     bool
    push_desktop_alerts:    bool
    push_instant_updates:   bool
    push_scheduled_summary: bool

 
    sms_urgent_alerts:          bool
    sms_otp_verification:       bool
    sms_payroll_credits:        bool
    sms_attendance_reminders:   bool

 
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
