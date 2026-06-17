"""
services/shift_management_service.py
Business logic for all 6 tabs of Shift Management & Rostering module.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from model.HR_Automation.shift_management import (
    ShiftMaster, ShiftBreakTime, ShiftAssignment,
    ShiftRoster, ShiftRosterDay, ShiftSwapRequest,
    FlexibleArrangement, WorkHourRules, ShiftNotification,
    ShiftTypeEnum, RosterPeriodEnum, RosterStatusEnum,
    SwapStatusEnum, NotificationTypeEnum, RotationPatternEnum,
)

logger = logging.getLogger(__name__)

DAYS_OF_WEEK = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


# ═══════════════════════════════════════════════════════════
# TAB 1 — SHIFT MASTER SERVICE
# ═══════════════════════════════════════════════════════════

class ShiftMasterService:

    @staticmethod
    def list_shifts(db: Session, search: Optional[str] = None,
                    shift_type: Optional[str] = None) -> List[ShiftMaster]:
        q = db.query(ShiftMaster)
        if search:
            term = f"%{search.lower()}%"
            q = q.filter(
                func.lower(ShiftMaster.name).like(term) |
                func.lower(ShiftMaster.code).like(term)
            )
        if shift_type and shift_type != "All":
            q = q.filter(ShiftMaster.shift_type == shift_type.lower())
        return q.order_by(ShiftMaster.id).all()

    @staticmethod
    def get_shift(db: Session, shift_id: int) -> ShiftMaster:
        shift = db.query(ShiftMaster).filter_by(id=shift_id).first()
        if not shift:
            raise ValueError(f"Shift id={shift_id} not found.")
        return shift

    @staticmethod
    def create_shift(db: Session, payload, created_by: Optional[int] = None) -> ShiftMaster:
        if db.query(ShiftMaster).filter_by(code=payload.code).first():
            raise ValueError(f"Shift code '{payload.code}' already exists.")

        shift = ShiftMaster(
            name=payload.name,
            code=payload.code.upper(),
            shift_type=payload.shift_type,
            start_time=payload.start_time,
            end_time=payload.end_time,
            duration_hours=payload.duration_hours,
            grace_period_minutes=payload.grace_period_minutes,
            week_offs=payload.week_offs,
            differential_pay=payload.differential_pay,
            is_active=payload.is_active,
            description=payload.description,
            allow_multiple_per_day=payload.allow_multiple_per_day,
            core_hours_start=payload.core_hours_start,
            core_hours_end=payload.core_hours_end,
            rotation_pattern=payload.rotation_pattern,
            created_by=created_by,
        )
        db.add(shift)
        db.flush()

        for b in payload.break_times:
            db.add(ShiftBreakTime(
                shift_id=shift.id,
                name=b.name,
                start_time=b.start_time,
                end_time=b.end_time,
                duration=b.duration,
                is_paid=b.is_paid,
                mandatory=b.mandatory,
                auto_deduct=b.auto_deduct,
            ))

        db.commit()
        db.refresh(shift)
        logger.info("Shift created: %s (%s)", shift.name, shift.code)
        return shift

    @staticmethod
    def update_shift(db: Session, shift_id: int, payload, updated_by: Optional[int] = None) -> ShiftMaster:
        shift = ShiftMasterService.get_shift(db, shift_id)

        for field, val in payload.model_dump(exclude_none=True, exclude={"break_times"}).items():
            setattr(shift, field, val)

        if payload.break_times is not None:
            # Replace all break times
            db.query(ShiftBreakTime).filter_by(shift_id=shift.id).delete()
            for b in payload.break_times:
                db.add(ShiftBreakTime(
                    shift_id=shift.id, name=b.name,
                    start_time=b.start_time, end_time=b.end_time,
                    duration=b.duration, is_paid=b.is_paid,
                ))

        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def delete_shift(db: Session, shift_id: int) -> None:
        shift = ShiftMasterService.get_shift(db, shift_id)
        # Check for active assignments
        active = db.query(ShiftAssignment).filter_by(shift_id=shift_id, is_active=True).count()
        if active:
            raise ValueError(f"Cannot delete — shift has {active} active assignments.")
        db.delete(shift)
        db.commit()


# ═══════════════════════════════════════════════════════════
# TAB 2 — SHIFT ASSIGNMENT SERVICE
# ═══════════════════════════════════════════════════════════

class ShiftAssignmentService:

    @staticmethod
    def bulk_assign(db: Session, payload, assigned_by: Optional[int] = None) -> List[ShiftAssignment]:
        shift = db.query(ShiftMaster).filter_by(id=payload.shift_id, is_active=True).first()
        if not shift:
            raise ValueError(f"Shift id={payload.shift_id} not found or inactive.")

        assignments = []
        for emp_id in payload.employee_ids:
            # Deactivate existing active assignment
            db.query(ShiftAssignment).filter_by(
                employee_id=emp_id, is_active=True
            ).update({"is_active": False})

            a = ShiftAssignment(
                employee_id=emp_id,
                shift_id=payload.shift_id,
                start_date=payload.start_date,
                end_date=None,
                is_active=True,
                assigned_by=assigned_by,
            )
            db.add(a)
            assignments.append(a)

            # Notification
            NotificationService.send(db, NotificationTypeEnum.shift_assigned, emp_id, {
                "shift_id":   shift.id,
                "shift_name": shift.name,
                "start_date": str(payload.start_date),
            }, f"You have been assigned to {shift.name} starting {payload.start_date}.")

        db.commit()
        logger.info("Bulk assigned %d employees to shift %s", len(assignments), shift.code)
        return assignments

    @staticmethod
    def individual_assign(db: Session, payload, assigned_by: Optional[int] = None) -> ShiftAssignment:
        shift = db.query(ShiftMaster).filter_by(id=payload.shift_id, is_active=True).first()
        if not shift:
            raise ValueError(f"Shift id={payload.shift_id} not found.")

        # Deactivate existing
        db.query(ShiftAssignment).filter_by(
            employee_id=payload.employee_id, is_active=True
        ).update({"is_active": False})

        a = ShiftAssignment(
            employee_id=payload.employee_id,
            shift_id=payload.shift_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_active=True,
            assigned_by=assigned_by,
        )
        db.add(a)
        db.commit()
        db.refresh(a)

        NotificationService.send(db, NotificationTypeEnum.shift_assigned, payload.employee_id, {
            "shift_id": shift.id, "shift_name": shift.name,
            "start_date": str(payload.start_date),
            "end_date": str(payload.end_date) if payload.end_date else None,
        }, f"You have been assigned to {shift.name} starting {payload.start_date}.")

        return a

    @staticmethod
    def list_assignments(db: Session, employee_id: Optional[str] = None,
                         active_only: bool = True) -> List[ShiftAssignment]:
        q = db.query(ShiftAssignment)
        if employee_id:
            q = q.filter_by(employee_id=employee_id)
        if active_only:
            q = q.filter_by(is_active=True)
        return q.order_by(ShiftAssignment.assigned_at.desc()).all()

    @staticmethod
    def update_assignment(db: Session, assignment_id: int, payload) -> ShiftAssignment:
        a = db.query(ShiftAssignment).filter_by(id=assignment_id).first()
        if not a:
            raise ValueError(f"Assignment id={assignment_id} not found.")
        for field, val in payload.model_dump(exclude_none=True).items():
            setattr(a, field, val)
        db.commit()
        db.refresh(a)
        return a


# ═══════════════════════════════════════════════════════════
# TAB 3 — ROSTERING SERVICE
# ═══════════════════════════════════════════════════════════

class RosteringService:

    @staticmethod
    def generate_roster(db: Session, payload, created_by: Optional[int] = None) -> ShiftRoster:
        shift = db.query(ShiftMaster).filter_by(id=payload.shift_id, is_active=True).first()
        if not shift:
            raise ValueError(f"Shift id={payload.shift_id} not found.")

        # Determine end date
        start = payload.start_date
        if payload.period == RosterPeriodEnum.weekly:
            end = start + timedelta(days=6)
        else:
            import calendar
            last_day = calendar.monthrange(start.year, start.month)[1]
            end = date(start.year, start.month, last_day)

        # Rotation shifts (for rotational type)
        rotation_shifts = []
        if shift.shift_type == ShiftTypeEnum.rotational and payload.rotation_shift_ids:
            rotation_shifts = db.query(ShiftMaster).filter(
                ShiftMaster.id.in_(payload.rotation_shift_ids),
                ShiftMaster.is_active == True,
            ).all()
        if not rotation_shifts:
            rotation_shifts = [shift]

        roster = ShiftRoster(
            name=f"{shift.name} Roster - {start}",
            shift_id=shift.id,
            period=payload.period,
            start_date=start,
            end_date=end,
            status=RosterStatusEnum.draft,
            is_published=False,
            rotation_pattern=payload.rotation_pattern or shift.rotation_pattern,
            rotation_shifts=[s.id for s in rotation_shifts],
            created_by=created_by,
        )
        db.add(roster)
        db.flush()

        # Generate day rows
        current = start
        day_index = 0
        week_index = 0
        prev_week_start = start

        while current <= end:
            day_of_week = current.strftime("%A")
            is_week_off = day_of_week in (shift.week_offs or [])

            # Rotation assignment
            assigned_shift = shift
            rot_pattern = payload.rotation_pattern or shift.rotation_pattern
            if shift.shift_type == ShiftTypeEnum.rotational and len(rotation_shifts) > 1:
                days_elapsed = (current - start).days
                if rot_pattern == RotationPatternEnum.daily:
                    idx = days_elapsed % len(rotation_shifts)
                elif rot_pattern == RotationPatternEnum.biweekly:
                    idx = (days_elapsed // 14) % len(rotation_shifts)
                else:  # weekly
                    idx = (days_elapsed // 7) % len(rotation_shifts)
                assigned_shift = rotation_shifts[idx]

            db.add(ShiftRosterDay(
                roster_id=roster.id,
                shift_id=assigned_shift.id,
                roster_date=current,
                day_of_week=day_of_week,
                is_week_off=is_week_off,
                employees=[],
                rotation_sequence=day_index + 1 if shift.shift_type == ShiftTypeEnum.rotational else None,
            ))
            current += timedelta(days=1)
            day_index += 1

        db.commit()
        db.refresh(roster)
        logger.info("Roster generated: %s (%s → %s)", roster.name, start, end)
        return roster

    @staticmethod
    def publish_roster(db: Session, roster_id: int, published_by: Optional[int] = None) -> dict:
        roster = db.query(ShiftRoster).filter_by(id=roster_id).first()
        if not roster:
            raise ValueError(f"Roster id={roster_id} not found.")
        if roster.is_published:
            raise ValueError("Roster is already published.")

        roster.is_published  = True
        roster.status        = RosterStatusEnum.published
        roster.published_at  = datetime.now(timezone.utc)
        roster.published_by  = published_by

        # Notify all assigned employees
        all_employees = set()
        for day in roster.days:
            all_employees.update(day.employees or [])

        for emp_id in all_employees:
            NotificationService.send(
                db, NotificationTypeEnum.roster_published, emp_id,
                {"roster_id": roster.id, "start": str(roster.start_date), "end": str(roster.end_date)},
                f'Your roster "{roster.name}" has been published ({roster.start_date} – {roster.end_date}).',
            )

        db.commit()
        return {"message": "Roster published.", "roster_id": roster_id,
                "notifications_sent": len(all_employees)}

    @staticmethod
    def list_rosters(db: Session) -> List[ShiftRoster]:
        return db.query(ShiftRoster).order_by(ShiftRoster.start_date.desc()).all()

    @staticmethod
    def get_roster(db: Session, roster_id: int) -> ShiftRoster:
        r = db.query(ShiftRoster).filter_by(id=roster_id).first()
        if not r:
            raise ValueError(f"Roster {roster_id} not found.")
        return r


# ═══════════════════════════════════════════════════════════
# TAB 4 — SHIFT SWAP SERVICE
# ═══════════════════════════════════════════════════════════

class ShiftSwapService:

    @staticmethod
    def create_swap_request(db: Session, payload, requested_by: Optional[int] = None) -> ShiftSwapRequest:
        req = ShiftSwapRequest(
            employee_id=payload.employee_id,
            current_shift_id=payload.current_shift_id,
            requested_shift_id=payload.requested_shift_id,
            swap_date=payload.swap_date,
            swap_with_employee_id=payload.swap_with_employee_id,
            reason=payload.reason,
            status=SwapStatusEnum.pending,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        logger.info("Swap request: %s on %s", payload.employee_id, payload.swap_date)
        return req

    @staticmethod
    def approve_or_reject(
        db: Session, request_id: int, approved: bool,
        rejection_reason: Optional[str] = None,
        decision_by: Optional[int] = None,
    ) -> ShiftSwapRequest:
        req = db.query(ShiftSwapRequest).filter_by(id=request_id).first()
        if not req:
            raise ValueError(f"Swap request {request_id} not found.")
        if req.status != SwapStatusEnum.pending:
            raise ValueError("Request already processed.")

        now = datetime.now(timezone.utc)

        if approved:
            req.status      = SwapStatusEnum.approved
            req.approved_by = decision_by
            req.approved_at = now

            # Update the assignment
            assignment = db.query(ShiftAssignment).filter_by(
                employee_id=req.employee_id, is_active=True
            ).first()
            if assignment:
                old_shift = db.query(ShiftMaster).filter_by(id=assignment.shift_id).first()
                new_shift = db.query(ShiftMaster).filter_by(id=req.requested_shift_id).first()
                assignment.shift_id = req.requested_shift_id

                NotificationService.send(
                    db, NotificationTypeEnum.shift_swapped, req.employee_id,
                    {"old_shift": old_shift.name if old_shift else "",
                     "new_shift": new_shift.name if new_shift else ""},
                    f"Shift swap approved. You are now on {new_shift.name if new_shift else 'new shift'} from {req.swap_date}.",
                )

                # Peer swap notification
                if req.swap_with_employee_id:
                    NotificationService.send(
                        db, NotificationTypeEnum.shift_swapped, req.swap_with_employee_id,
                        {"old_shift": new_shift.name if new_shift else "",
                         "new_shift": old_shift.name if old_shift else ""},
                        f"You have been swapped to {old_shift.name if old_shift else 'shift'} from {req.swap_date}.",
                    )
        else:
            req.status           = SwapStatusEnum.rejected
            req.rejected_by      = decision_by
            req.rejected_at      = now
            req.rejection_reason = rejection_reason or "Not approved."

            NotificationService.send(
                db, NotificationTypeEnum.shift_swap_rejected, req.employee_id,
                {"swap_date": str(req.swap_date), "reason": req.rejection_reason},
                f"Your shift swap request for {req.swap_date} has been rejected.",
            )

        db.commit()
        db.refresh(req)
        return req

    @staticmethod
    def list_requests(db: Session, status: Optional[SwapStatusEnum] = None,
                      employee_id: Optional[str] = None) -> List[ShiftSwapRequest]:
        q = db.query(ShiftSwapRequest)
        if status:
            q = q.filter_by(status=status)
        if employee_id:
            q = q.filter_by(employee_id=employee_id)
        return q.order_by(ShiftSwapRequest.requested_at.desc()).all()


# ═══════════════════════════════════════════════════════════
# TAB 5 — FLEXIBLE ARRANGEMENTS SERVICE
# ═══════════════════════════════════════════════════════════

class FlexibleArrangementService:

    @staticmethod
    def save(db: Session, payload, created_by: Optional[int] = None) -> FlexibleArrangement:
        existing = db.query(FlexibleArrangement).filter_by(
            employee_id=payload.employee_id
        ).first()

        if existing:
            for f, v in payload.model_dump().items():
                setattr(existing, f, v)
            existing.is_active  = True
            existing.created_by = created_by
            db.commit()
            db.refresh(existing)
            return existing

        arr = FlexibleArrangement(
            employee_id=payload.employee_id,
            arrangement_type=payload.arrangement_type,
            core_hours_start=payload.core_hours_start,
            core_hours_end=payload.core_hours_end,
            flexible_start=payload.flexible_start,
            flexible_end=payload.flexible_end,
            remote_work_days=payload.remote_work_days,
            office_days=payload.office_days,
            remote_days=payload.remote_days,
            compressed_enabled=payload.compressed_enabled,
            compressed_work_days=payload.compressed_work_days,
            compressed_hours_per_day=payload.compressed_hours_per_day,
            is_active=True,
            created_by=created_by,
        )
        db.add(arr)
        db.commit()
        db.refresh(arr)
        return arr

    @staticmethod
    def list_all(db: Session) -> List[FlexibleArrangement]:
        return db.query(FlexibleArrangement).filter_by(is_active=True).all()

    @staticmethod
    def deactivate(db: Session, arrangement_id: int) -> FlexibleArrangement:
        arr = db.query(FlexibleArrangement).filter_by(id=arrangement_id).first()
        if not arr:
            raise ValueError(f"Arrangement {arrangement_id} not found.")
        arr.is_active = False
        db.commit()
        return arr


# ═══════════════════════════════════════════════════════════
# TAB 6 — WORK HOUR RULES SERVICE
# ═══════════════════════════════════════════════════════════

class WorkHourRulesService:

    @staticmethod
    def get(db: Session) -> WorkHourRules:
        rules = db.query(WorkHourRules).filter_by(id=1).first()
        if not rules:
            rules = WorkHourRules(id=1)
            db.add(rules)
            db.commit()
            db.refresh(rules)
        return rules

    @staticmethod
    def update(db: Session, payload, updated_by: Optional[int] = None) -> WorkHourRules:
        rules = WorkHourRulesService.get(db)
        for field, val in payload.model_dump(exclude_none=True).items():
            setattr(rules, field, val)
        rules.updated_by = updated_by
        db.commit()
        db.refresh(rules)
        return rules


# ═══════════════════════════════════════════════════════════
# NOTIFICATION SERVICE  (Bell panel)
# ═══════════════════════════════════════════════════════════

class NotificationService:

    @staticmethod
    def send(db: Session, ntype: NotificationTypeEnum, employee_id: str,
             payload: dict, message: str) -> ShiftNotification:
        n = ShiftNotification(
            type=ntype,
            employee_id=employee_id,
            message=message,
            payload=payload,
        )
        db.add(n)
        # commit is handled by caller
        logger.info("Notification → %s: %s", employee_id, message)
        return n

    @staticmethod
    def list_for_employee(db: Session, employee_id: str,
                          unread_only: bool = False) -> List[ShiftNotification]:
        q = db.query(ShiftNotification).filter_by(employee_id=employee_id)
        if unread_only:
            q = q.filter_by(is_read=False)
        return q.order_by(ShiftNotification.created_at.desc()).limit(100).all()

    @staticmethod
    def mark_read(db: Session, employee_id: str,
                  notification_ids: Optional[List[int]] = None) -> int:
        q = db.query(ShiftNotification).filter_by(employee_id=employee_id, is_read=False)
        if notification_ids:
            q = q.filter(ShiftNotification.id.in_(notification_ids))
        count = q.count()
        q.update({"is_read": True})
        db.commit()
        return count
