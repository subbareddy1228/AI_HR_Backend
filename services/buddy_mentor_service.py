from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from fastapi import HTTPException

from model.onboarding.buddy_mentor import (
    BuddyProgram, AssignmentRule, BuddyPairing,
    BuddyFeedback, BuddyCommunication,
    ProgramStatus, PairingStatus,
)
from model.onboarding.employee import Employee
from schema.onboarding.buddy_mentor import (
    BuddyProgramCreate, BuddyProgramUpdate,
    BuddyPairingCreate, BuddyPairingUpdate,
    BuddyFeedbackCreate, BuddyCommunicationCreate,
    AutoMatchRequest, AutoMatchOut,
    ProgramAnalyticsOut, BuddyDashboardOut,
    BuddyProgramListOut, DeptDistribution, LocDistribution,
)




def get_dashboard_summary(db: Session) -> BuddyDashboardOut:
    total_programs  = db.query(func.count(BuddyProgram.id)).scalar() or 0
    active_programs = db.query(func.count(BuddyProgram.id)).filter(
        BuddyProgram.status == ProgramStatus.ACTIVE
    ).scalar() or 0

    total_pairs  = db.query(func.count(BuddyPairing.id)).scalar() or 0
    active_pairs = db.query(func.count(BuddyPairing.id)).filter(
        BuddyPairing.status == PairingStatus.ACTIVE
    ).scalar() or 0

    
    available_buddies = db.query(
        func.count(distinct(BuddyPairing.buddy_id))
    ).filter(BuddyPairing.status == PairingStatus.ACTIVE).scalar() or 0

    all_feedbacks = db.query(BuddyFeedback).all()
    avg_rating = (
        round(sum(f.overall_rating for f in all_feedbacks) / len(all_feedbacks), 1)
        if all_feedbacks else None
    )

   
    assigned_ids = db.query(BuddyPairing.new_joiner_id).filter(
        BuddyPairing.status == PairingStatus.ACTIVE
    ).subquery()
    unassigned_joiners = db.query(func.count(Employee.id)).filter(
        Employee.id.not_in(assigned_ids)
    ).scalar() or 0

    return BuddyDashboardOut(
        total_programs=total_programs,
        active_programs=active_programs,
        total_pairs=total_pairs,
        active_pairs=active_pairs,
        available_buddies=available_buddies,
        avg_rating=avg_rating,
        unassigned_joiners=unassigned_joiners,
    )




def create_program(db: Session, payload: BuddyProgramCreate) -> BuddyProgram:
    rules_data = payload.assignment_rules or []
    data = payload.model_dump(exclude={"assignment_rules"})
    program = BuddyProgram(**data)
    db.add(program)
    db.flush()  

    for rule in rules_data:
        db.add(AssignmentRule(program_id=program.id, **rule.model_dump()))

    db.commit()
    db.refresh(program)
    return program


def get_all_programs(
    db: Session,
    status: Optional[str]     = None,
    department: Optional[str] = None,
    location: Optional[str]   = None,
) -> List[BuddyProgramListOut]:
    query = db.query(BuddyProgram)
    if status:
        query = query.filter(BuddyProgram.status == status)
    if department and department.lower() != "all":
        query = query.filter(BuddyProgram.department == department)
    if location and location.lower() != "all":
        query = query.filter(BuddyProgram.location == location)

    programs = query.order_by(BuddyProgram.created_on.desc()).all()

    result = []
    for p in programs:
        total  = len(p.pairings)
        active = sum(1 for pair in p.pairings if pair.status == PairingStatus.ACTIVE)
        scores = [pair.feedback_score for pair in p.pairings if pair.feedback_score is not None]
        avg    = round(sum(scores) / len(scores), 1) if scores else None
        result.append(BuddyProgramListOut(
            id=p.id,
            program_name=p.program_name,
            program_type=p.program_type,
            status=p.status,
            department=p.department,
            location=p.location,
            start_date=p.start_date,
            end_date=p.end_date,
            total_pairs=total,
            active_pairs=active,
            avg_rating=avg,
        ))
    return result


def get_program_by_id(db: Session, program_id: int) -> BuddyProgram:
    program = db.query(BuddyProgram).filter(BuddyProgram.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Buddy program not found")
    return program


def update_program(db: Session, program_id: int, payload: BuddyProgramUpdate) -> BuddyProgram:
    program = get_program_by_id(db, program_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(program, field, value)
    db.commit()
    db.refresh(program)
    return program


def delete_program(db: Session, program_id: int) -> dict:
    program = get_program_by_id(db, program_id)
    name = program.program_name
    db.delete(program)
    db.commit()
    return {"message": f"Program '{name}' deleted successfully"}




def add_rule(db: Session, program_id: int, payload) -> AssignmentRule:
    get_program_by_id(db, program_id)   # validates existence
    rule = AssignmentRule(program_id=program_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def delete_rule(db: Session, rule_id: int) -> dict:
    rule = db.query(AssignmentRule).filter(AssignmentRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Assignment rule not found")
    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted"}




def create_pairing(db: Session, payload: BuddyPairingCreate) -> BuddyPairing:
    get_program_by_id(db, payload.program_id)

    
    existing = db.query(BuddyPairing).filter(
        BuddyPairing.program_id    == payload.program_id,
        BuddyPairing.new_joiner_id == payload.new_joiner_id,
        BuddyPairing.status        == PairingStatus.ACTIVE,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="New joiner already has an active pairing in this program"
        )

    pairing = BuddyPairing(**payload.model_dump())
    db.add(pairing)
    db.commit()
    db.refresh(pairing)
    return pairing


def get_pairings_by_program(db: Session, program_id: int) -> List[BuddyPairing]:
    return (
        db.query(BuddyPairing)
        .filter(BuddyPairing.program_id == program_id)
        .order_by(BuddyPairing.assignment_date.desc())
        .all()
    )


def get_pairing_by_id(db: Session, pairing_id: int) -> BuddyPairing:
    pairing = db.query(BuddyPairing).filter(BuddyPairing.id == pairing_id).first()
    if not pairing:
        raise HTTPException(status_code=404, detail="Pairing not found")
    return pairing


def update_pairing(db: Session, pairing_id: int, payload: BuddyPairingUpdate) -> BuddyPairing:
    pairing = get_pairing_by_id(db, pairing_id)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(pairing, field, value)
    db.commit()
    db.refresh(pairing)
    return pairing


def auto_match_score(db: Session, payload: AutoMatchRequest) -> AutoMatchOut:
   
    buddy  = db.query(Employee).filter(Employee.id == payload.buddy_id).first()
    joiner = db.query(Employee).filter(Employee.id == payload.new_joiner_id).first()

    if not buddy:
        raise HTTPException(status_code=404, detail=f"Buddy employee id={payload.buddy_id} not found")
    if not joiner:
        raise HTTPException(status_code=404, detail=f"New joiner employee id={payload.new_joiner_id} not found")

    score   = 30
    reasons = ["Base score: 30"]

    if getattr(buddy, "department", None) and buddy.department == getattr(joiner, "department", None):
        score += 40
        reasons.append("Same department: +40")

    
    doj = getattr(buddy, "date_of_joining", None)
    if doj:
        tenure_days = (datetime.utcnow().date() - doj).days
        if tenure_days >= 365:
            score += 30
            reasons.append("Minimum 1 yr tenure: +30")
        else:
            reasons.append("Tenure < 1 yr: +0")
    else:
        reasons.append("Tenure unknown: +0")

    return AutoMatchOut(
        buddy_id=payload.buddy_id,
        new_joiner_id=payload.new_joiner_id,
        match_score=min(score, 100),
        match_reason=", ".join(reasons),
    )




def submit_feedback(db: Session, payload: BuddyFeedbackCreate) -> BuddyFeedback:
    pairing = get_pairing_by_id(db, payload.pairing_id)

    feedback = BuddyFeedback(**payload.model_dump())
    db.add(feedback)
    db.flush()

   
    all_ratings = db.query(BuddyFeedback.overall_rating).filter(
        BuddyFeedback.pairing_id == payload.pairing_id
    ).all()
    ratings = [r[0] for r in all_ratings]
    pairing.feedback_score = round(sum(ratings) / len(ratings), 2)

    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedbacks_by_pairing(db: Session, pairing_id: int) -> List[BuddyFeedback]:
    get_pairing_by_id(db, pairing_id)
    return (
        db.query(BuddyFeedback)
        .filter(BuddyFeedback.pairing_id == pairing_id)
        .order_by(BuddyFeedback.submitted_at.desc())
        .all()
    )




def record_communication(db: Session, payload: BuddyCommunicationCreate) -> BuddyCommunication:
    pairing = get_pairing_by_id(db, payload.pairing_id)

    comm = BuddyCommunication(**payload.model_dump())
    db.add(comm)

    
    if not pairing.last_checkin or payload.date > pairing.last_checkin:
        pairing.last_checkin = payload.date

    db.commit()
    db.refresh(comm)
    return comm


def get_communications_by_pairing(db: Session, pairing_id: int) -> List[BuddyCommunication]:
    get_pairing_by_id(db, pairing_id)
    return (
        db.query(BuddyCommunication)
        .filter(BuddyCommunication.pairing_id == pairing_id)
        .order_by(BuddyCommunication.date.desc())
        .all()
    )




def get_program_analytics(db: Session, program_id: int) -> ProgramAnalyticsOut:
    program = get_program_by_id(db, program_id)

    pairings  = db.query(BuddyPairing).filter(BuddyPairing.program_id == program_id).all()
    total     = len(pairings)
    active    = sum(1 for p in pairings if p.status == PairingStatus.ACTIVE)
    completed = sum(1 for p in pairings if p.status == PairingStatus.COMPLETED)
    completion_rate = round(completed / total * 100, 1) if total else 0.0

    feedbacks = (
        db.query(BuddyFeedback)
        .join(BuddyPairing)
        .filter(BuddyPairing.program_id == program_id)
        .all()
    )
    fb_count   = len(feedbacks)
    avg_rating = round(sum(f.overall_rating for f in feedbacks) / fb_count, 1) if fb_count else None

    match_scores = [p.match_score for p in pairings if p.match_score is not None]
    avg_match    = round(sum(match_scores) / len(match_scores), 1) if match_scores else None

    
    dept_rows = (
        db.query(Employee.department, func.count(BuddyPairing.id).label("cnt"))
        .join(BuddyPairing, BuddyPairing.new_joiner_id == Employee.id)
        .filter(BuddyPairing.program_id == program_id)
        .group_by(Employee.department)
        .all()
    )
    dept_dist = [DeptDistribution(department=r[0] or "Unknown", count=r[1]) for r in dept_rows]

    
    loc_rows = (
        db.query(Employee.work_location, func.count(BuddyPairing.id).label("cnt"))
        .join(BuddyPairing, BuddyPairing.new_joiner_id == Employee.id)
        .filter(BuddyPairing.program_id == program_id)
        .group_by(Employee.work_location)
        .all()
    )
    loc_dist = [LocDistribution(location=r[0] or "Unknown", count=r[1]) for r in loc_rows]

    return ProgramAnalyticsOut(
        program_id=program_id,
        program_name=program.program_name,
        total_pairs=total,
        active_pairs=active,
        completed_pairs=completed,
        completion_rate=completion_rate,
        avg_rating=avg_rating,
        avg_match_score=avg_match,
        feedback_count=fb_count,
        satisfaction_score=avg_rating,
        time_to_productivity_days=28,  
        department_distribution=dept_dist,
        location_distribution=loc_dist,
    )
