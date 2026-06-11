from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from fastapi import HTTPException

from model.onboarding.induction import (
    InductionProgram,
    InductionParticipant,
    InductionSession,
    InductionPolicy,
    PolicyAcknowledgment,
)
from model.onboarding.employee import Employee
from schema.onboarding.induction import (
    ProgramCreate, ProgramUpdate,
    ParticipantAdd, BulkParticipantAdd, AttendanceUpdate, BulkAttendanceUpdate,
    SessionCreate, SessionUpdate,
    InductionPolicyCreate, InductionPolicyUpdate,
    AcknowledgmentUpdate,
)



def _get_program_or_404(db: Session, program_id: int) -> InductionProgram:
    obj = db.query(InductionProgram).filter(InductionProgram.id == program_id).first()
    if not obj:
        raise HTTPException(404, "Induction program not found.")
    return obj


def _get_session_or_404(db: Session, session_id: int) -> InductionSession:
    obj = db.query(InductionSession).filter(InductionSession.id == session_id).first()
    if not obj:
        raise HTTPException(404, "Session not found.")
    return obj


def _get_policy_or_404(db: Session, policy_id: int) -> InductionPolicy:
    obj = db.query(InductionPolicy).filter(InductionPolicy.id == policy_id).first()
    if not obj:
        raise HTTPException(404, "Policy not found.")
    return obj


def _recalc_program_stats(db: Session, program_id: int):
   
    prog = db.query(InductionProgram).filter(InductionProgram.id == program_id).first()
    if not prog:
        return
    enrolled = db.query(func.count(InductionParticipant.id)).filter(
        InductionParticipant.program_id == program_id
    ).scalar() or 0
    avg = db.query(func.avg(InductionParticipant.rating)).filter(
        InductionParticipant.program_id == program_id,
        InductionParticipant.rating != None,
    ).scalar() or 0.0
    prog.avg_rating = round(float(avg), 1)
    db.commit()


def _recalc_policy_stats(db: Session, policy_id: int):
    
    policy = db.query(InductionPolicy).filter(InductionPolicy.id == policy_id).first()
    if not policy:
        return
    completed = db.query(func.count(PolicyAcknowledgment.id)).filter(
        PolicyAcknowledgment.policy_id == policy_id,
        PolicyAcknowledgment.acknowledged == True,
    ).scalar() or 0
    policy.completed_employees = completed
    db.commit()




def get_induction_stats(db: Session) -> dict:
   
    total_programs = db.query(func.count(InductionProgram.id)).scalar() or 0

    total_participants = db.query(
        func.count(func.distinct(InductionParticipant.employee_id))
    ).scalar() or 0

    
    policies = db.query(InductionPolicy).all()
    if policies:
        pcts = []
        for p in policies:
            if p.total_employees > 0:
                pcts.append(p.completed_employees / p.total_employees * 100)
        policy_completion = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
    else:
        policy_completion = 0.0

    avg_rating_raw = db.query(func.avg(InductionParticipant.rating)).filter(
        InductionParticipant.rating != None
    ).scalar()
    avg_rating = round(float(avg_rating_raw), 1) if avg_rating_raw else 0.0

    return {
        "total_programs":    total_programs,
        "total_participants": total_participants,
        "policy_completion": policy_completion,
        "avg_rating":        avg_rating,
    }




def list_programs(db: Session) -> list:
    programs = db.query(InductionProgram).order_by(InductionProgram.created_at.desc()).all()
    result = []
    for prog in programs:
        enrolled = db.query(func.count(InductionParticipant.id)).filter(
            InductionParticipant.program_id == prog.id
        ).scalar() or 0
        d = {
            "id":               prog.id,
            "name":             prog.name,
            "description":      prog.description,
            "type":             prog.type,
            "status":           prog.status,
            "start_date":       str(prog.start_date),
            "end_date":         str(prog.end_date),
            "max_participants": prog.max_participants,
            "enrolled_count":   enrolled,
            "avg_rating":       prog.avg_rating,
            "created_at":       prog.created_at,
            "updated_at":       prog.updated_at,
        }
        result.append(d)
    return result


def create_program(db: Session, payload: ProgramCreate) -> InductionProgram:
    prog = InductionProgram(**payload.model_dump())
    db.add(prog)
    db.commit()
    db.refresh(prog)
    return prog


def update_program(db: Session, program_id: int, payload: ProgramUpdate) -> InductionProgram:
    prog = _get_program_or_404(db, program_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(prog, k, v)
    prog.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prog)
    return prog


def delete_program(db: Session, program_id: int) -> dict:
    prog = _get_program_or_404(db, program_id)
    db.delete(prog)
    db.commit()
    return {"message": f"Program '{prog.name}' deleted."}




def list_participants(
    db: Session,
    search:     Optional[str] = None,
    department: Optional[str] = None,
) -> list:
    
    q = (
        db.query(InductionParticipant, Employee, InductionProgram)
        .join(Employee,         Employee.id         == InductionParticipant.employee_id)
        .outerjoin(InductionProgram, InductionProgram.id == InductionParticipant.program_id)
    )

    if search:
        term = f"%{search}%"
        q = q.filter(
            Employee.first_name.ilike(term) |
            Employee.last_name.ilike(term)  |
            Employee.employee_code.ilike(term) |
            Employee.department.ilike(term)
        )

    if department and department not in ("All Departments", "All", ""):
        q = q.filter(Employee.department == department)

    rows = q.order_by(Employee.first_name).all()
    result = []
    for part, emp, prog in rows:
        result.append({
            "id":            part.id,
            "program_id":    part.program_id,
            "employee_id":   part.employee_id,
            "attendance":    part.attendance,
            "rating":        part.rating,
            "enrolled_at":   part.enrolled_at,
            "employee_name": f"{emp.first_name} {emp.last_name or ''}".strip(),
            "employee_code": emp.employee_code,
            "email":         emp.official_email,
            "mobile":        emp.mobile_number,
            "department":    emp.department,
            "designation":   emp.designation,
            "joining_date":  str(emp.joining_date) if emp.joining_date else None,
            "program_name":  prog.name if prog else "Not Assigned",
        })
    return result


def add_participant(db: Session, payload: ParticipantAdd) -> InductionParticipant:
    prog = _get_program_or_404(db, payload.program_id)

    
    if prog.max_participants:
        enrolled = db.query(func.count(InductionParticipant.id)).filter(
            InductionParticipant.program_id == payload.program_id
        ).scalar() or 0
        if enrolled >= prog.max_participants:
            raise HTTPException(400, "Program is at full capacity.")

  
    existing = db.query(InductionParticipant).filter(
        InductionParticipant.program_id  == payload.program_id,
        InductionParticipant.employee_id == payload.employee_id,
    ).first()
    if existing:
        raise HTTPException(409, "Employee is already enrolled in this program.")

    part = InductionParticipant(
        program_id=payload.program_id,
        employee_id=payload.employee_id,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    _recalc_program_stats(db, payload.program_id)
    return part


def bulk_add_participants(db: Session, payload: BulkParticipantAdd) -> dict:
    prog = _get_program_or_404(db, payload.program_id)
    added, skipped = 0, 0
    for eid in payload.employee_ids:
        existing = db.query(InductionParticipant).filter(
            InductionParticipant.program_id  == payload.program_id,
            InductionParticipant.employee_id == eid,
        ).first()
        if existing:
            skipped += 1
            continue
        db.add(InductionParticipant(program_id=payload.program_id, employee_id=eid))
        added += 1
    db.commit()
    _recalc_program_stats(db, payload.program_id)
    return {"added": added, "skipped": skipped}


def mark_attendance(
    db: Session,
    participant_id: int,
    payload: AttendanceUpdate,
) -> InductionParticipant:
    part = db.query(InductionParticipant).filter(
        InductionParticipant.id == participant_id
    ).first()
    if not part:
        raise HTTPException(404, "Participant record not found.")
    part.attendance = payload.attendance
    part.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(part)
    return part


def bulk_mark_attendance(db: Session, payload: BulkAttendanceUpdate) -> dict:
    """Bulk attendance — used by the 'Mark Attendance' button."""
    updated = 0
    for item in payload.updates:
        part = db.query(InductionParticipant).filter(
            InductionParticipant.employee_id == item["employee_id"],
            InductionParticipant.program_id  == item["program_id"],
        ).first()
        if part:
            part.attendance = item.get("attendance", "Present")
            part.updated_at = datetime.utcnow()
            updated += 1
    db.commit()
    return {"updated": updated}


def remove_participant(db: Session, participant_id: int) -> dict:
    part = db.query(InductionParticipant).filter(
        InductionParticipant.id == participant_id
    ).first()
    if not part:
        raise HTTPException(404, "Participant not found.")
    prog_id = part.program_id
    db.delete(part)
    db.commit()
    _recalc_program_stats(db, prog_id)
    return {"message": "Participant removed."}




def list_sessions(db: Session, program_id: Optional[int] = None) -> list:
    q = db.query(InductionSession, InductionProgram).join(
        InductionProgram, InductionProgram.id == InductionSession.program_id
    )
    if program_id:
        q = q.filter(InductionSession.program_id == program_id)
    rows = q.order_by(InductionSession.session_date).all()
    result = []
    for sess, prog in rows:
        result.append({
            "id":           sess.id,
            "program_id":   sess.program_id,
            "program_name": prog.name,
            "title":        sess.title,
            "description":  sess.description,
            "session_date": str(sess.session_date),
            "start_time":   sess.start_time,
            "end_time":     sess.end_time,
            "duration_hrs": sess.duration_hrs,
            "mode":         sess.mode,
            "status":       sess.status,
            "created_at":   sess.created_at,
        })
    return result


def create_session(db: Session, payload: SessionCreate) -> InductionSession:
    _get_program_or_404(db, payload.program_id)
    sess = InductionSession(**payload.model_dump())
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


def update_session(db: Session, session_id: int, payload: SessionUpdate) -> InductionSession:
    sess = _get_session_or_404(db, session_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sess, k, v)
    sess.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sess)
    return sess


def delete_session(db: Session, session_id: int) -> dict:
    sess = _get_session_or_404(db, session_id)
    db.delete(sess)
    db.commit()
    return {"message": "Session deleted."}




def list_policies(db: Session) -> list:
    policies = db.query(InductionPolicy).order_by(InductionPolicy.created_at.desc()).all()
    result = []
    for p in policies:
        pct = round(p.completed_employees / p.total_employees * 100, 1) if p.total_employees > 0 else 0.0
       
        modules_done = db.query(func.sum(PolicyAcknowledgment.modules_completed)).filter(
            PolicyAcknowledgment.policy_id == p.id
        ).scalar() or 0
        result.append({
            "id":                  p.id,
            "title":               p.title,
            "category":            p.category,
            "version":             p.version,
            "effective_date":      str(p.effective_date),
            "status":              p.status,
            "total_employees":     p.total_employees,
            "completed_employees": p.completed_employees,
            "completion_pct":      pct,
            "total_modules":       p.total_modules,
            "modules_completed":   modules_done,
            "created_at":          p.created_at,
        })
    return result


def create_policy(db: Session, payload: InductionPolicyCreate) -> InductionPolicy:
    policy = InductionPolicy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(db: Session, policy_id: int, payload: InductionPolicyUpdate) -> InductionPolicy:
    policy = _get_policy_or_404(db, policy_id)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(policy, k, v)
    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return policy


def delete_policy(db: Session, policy_id: int) -> dict:
    policy = _get_policy_or_404(db, policy_id)
    db.delete(policy)
    db.commit()
    return {"message": f"Policy '{policy.title}' deleted."}


def acknowledge_policy(
    db: Session,
    policy_id: int,
    employee_id: int,
    payload: AcknowledgmentUpdate,
) -> PolicyAcknowledgment:
    ack = db.query(PolicyAcknowledgment).filter(
        PolicyAcknowledgment.policy_id   == policy_id,
        PolicyAcknowledgment.employee_id == employee_id,
    ).first()

    if not ack:
        ack = PolicyAcknowledgment(policy_id=policy_id, employee_id=employee_id)
        db.add(ack)

    ack.acknowledged = payload.acknowledged
    if payload.acknowledged:
        ack.acknowledged_at = datetime.utcnow()
    if payload.modules_completed is not None:
        ack.modules_completed = payload.modules_completed
    ack.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(ack)
    _recalc_policy_stats(db, policy_id)
    return ack