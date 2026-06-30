from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException
from datetime import datetime
from typing import Optional

from model.HR_Automation.work_hour_rule import WorkHourRule
from schema.HR_Automation.work_hour_rule import (
    WorkHourRuleCreate,
    WorkHourRuleUpdate,
)


def get_rule_or_404(db: Session, rule_id: int) -> WorkHourRule:
    rule = db.execute(
        select(WorkHourRule).where(WorkHourRule.id == rule_id)
    ).scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Work hour rule not found")
    return rule


def create_rule(db: Session, payload: WorkHourRuleCreate) -> WorkHourRule:
    existing = db.execute(
        select(WorkHourRule).where(WorkHourRule.rule_name == payload.rule_name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Rule name already exists")

    rule = WorkHourRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_rules(db: Session, active_only: bool = True) -> list:
    stmt = select(WorkHourRule)
    if active_only:
        stmt = stmt.where(WorkHourRule.is_active == True)
    return db.execute(stmt.order_by(WorkHourRule.id)).scalars().all()


def get_rule(db: Session, rule_id: int) -> WorkHourRule:
    return get_rule_or_404(db, rule_id)


def get_active_policy(db: Session) -> WorkHourRule:

    rule = db.execute(
        select(WorkHourRule).where(WorkHourRule.is_active == True)
    ).scalars().first()

    if not rule:
        rule = WorkHourRule(rule_name="Default Policy")
        db.add(rule)
        db.commit()
        db.refresh(rule)

    return rule


def update_rule(db: Session, rule_id: int, payload: WorkHourRuleUpdate) -> WorkHourRule:
    rule = get_rule_or_404(db, rule_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, key, value)
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def update_attendance_tab(db: Session, rule_id: int, attendance_payload: dict) -> WorkHourRule:
   
    rule = get_rule_or_404(db, rule_id)
    allowed_keys = {
        "grace_period_minutes", "min_daily_hours", "short_leave_categories_count",
        "absence_alert_days", "weekend_rate_multiplier", "late_arrival_rules",
        "early_departure_rules", "work_hours_half_day_config", "short_leave_policies",
        "continuous_absence_detection", "weekend_working", "holiday_working",
    }
    for key, value in attendance_payload.items():
        if key in allowed_keys:
            setattr(rule, key, value)
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def update_overtime_tab(db: Session, rule_id: int, overtime_payload: dict) -> WorkHourRule:
    
    rule = get_rule_or_404(db, rule_id)
    allowed_keys = {
        "overtime_eligibility", "overtime_calculation", "overtime_caps",
        "overtime_approval_workflow", "overtime_compensation_settings",
        "overtime_reports_settings", "overtime_categories",
    }
    for key, value in overtime_payload.items():
        if key in allowed_keys:
            setattr(rule, key, value)
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def update_breaks_tab(db: Session, rule_id: int, breaks_payload: dict) -> WorkHourRule:
    """Partial update scoped to just the Breaks tab's JSON sub-sections."""
    rule = get_rule_or_404(db, rule_id)
    allowed_keys = {
        "break_configurations", "break_settings", "break_auto_deduction_rules",
    }
    for key, value in breaks_payload.items():
        if key in allowed_keys:
            setattr(rule, key, value)
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def update_settings_tab(db: Session, rule_id: int, settings_payload: dict) -> WorkHourRule:
    
    rule = get_rule_or_404(db, rule_id)
    allowed_keys = {
        "currency", "time_format", "week_start_day", "backup_frequency",
        "auto_save", "email_alerts", "sms_alerts",
    }
    for key, value in settings_payload.items():
        if key in allowed_keys:
            setattr(rule, key, value)
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> dict:
    rule = get_rule_or_404(db, rule_id)
    db.delete(rule)
    db.commit()
    return {"message": "Work hour rule deleted successfully"}


def get_attendance_stats(db: Session, rule_id: Optional[int] = None) -> dict:
    
    rule = get_rule_or_404(db, rule_id) if rule_id else get_active_policy(db)
    active_count = len(list_rules(db, active_only=True))
    return {
        "active_rules": active_count,
        "grace_period_minutes": rule.grace_period_minutes,
        "min_daily_hours": rule.min_daily_hours,
        "short_leave_categories_count": rule.short_leave_categories_count,
        "absence_alert_days": rule.absence_alert_days,
        "weekend_rate_multiplier": rule.weekend_rate_multiplier,
    }


def get_overtime_stats(db: Session, rule_id: Optional[int] = None) -> dict:
   
    rule = get_rule_or_404(db, rule_id) if rule_id else get_active_policy(db)
    calc = rule.overtime_calculation or {}
    caps = rule.overtime_caps or {}
    workflow = rule.overtime_approval_workflow or {}
    comp = rule.overtime_compensation_settings or {}

    weekday_rate = calc.get("weekday_rate", 1.5)
    weekend_rate = calc.get("weekend_rate", 2.0)
    avg_rate = round((weekday_rate + weekend_rate) / 2, 2)

    return {
        "avg_overtime_rate": avg_rate,
        "monthly_cap_hours": caps.get("monthly_cap_hours", 80),
        "yearly_cap_hours": caps.get("yearly_cap_hours", 300),
        "approval_type": workflow.get("workflow_type", "Multi-level"),
        "compensation_types_count": len(
            {c.get("compensation_type") for c in (rule.overtime_categories or [])}
        ) or 1,
    }


def get_storage_usage(db: Session) -> dict:

    import json

    rule = get_active_policy(db)

    def size_kb(*field_names) -> float:
        total_bytes = 0
        for name in field_names:
            value = getattr(rule, name, None)
            if value:
                total_bytes += len(json.dumps(value).encode("utf-8"))
        return round(total_bytes / 1024, 2)

    attendance_kb = size_kb(
        "late_arrival_rules", "early_departure_rules", "work_hours_half_day_config",
        "short_leave_policies", "continuous_absence_detection",
        "weekend_working", "holiday_working",
    )
    overtime_kb = size_kb(
        "overtime_eligibility", "overtime_calculation", "overtime_caps",
        "overtime_approval_workflow", "overtime_compensation_settings",
        "overtime_reports_settings", "overtime_categories",
    )
    breaks_kb = size_kb(
        "break_configurations", "break_settings", "break_auto_deduction_rules",
    )
    settings_kb = round(
        len(json.dumps({
            "currency": rule.currency,
            "time_format": rule.time_format,
            "week_start_day": rule.week_start_day,
            "backup_frequency": rule.backup_frequency,
        }).encode("utf-8")) / 1024,
        2,
    )

    total = round(attendance_kb + overtime_kb + breaks_kb + settings_kb, 2)

    return {
        "attendance_rules_kb": attendance_kb,
        "overtime_management_kb": overtime_kb,
        "break_management_kb": breaks_kb,
        "system_settings_kb": settings_kb,
        "total_kb": total,
    }
