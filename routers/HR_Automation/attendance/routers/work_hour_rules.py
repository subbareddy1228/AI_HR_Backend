# router/work_hour_rules_router.py
#
# All endpoints for Work Hour Rules & Policies.
# Register in main.py:
#   from router.work_hour_rules_router import router as work_hour_rules_router
#   app.include_router(work_hour_rules_router, prefix="/api/attendance")
#
# Final URL map:
#   GET    /api/attendance/work-hour-rules/                              ← page load
#   GET    /api/attendance/work-hour-rules/compliance-stats             ← stats bar (dynamic)
#   POST   /api/attendance/work-hour-rules/save                         ← Save Changes button
#   POST   /api/attendance/work-hour-rules/save-tab                     ← single tab auto-save
#   POST   /api/attendance/work-hour-rules/reset                        ← Reset button
#   GET    /api/attendance/work-hour-rules/export                       ← Export button (JSON)
#   POST   /api/attendance/work-hour-rules/import                       ← Import button (JSON)
#   POST   /api/attendance/work-hour-rules/backup                       ← Backup button (Settings tab)
#   DELETE /api/attendance/work-hour-rules/cache                        ← Clear Cache button (Settings tab)
#
#   GET    /api/attendance/work-hour-rules/settings                     ← Settings tab load
#   PUT    /api/attendance/work-hour-rules/settings                     ← Settings tab save
#
# Short-leave category sub-endpoints (Attendance tab):
#   POST   /api/attendance/work-hour-rules/attendance/short-leave/category
#   PUT    /api/attendance/work-hour-rules/attendance/short-leave/category/{cat_id}
#   DELETE /api/attendance/work-hour-rules/attendance/short-leave/category/{cat_id}
#
# Overtime category sub-endpoints (Overtime tab):
#   POST   /api/attendance/work-hour-rules/overtime/category
#   PUT    /api/attendance/work-hour-rules/overtime/category/{cat_id}
#   DELETE /api/attendance/work-hour-rules/overtime/category/{cat_id}
#   POST   /api/attendance/work-hour-rules/overtime/category/{cat_id}/duplicate  ← ADDED
#
# Break sub-endpoints (Breaks tab):
#   POST   /api/attendance/work-hour-rules/breaks/break
#   PUT    /api/attendance/work-hour-rules/breaks/break/{break_id}
#   DELETE /api/attendance/work-hour-rules/breaks/break/{break_id}
#   POST   /api/attendance/work-hour-rules/breaks/break/{break_id}/duplicate     ← ADDED

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db
from schema.HR_Automation.work_hour_rule import (
    WorkHourRuleConfigOut,
    ComplianceStatsOut,
    ResetOut,
    SaveAllIn,
    SaveTabIn,
    ShortLeaveCategory,
    OvertimeCategory,
    BreakItem,
    WorkHourSettingsIn,      # NEW
    WorkHourSettingsOut,     # NEW
)
from services.HR_Automation.work_hour_rule_service import (
    get_config,
    get_compliance_stats,
    save_all,
    save_tab,
    reset_config,
    export_config,
    import_config,
    _get_or_create,
    _to_out)


router = APIRouter(prefix="/api/attendance/work-hour-rules", tags=["Work Hour Rules"])

VALID_TABS = {"attendance", "overtime", "breaks", "settings"}  # "settings" was missing


# ─────────────────────────────────────────────────────────────────────────────
# 1. Page load — full config
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/",
    response_model=WorkHourRuleConfigOut,
    summary="Page load — returns full Work Hour Rules config for all 4 tabs")
def get_work_hour_rules(
    db: Session = Depends(get_db)
):
    """
    Called when the page mounts.
    Returns attendance_rules, overtime_rules, break_rules, and settings.
    Seeds defaults if no config row exists yet.
    """
    return get_config(db)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Compliance stats bar (dynamic — not hardcoded)
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/compliance-stats",
    response_model=ComplianceStatsOut,
    summary="Stats bar — Active Rules / Grace Period / Min Hours / Short Leave / Absence Alert / Weekend Rate")
def compliance_stats(
    db: Session = Depends(get_db)
):
    """
    FIX: compliance score must be computed dynamically from the stored config,
    not hardcoded to 95 or 150.

    Score formula (matches frontend):
      base = 100
      +10  for each active attendance sub-rule (lateArrival, earlyDeparture,
             workHours, shortLeave, continuousAbsence)
      +10  for weekendWorking.requiresApproval
      +10  for holidayWorking.requiresApproval
      Total can exceed 100 (frontend displays "150%" if all 6 rules enabled).
    """
    return get_compliance_stats(db)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Save Changes (all tabs)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/save",
    response_model=WorkHourRuleConfigOut,
    summary="Save Changes button — persist full state of all 4 tabs")
def save_changes(
    payload: SaveAllIn,
    db: Session = Depends(get_db)
):
    return save_all(
        db=db,
        attendance_rules=payload.attendance_rules,
        overtime_rules=payload.overtime_rules,
        break_rules=payload.break_rules,
        settings=payload.settings,
        saved_by=1)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Auto-save single tab
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/save-tab",
    response_model=WorkHourRuleConfigOut,
    summary="Auto-save — update a single tab's config")
def save_single_tab(
    payload: SaveTabIn,
    db: Session = Depends(get_db)
):
    """
    FIX: "settings" is now a valid tab name (was missing, caused 422).
    Valid values: "attendance" | "overtime" | "breaks" | "settings"
    """
    if payload.tab not in VALID_TABS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tab '{payload.tab}'. Must be one of: {sorted(VALID_TABS)}")
    try:
        return save_tab(db, payload.tab, payload.data, saved_by=1)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 5. Reset
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/reset",
    response_model=ResetOut,
    summary="Reset button — restore defaults for one tab or all tabs")
def reset_rules(
    tab: Optional[str] = Query(
        default=None,
        description="'attendance' | 'overtime' | 'breaks' | 'settings' | omit for all"),
    db: Session = Depends(get_db)
):
    if tab and tab not in VALID_TABS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tab '{tab}'. Must be one of: {sorted(VALID_TABS)}")
    try:
        return reset_config(db, tab=tab, reset_by=1)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# 6. Export (header button → downloads JSON)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/export", summary="Export button — download full config as JSON")
def export_rules(
    db: Session = Depends(get_db)
):
    data     = export_config(db)
    filename = f"work-hour-rules-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": f"attachment; filename={filename}"})


# ─────────────────────────────────────────────────────────────────────────────
# 7. Import (header button → upload JSON file)
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/import",
    response_model=WorkHourRuleConfigOut,
    summary="Import button — upload a JSON file to overwrite current config")
async def import_rules(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=422, detail="Only .json files are accepted.")
    content = await file.read()
    try:
        data = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON format.")
    return import_config(db, data, imported_by=1)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Backup  (Settings tab → Backup button)          ← NEW
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/backup", summary="Backup button — snapshot current config to DB backup column")
def backup_rules(
    db: Session = Depends(get_db)
):
    """
    NEW: Maps to the Settings tab → Backup button.
    Saves a timestamped snapshot of the full config into the
    work_hour_rules.backup_json column and sets last_backup_at.
    Also returns the JSON for the frontend to trigger a browser download.
    """
    config   = _get_or_create(db)
    snapshot = export_config(db)

    config.backup_json    = snapshot
    config.last_backup_at = datetime.now(timezone.utc)
    config.updated_by     = 1
    db.commit()

    filename = f"work-hours-backup-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.json"
    return JSONResponse(
        content={
            "message":       "Backup created successfully.",
            "last_backup_at": config.last_backup_at.isoformat(),
            "data":           snapshot,
        },
        headers={"Content-Disposition": f"attachment; filename={filename}"})


# ─────────────────────────────────────────────────────────────────────────────
# 9. Clear Cache (Settings tab → Clear Cache button)  ← NEW
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/cache", summary="Clear Cache button — wipe config row and restore defaults")
def clear_cache(
    db: Session = Depends(get_db)
):
    """
    NEW: Maps to Settings tab → Clear Cache button.
    Deletes the current config row so the next GET / seeds fresh defaults.
    Frontend should reload the page after this call succeeds.
    """
    from model.HR_Automation.work_hour_rule import WorkHourRuleConfig   # adjust import path
    db.query(WorkHourRuleConfig).delete()
    db.commit()
    return {"message": "Config cleared. Defaults will be loaded on next page visit."}


# ─────────────────────────────────────────────────────────────────────────────
# 10. Settings tab — GET / PUT                        ← NEW
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/settings",
    response_model=WorkHourSettingsOut,
    summary="Settings tab load — currency, timeFormat, weekStart, autoSave, notifications, backupFrequency")
def get_settings(
    db: Session = Depends(get_db)
):
    """
    NEW: Settings tab was previously 100% localStorage.
    Returns the settings sub-object from the config row so the tab
    is properly initialised from the database on every page load.

    Fields:
      currency         : "INR" | "USD" | "EUR" | "GBP"
      timeFormat       : "12h" | "24h"
      weekStart        : "Monday" | "Sunday"
      autoSave         : bool
      notificationEmails: bool
      smsAlerts        : bool
      backupFrequency  : "Daily" | "Weekly" | "Monthly"
      lastBackupAt     : datetime | null
      rulesVersion     : str  (e.g. "v3.2.1")
    """
    config = _get_or_create(db)
    return config.settings or {}


@router.put(
    "/settings",
    response_model=WorkHourSettingsOut,
    summary="Settings tab save — persist general settings fields")
def update_settings(
    payload: WorkHourSettingsIn,
    db: Session = Depends(get_db)
):
    """
    NEW: Saves Settings tab fields to the config row.
    Only supplied fields are changed (partial update).
    """
    config = _get_or_create(db)
    existing = config.settings or {}
    existing.update(payload.model_dump(exclude_none=True))
    config.settings   = existing
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config.settings


# ─────────────────────────────────────────────────────────────────────────────
# SHORT-LEAVE CATEGORIES  (Attendance tab)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/attendance/short-leave/category",
    response_model=WorkHourRuleConfigOut,
    summary="Add a new short-leave category")
def add_short_leave_category(
    payload: ShortLeaveCategory,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    att    = config.attendance_rules or {}
    cats   = att.get("shortLeave", {}).get("categories", [])

    next_id = max((c["id"] for c in cats), default=0) + 1
    new_cat = payload.model_dump()
    new_cat["id"] = next_id
    cats.append(new_cat)

    att.setdefault("shortLeave", {})["categories"] = cats
    config.attendance_rules = att
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.put(
    "/attendance/short-leave/category/{cat_id}",
    response_model=WorkHourRuleConfigOut,
    summary="Update a short-leave category (pencil icon)")
def update_short_leave_category(
    cat_id: int,
    payload: ShortLeaveCategory,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    att    = config.attendance_rules or {}
    cats   = att.get("shortLeave", {}).get("categories", [])

    if not any(c["id"] == cat_id for c in cats):
        raise HTTPException(status_code=404, detail=f"Category id {cat_id} not found.")

    updated = [
        {**c, **payload.model_dump(exclude={"id"})} if c["id"] == cat_id else c
        for c in cats
    ]
    att["shortLeave"]["categories"] = updated
    config.attendance_rules = att
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.delete(
    "/attendance/short-leave/category/{cat_id}",
    response_model=WorkHourRuleConfigOut,
    summary="Delete a short-leave category (trash icon)")
def delete_short_leave_category(
    cat_id: int,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    att    = config.attendance_rules or {}
    cats   = att.get("shortLeave", {}).get("categories", [])

    new_cats = [c for c in cats if c["id"] != cat_id]
    if len(new_cats) == len(cats):
        raise HTTPException(status_code=404, detail=f"Category id {cat_id} not found.")

    att["shortLeave"]["categories"] = new_cats
    config.attendance_rules = att
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


# ─────────────────────────────────────────────────────────────────────────────
# OVERTIME CATEGORIES  (Overtime tab)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/overtime/category",
    response_model=WorkHourRuleConfigOut,
    summary="Add a new overtime category (+ Add button)")
def add_overtime_category(
    payload: OvertimeCategory,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    ot     = config.overtime_rules or {}
    cats   = ot.get("categories", [])

    next_id = max((c["id"] for c in cats), default=0) + 1
    new_cat = payload.model_dump()
    new_cat["id"] = next_id
    cats.append(new_cat)

    ot["categories"] = cats
    config.overtime_rules = ot
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.put(
    "/overtime/category/{cat_id}",
    response_model=WorkHourRuleConfigOut,
    summary="Update an overtime category (inline table edit)")
def update_overtime_category(
    cat_id: int,
    payload: OvertimeCategory,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    ot     = config.overtime_rules or {}
    cats   = ot.get("categories", [])

    if not any(c["id"] == cat_id for c in cats):
        raise HTTPException(status_code=404, detail=f"Category id {cat_id} not found.")

    updated = [
        {**c, **payload.model_dump(exclude={"id"})} if c["id"] == cat_id else c
        for c in cats
    ]
    ot["categories"] = updated
    config.overtime_rules = ot
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.delete(
    "/overtime/category/{cat_id}",
    response_model=WorkHourRuleConfigOut,
    summary="Delete an overtime category (trash icon)")
def delete_overtime_category(
    cat_id: int,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    ot     = config.overtime_rules or {}
    cats   = ot.get("categories", [])

    # FIX: removed min-1 guard — UI allows deleting all categories
    new_cats = [c for c in cats if c["id"] != cat_id]
    if len(new_cats) == len(cats):
        raise HTTPException(status_code=404, detail=f"Category id {cat_id} not found.")

    ot["categories"] = new_cats
    config.overtime_rules = ot
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.post(
    "/overtime/category/{cat_id}/duplicate",
    response_model=WorkHourRuleConfigOut,
    summary="Duplicate an overtime category (copy icon on each row)",  # ← NEW
)
def duplicate_overtime_category(
    cat_id: int,
    db: Session = Depends(get_db)
):
    """
    NEW: Copy icon on the Overtime tab category row.
    Clones the row, assigns a new id, appends "(Copy)" to the name.
    """
    config = _get_or_create(db)
    ot     = config.overtime_rules or {}
    cats   = ot.get("categories", [])

    original = next((c for c in cats if c["id"] == cat_id), None)
    if not original:
        raise HTTPException(status_code=404, detail=f"Category id {cat_id} not found.")

    next_id   = max((c["id"] for c in cats), default=0) + 1
    duplicate = {**original, "id": next_id, "name": f"{original.get('name', '')} (Copy)"}
    cats.append(duplicate)

    ot["categories"] = cats
    config.overtime_rules = ot
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


# ─────────────────────────────────────────────────────────────────────────────
# BREAKS  (Breaks tab)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/breaks/break",
    response_model=WorkHourRuleConfigOut,
    summary="Add a new break (+ Add Break button)")
def add_break(
    payload: BreakItem,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    br     = config.break_rules or {}
    breaks = br.get("breaks", [])

    next_id   = max((b["id"] for b in breaks), default=0) + 1
    new_break = payload.model_dump()
    new_break["id"] = next_id
    breaks.append(new_break)

    br["breaks"] = breaks
    config.break_rules = br
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.put(
    "/breaks/break/{break_id}",
    response_model=WorkHourRuleConfigOut,
    summary="Update a break (pencil icon → edit modal)")
def update_break(
    break_id: int,
    payload: BreakItem,
    db: Session = Depends(get_db)
):
    config = _get_or_create(db)
    br     = config.break_rules or {}
    breaks = br.get("breaks", [])

    if not any(b["id"] == break_id for b in breaks):
        raise HTTPException(status_code=404, detail=f"Break id {break_id} not found.")

    updated = [
        {**b, **payload.model_dump(exclude={"id"})} if b["id"] == break_id else b
        for b in breaks
    ]
    br["breaks"] = updated
    config.break_rules = br
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.delete(
    "/breaks/break/{break_id}",
    response_model=WorkHourRuleConfigOut,
    summary="Delete a break (trash icon)")
def delete_break(
    break_id: int,
    db: Session = Depends(get_db)
):
    """
    FIX: removed the min-1 guard — the UI allows deleting ALL breaks.
    If you want a minimum, lower it to 0 (just remove the guard entirely).
    """
    config = _get_or_create(db)
    br     = config.break_rules or {}
    breaks = br.get("breaks", [])

    new_breaks = [b for b in breaks if b["id"] != break_id]
    if len(new_breaks) == len(breaks):
        raise HTTPException(status_code=404, detail=f"Break id {break_id} not found.")

    br["breaks"] = new_breaks
    config.break_rules = br
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


@router.post(
    "/breaks/break/{break_id}/duplicate",
    response_model=WorkHourRuleConfigOut,
    summary="Duplicate a break (copy icon on break card)",   # ← NEW
)
def duplicate_break(
    break_id: int,
    db: Session = Depends(get_db)
):
    """
    NEW: Copy icon on each break card in the Breaks tab.
    Clones the break with a new id and appends "(Copy)" to the name.
    """
    config = _get_or_create(db)
    br     = config.break_rules or {}
    breaks = br.get("breaks", [])

    original = next((b for b in breaks if b["id"] == break_id), None)
    if not original:
        raise HTTPException(status_code=404, detail=f"Break id {break_id} not found.")

    next_id   = max((b["id"] for b in breaks), default=0) + 1
    duplicate = {**original, "id": next_id, "name": f"{original.get('name', '')} (Copy)"}
    breaks.append(duplicate)

    br["breaks"] = breaks
    config.break_rules = br
    config.updated_by = 1
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)