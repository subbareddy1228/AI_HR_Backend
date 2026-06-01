from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from core.database import get_db
from schema.assignment import AssignmentCreate, AssignmentOut, CandidatePreselectionPayload, CandidatePreselectionOut
from routers.Candidate_assessments.Assessment.Assessments.services import assignment_service
from routers.Candidate_assessments.Assessment.Assessments.services.results_service import get_all_assessment_results
from core.dependencies import get_current_user
from model.models import User, AssessmentCandidatePreselection
from typing import List, Dict, Any

router = APIRouter(prefix="/assignments", tags=["Assignments"])

@router.post("/", response_model=AssignmentOut)
def assign(data: AssignmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return assignment_service.create_assignment(db, data, user)

@router.get("/", response_model=List[AssignmentOut])
def list_assignments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return assignment_service.get_assignments(db, user)

@router.get("/with-status", response_model=List[Dict[str, Any]])
def list_assignments_with_completion_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Get assignments with actual completion status by checking test completion tables
    """
    return assignment_service.get_assignments_with_completion_status(db, user)

@router.get("/all-results", response_model=List[Dict[str, Any]])
def get_all_results(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Get all assessment results directly from result tables (aptitude, communication, coding)
    without requiring assignments. Groups results by candidate email.
    Filtered by recruiter.
    """
    return get_all_assessment_results(db, user)

@router.post("/preselect-candidates", response_model=CandidatePreselectionOut)
def save_preselected_candidates(
    payload: CandidatePreselectionPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    row = db.query(AssessmentCandidatePreselection).filter(
        AssessmentCandidatePreselection.user_id == user.id
    ).first()

    clean_ids = sorted(list({int(cid) for cid in payload.candidate_ids if cid is not None}))
    clean_emails = sorted(list({str(email).strip().lower() for email in payload.candidate_emails if email}))

    if row:
        row.candidate_ids = clean_ids
        row.candidate_emails = clean_emails
        row.updated_at = datetime.utcnow()
        db.add(row)
    else:
        row = AssessmentCandidatePreselection(
            user_id=user.id,
            candidate_ids=clean_ids,
            candidate_emails=clean_emails
        )
        db.add(row)
    db.commit()
    db.refresh(row)

    return CandidatePreselectionOut(
        candidate_ids=row.candidate_ids or [],
        candidate_emails=row.candidate_emails or [],
        updated_at=row.updated_at.isoformat() if row.updated_at else None
    )

@router.get("/preselect-candidates", response_model=CandidatePreselectionOut)
def get_preselected_candidates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    row = db.query(AssessmentCandidatePreselection).filter(
        AssessmentCandidatePreselection.user_id == user.id
    ).first()
    if not row:
        return CandidatePreselectionOut(candidate_ids=[], candidate_emails=[], updated_at=None)
    return CandidatePreselectionOut(
        candidate_ids=row.candidate_ids or [],
        candidate_emails=row.candidate_emails or [],
        updated_at=row.updated_at.isoformat() if row.updated_at else None
    )

@router.delete("/preselect-candidates")
def clear_preselected_candidates(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    row = db.query(AssessmentCandidatePreselection).filter(
        AssessmentCandidatePreselection.user_id == user.id
    ).first()
    if row:
        db.delete(row)
        db.commit()
    return {"success": True}
