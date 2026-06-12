from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional, List

from core.database import get_db
from schema.onboarding.buddy_mentor import (
    BuddyProgramCreate, BuddyProgramUpdate, BuddyProgramOut, BuddyProgramListOut,
    BuddyPairingCreate, BuddyPairingUpdate, BuddyPairingOut,
    BuddyFeedbackCreate, BuddyFeedbackOut,
    BuddyCommunicationCreate, BuddyCommunicationOut,
    AssignmentRuleCreate, AssignmentRuleOut,
    AutoMatchRequest, AutoMatchOut,
    ProgramAnalyticsOut, BuddyDashboardOut,
)
import services.buddy_mentor_service as svc

router = APIRouter(
    prefix="/buddy-mentor",
    tags=["Buddy Mentor Program"],
)




@router.get("/dashboard", response_model=BuddyDashboardOut)
def get_dashboard(db: Session = Depends(get_db)):
    
    return svc.get_dashboard_summary(db)




@router.post("/programs", response_model=BuddyProgramOut, status_code=status.HTTP_201_CREATED)
def create_program(payload: BuddyProgramCreate, db: Session = Depends(get_db)):
    
    return svc.create_program(db, payload)


@router.get("/programs", response_model=List[BuddyProgramListOut])
def list_programs(
    status:     Optional[str] = Query(None, description="Active | Completed | Draft"),
    department: Optional[str] = Query(None),
    location:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.get_all_programs(db, status, department, location)


@router.get("/programs/{program_id}", response_model=BuddyProgramOut)
def get_program(program_id: int, db: Session = Depends(get_db)):
    
    return svc.get_program_by_id(db, program_id)


@router.put("/programs/{program_id}", response_model=BuddyProgramOut)
def update_program(
    program_id: int,
    payload: BuddyProgramUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_program(db, program_id, payload)


@router.delete("/programs/{program_id}")
def delete_program(program_id: int, db: Session = Depends(get_db)):
    
    return svc.delete_program(db, program_id)




@router.post(
    "/programs/{program_id}/rules",
    response_model=AssignmentRuleOut,
    status_code=status.HTTP_201_CREATED,
)
def add_rule(
    program_id: int,
    payload: AssignmentRuleCreate,
    db: Session = Depends(get_db),
):
    return svc.add_rule(db, program_id, payload)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    
    return svc.delete_rule(db, rule_id)




@router.post("/pairings", response_model=BuddyPairingOut, status_code=status.HTTP_201_CREATED)
def create_pairing(payload: BuddyPairingCreate, db: Session = Depends(get_db)):
    
    return svc.create_pairing(db, payload)


@router.get("/programs/{program_id}/pairings", response_model=List[BuddyPairingOut])
def list_pairings(program_id: int, db: Session = Depends(get_db)):
    
    return svc.get_pairings_by_program(db, program_id)


@router.put("/pairings/{pairing_id}", response_model=BuddyPairingOut)
def update_pairing(
    pairing_id: int,
    payload: BuddyPairingUpdate,
    db: Session = Depends(get_db),
):
    
    return svc.update_pairing(db, pairing_id, payload)


@router.post("/pairings/auto-match", response_model=AutoMatchOut)
def auto_match(payload: AutoMatchRequest, db: Session = Depends(get_db)):
    
    return svc.auto_match_score(db, payload)




@router.post("/feedback", response_model=BuddyFeedbackOut, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: BuddyFeedbackCreate, db: Session = Depends(get_db)):
    
    return svc.submit_feedback(db, payload)


@router.get("/pairings/{pairing_id}/feedback", response_model=List[BuddyFeedbackOut])
def get_feedback(pairing_id: int, db: Session = Depends(get_db)):
    
    return svc.get_feedbacks_by_pairing(db, pairing_id)




@router.post(
    "/communications",
    response_model=BuddyCommunicationOut,
    status_code=status.HTTP_201_CREATED,
)
def record_communication(payload: BuddyCommunicationCreate, db: Session = Depends(get_db)):
    
    return svc.record_communication(db, payload)


@router.get("/pairings/{pairing_id}/communications", response_model=List[BuddyCommunicationOut])
def get_communications(pairing_id: int, db: Session = Depends(get_db)):
    
    return svc.get_communications_by_pairing(db, pairing_id)




@router.get("/programs/{program_id}/analytics", response_model=ProgramAnalyticsOut)
def get_analytics(program_id: int, db: Session = Depends(get_db)):
    
    return svc.get_program_analytics(db, program_id)