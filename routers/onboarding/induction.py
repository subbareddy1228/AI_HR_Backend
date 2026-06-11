from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from schema.onboarding.induction import (
    ProgramCreate, ProgramUpdate,
    ParticipantAdd, BulkParticipantAdd, AttendanceUpdate, BulkAttendanceUpdate,
    SessionCreate, SessionUpdate,
    InductionPolicyCreate, InductionPolicyUpdate,
    AcknowledgmentUpdate,
)
from services.induction_service import (
    get_induction_stats,
    list_programs, create_program, update_program, delete_program,
    list_participants, add_participant, bulk_add_participants,
    mark_attendance, bulk_mark_attendance, remove_participant,
    list_sessions, create_session, update_session, delete_session,
    list_policies, create_policy, update_policy, delete_policy,
    acknowledge_policy,
)

router = APIRouter(prefix="/api/induction", tags=["Induction & Orientation"])



@router.get("/stats", summary="Dashboard stat cards")
def induction_stats(db: Session = Depends(get_db)):
   
    return get_induction_stats(db)



@router.get("/programs", summary="List all induction programs")
def get_programs(db: Session = Depends(get_db)):
    return {"programs": list_programs(db)}


@router.post("/programs", status_code=status.HTTP_201_CREATED, summary="Create Program")
def post_program(payload: ProgramCreate, db: Session = Depends(get_db)):
    return create_program(db, payload)


@router.put("/programs/{program_id}", summary="Edit program")
def put_program(program_id: int, payload: ProgramUpdate, db: Session = Depends(get_db)):
    return update_program(db, program_id, payload)


@router.delete("/programs/{program_id}", summary="Delete program")
def del_program(program_id: int, db: Session = Depends(get_db)):
    return delete_program(db, program_id)




@router.get("/participants", summary="Employees List — search + filter by department")
def get_participants(
    search:     Optional[str] = Query(None, description="Search by name, ID, department"),
    department: Optional[str] = Query(None, description="Filter by Department dropdown"),
    db: Session = Depends(get_db),
):
    return {"employees": list_participants(db, search=search, department=department)}


@router.post("/participants", status_code=status.HTTP_201_CREATED, summary="Add Employee to program")
def post_participant(payload: ParticipantAdd, db: Session = Depends(get_db)):
    return add_participant(db, payload)


@router.post("/participants/bulk", status_code=status.HTTP_201_CREATED, summary="Bulk add employees")
def post_bulk_participants(payload: BulkParticipantAdd, db: Session = Depends(get_db)):
    return bulk_add_participants(db, payload)


@router.put("/participants/{participant_id}/attendance", summary="Mark single attendance")
def put_attendance(participant_id: int, payload: AttendanceUpdate, db: Session = Depends(get_db)):
    return mark_attendance(db, participant_id, payload)


@router.post("/participants/bulk-attendance", summary="Mark Attendance (bulk)")
def post_bulk_attendance(payload: BulkAttendanceUpdate, db: Session = Depends(get_db)):
    """Used by the 'Mark Attendance (N)' button after selecting employees."""
    return bulk_mark_attendance(db, payload)


@router.delete("/participants/{participant_id}", summary="Remove participant")
def del_participant(participant_id: int, db: Session = Depends(get_db)):
    return remove_participant(db, participant_id)




@router.get("/sessions", summary="Sessions Management table")
def get_sessions(
    program_id: Optional[int] = Query(None, description="Filter by program"),
    db: Session = Depends(get_db),
):
    return {"sessions": list_sessions(db, program_id=program_id)}


@router.post("/sessions", status_code=status.HTTP_201_CREATED, summary="Add Session")
def post_session(payload: SessionCreate, db: Session = Depends(get_db)):
    return create_session(db, payload)


@router.put("/sessions/{session_id}", summary="Edit session")
def put_session(session_id: int, payload: SessionUpdate, db: Session = Depends(get_db)):
    return update_session(db, session_id, payload)


@router.delete("/sessions/{session_id}", summary="Delete session")
def del_session(session_id: int, db: Session = Depends(get_db)):
    return delete_session(db, session_id)




@router.get("/policies", summary="Policy Acknowledgment table")
def get_policies(db: Session = Depends(get_db)):
    return {"policies": list_policies(db)}


@router.post("/policies", status_code=status.HTTP_201_CREATED, summary="Add Policy")
def post_policy(payload: InductionPolicyCreate, db: Session = Depends(get_db)):
    return create_policy(db, payload)


@router.put("/policies/{policy_id}", summary="Edit policy")
def put_policy(policy_id: int, payload: InductionPolicyUpdate, db: Session = Depends(get_db)):
    return update_policy(db, policy_id, payload)


@router.delete("/policies/{policy_id}", summary="Delete policy")
def del_policy(policy_id: int, db: Session = Depends(get_db)):
    return delete_policy(db, policy_id)


@router.post(
    "/policies/{policy_id}/acknowledge/{employee_id}",
    summary="Employee acknowledges a policy",
)
def post_acknowledge(
    policy_id:   int,
    employee_id: int,
    payload:     AcknowledgmentUpdate,
    db: Session  = Depends(get_db),
):
    return acknowledge_policy(db, policy_id, employee_id, payload)