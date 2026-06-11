

from __future__ import annotations
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from model.Company_Settings.notification_preference import NotificationPreference
from schema.Company_Settings.notification_preference import NotificationPreferenceCreate


def upsert_notification_preferences(
    db:        Session,
    tenant_id: int,
    data:      NotificationPreferenceCreate,
    actor_id:  Optional[int] = None,
) -> NotificationPreference:

    pref = _get_pref(db, tenant_id)

    flat = {
 
        "email_system_alerts":          data.email.system_alerts,
        "email_payroll_updates":        data.email.payroll_updates,
        "email_leave_approvals":        data.email.leave_approvals,
        "email_attendance_reminders":   data.email.attendance_reminders,
        "email_policy_updates":         data.email.policy_updates,
        "email_security_alerts":        data.email.security_alerts,
        "email_weekly_reports":         data.email.weekly_reports,
        "email_monthly_summaries":      data.email.monthly_summaries,

        "push_mobile_alerts":           data.push.mobile_alerts,
        "push_desktop_alerts":          data.push.desktop_alerts,
        "push_instant_updates":         data.push.instant_updates,
        "push_scheduled_summary":       data.push.scheduled_summary,

        "sms_urgent_alerts":            data.sms.urgent_alerts,
        "sms_otp_verification":         data.sms.otp_verification,
        "sms_payroll_credits":          data.sms.payroll_credits,
        "sms_attendance_reminders":     data.sms.attendance_reminders,
    }

    if pref:
        for field, value in flat.items():
            setattr(pref, field, value)
        pref.updated_by = actor_id
    else:
        pref = NotificationPreference(
            tenant_id  = tenant_id,
            updated_by = actor_id,
            **flat,
        )
        db.add(pref)

    db.commit()
    db.refresh(pref)
    return pref


def get_notification_preferences(
    db: Session, tenant_id: int
) -> NotificationPreference:
    pref = _get_pref(db, tenant_id)
    if not pref:
        raise HTTPException(
            status_code=404,
            detail="Notification preferences not configured",
        )
    return pref


def _get_pref(db: Session, tenant_id: int) -> Optional[NotificationPreference]:
    return (
        db.query(NotificationPreference)
        .filter(NotificationPreference.tenant_id == tenant_id)
        .first()
    )
