from sqlalchemy.orm import Session
from sqlalchemy import text, func
from schema.assignment import AssignmentCreate
from model.models import Assignment, Assessment, LegacyCandidate, User, Job, Application, Candidate, CandidateRecord
from sqlmodel import select
from typing import List, Dict, Any, Optional


def _normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _get_recruiter_candidate_record_ids(db: Session, user: User) -> List[int]:
    """
    Resolve candidate_records IDs owned by a recruiter through job applications.
    Assignments in this module are created using candidate_records.id from resume endpoints.
    """
    job_ids = [row[0] for row in db.execute(select(Job.id).where(Job.recruiter_id == user.id)).all()]
    if not job_ids:
        return []

    applications = db.execute(select(Application).where(Application.job_id.in_(job_ids))).scalars().all()
    if not applications:
        return []

    candidate_emails = set()
    app_candidate_ids = {app.candidate_id for app in applications if app.candidate_id}

    for app in applications:
        normalized = _normalize_email(app.candidate_email)
        if normalized:
            candidate_emails.add(normalized)

    if app_candidate_ids:
        candidate_rows = db.execute(
            select(Candidate.email).where(Candidate.id.in_(list(app_candidate_ids)))
        ).all()
        for row in candidate_rows:
            normalized = _normalize_email(row[0] if row else None)
            if normalized:
                candidate_emails.add(normalized)

    if not candidate_emails:
        return []

    candidate_record_ids = [
        row[0]
        for row in db.execute(
            select(CandidateRecord.id).where(
                func.lower(func.trim(CandidateRecord.candidate_email)).in_(list(candidate_emails))
            )
        ).all()
    ]
    return sorted(list(set(candidate_record_ids)))

def create_assignment(db: Session, data: AssignmentCreate, user: Optional[User] = None):
    assignment = Assignment(**data.dict())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

def get_assignments(db: Session, user: Optional[User] = None):
    query = db.query(Assignment)
    
    # Filter by recruiter if user is provided and not admin
    if user and user.role.lower() != "admin":
        candidate_record_ids = _get_recruiter_candidate_record_ids(db, user)
        if not candidate_record_ids:
            return []
        query = query.filter(Assignment.candidate_id.in_(candidate_record_ids))
    
    return query.all()

def get_assignments_with_completion_status(db: Session, user: Optional[User] = None) -> List[Dict[str, Any]]:
    """
    Get assignments with actual completion status by checking test tables.
    Also includes results for candidates who completed tests even without explicit assignments.
    """
    # Get assignments filtered by recruiter
    assignments = get_assignments(db, user)
    
    # Get recruiter's candidate IDs for filtering results
    recruiter_candidate_record_ids = set()
    if user and user.role.lower() != "admin":
        recruiter_candidate_record_ids = set(_get_recruiter_candidate_record_ids(db, user))
    result = []
    
    # Track which candidate-email combinations we've already processed
    processed_candidates = set()
    
    for assignment in assignments:
        # Get assessment details to know the type
        assessment = db.query(Assessment).filter(Assessment.id == assignment.assessment_id).first()
        
        assignment_dict = {
            "id": assignment.id,
            "candidate_id": assignment.candidate_id,
            "assessment_id": assignment.assessment_id,
            "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
            "status": assignment.status,
            "actual_status": assignment.status,  # Default to assignment status
            "completed_at": None,
            "score": None,
            "question_count": assessment.question_count if assessment and assessment.question_count else (25 if assessment and assessment.type == 'aptitude' else None)  # Include question_count from assessment, default to 25 for aptitude
        }
        
        if assessment and assignment.candidate_id:
            assessment_type = assessment.type.lower() if assessment.type else None
            
            # Get candidate email for matching across different tables
            candidate_email = None
            try:
                email_result = db.execute(
                    text("SELECT candidate_email FROM candidate_records WHERE id = :id"),
                    {"id": assignment.candidate_id}
                ).first()
                if email_result:
                    candidate_email = email_result[0]
                    print(f"📧 Found candidate email for assignment {assignment.id}: {candidate_email}")
                else:
                    print(f"⚠️ No candidate email found for candidate_id {assignment.candidate_id}")
            except Exception as e:
                print(f"❌ Error getting candidate email for candidate_id {assignment.candidate_id}: {e}")
            
            # Check aptitude test completion
            if assessment_type == 'aptitude' and candidate_email:
                try:
                    aptitude_candidate = db.query(LegacyCandidate).filter(
                        LegacyCandidate.email == candidate_email
                    ).first()
                    
                    if aptitude_candidate:
                        # Check if test is completed (Qualified or Regret status)
                        if aptitude_candidate.status and aptitude_candidate.status.lower() in ['qualified', 'regret', 'completed', 'passed', 'submitted']:
                            assignment_dict["actual_status"] = "Completed"
                            assignment_dict["score"] = aptitude_candidate.score
                            assignment_dict["test_status"] = aptitude_candidate.status  # Include the actual test result
                            
                            # 🔥 Get actual total questions from candidate's answers
                            if aptitude_candidate.answers:
                                if isinstance(aptitude_candidate.answers, dict):
                                    # Count the number of questions answered
                                    total_answered = len(aptitude_candidate.answers)
                                    assignment_dict["question_count"] = total_answered
                                else:
                                    # If answers is stored differently, use assessment question_count
                                    assignment_dict["question_count"] = assessment.question_count if assessment and assessment.question_count else 25
                        elif aptitude_candidate.status and aptitude_candidate.status.lower() == 'pending':
                            assignment_dict["actual_status"] = "In Progress"
                except Exception as e:
                    print(f"Error checking aptitude test: {e}")
            
            # Check communication test completion
            elif assessment_type == 'communication' and candidate_email:
                try:
                    # Query communication_assessment_results table directly
                    comm_result = db.execute(
                        text("""
                            SELECT total_score, passed, submitted_at
                            FROM communication_assessment_results 
                            WHERE LOWER(email) = LOWER(:email)
                            ORDER BY submitted_at DESC
                            LIMIT 1
                        """),
                        {"email": candidate_email}
                    ).first()
                    
                    if comm_result:
                        print(f"🔍 Communication result found for {candidate_email}: score={comm_result[0]}, passed={comm_result[1]}, submitted_at={comm_result[2]}")
                        if comm_result[2]:  # submitted_at exists
                            assignment_dict["actual_status"] = "Completed"
                            assignment_dict["completed_at"] = comm_result[2].isoformat() if comm_result[2] else None
                            assignment_dict["score"] = float(comm_result[0]) if comm_result[0] is not None else 0
                            assignment_dict["test_status"] = "Qualified" if (comm_result[1] is True) else "Regret"
                        else:
                            print(f"⚠️ Communication result found but no submitted_at for {candidate_email}")
                    else:
                        print(f"⚠️ No communication result found for {candidate_email}")
                except Exception as e:
                    print(f"❌ Error checking communication test for {candidate_email}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Check coding test completion
            elif assessment_type == 'coding' and candidate_email:
                try:
                    # Check coding_assessment_results table for coding completions
                    coding_result = db.execute(
                        text("""
                            SELECT COUNT(*) as submission_count, 
                                   SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                                   MAX(timestamp) as last_submission
                            FROM coding_assessment_results 
                            WHERE LOWER(candidate_email) = LOWER(:email)
                        """),
                        {"email": candidate_email}
                    ).first()
                    
                    if coding_result:
                        print(f"🔍 Coding result found for {candidate_email}: count={coding_result[0]}, success={coding_result[1]}, last_submission={coding_result[2]}")
                        if coding_result[0] and coding_result[0] > 0:
                            assignment_dict["actual_status"] = "Completed"
                            assignment_dict["completed_at"] = coding_result[2].isoformat() if coding_result[2] else None
                            assignment_dict["score"] = int(coding_result[1] or 0)  # Number of successful submissions
                            assignment_dict["test_status"] = "Qualified" if (coding_result[1] or 0) >= 1 else "Regret"
                        else:
                            print(f"⚠️ Coding result found but no submissions for {candidate_email}")
                    else:
                        print(f"⚠️ No coding result found for {candidate_email}")
                except Exception as e:
                    print(f"❌ Error checking coding test for {candidate_email}: {e}")
                    import traceback
                    traceback.print_exc()
        
        result.append(assignment_dict)
        
        # Track processed candidates
        if candidate_email:
            processed_candidates.add(candidate_email.lower())
    
    # 🔥 ADD MISSING RESULTS: Check for communication and coding results that don't have assignments
    # Get all candidates who have results but might not have assignments
    try:
        # Track which candidate-assessment combinations already have assignments
        existing_combinations = set()
        for assignment_dict in result:
            if assignment_dict.get("candidate_id") and assignment_dict.get("assessment_id"):
                existing_combinations.add((assignment_dict["candidate_id"], assignment_dict["assessment_id"]))
        
        # Get all unique candidate emails from candidate_records (filtered by recruiter if needed)
        if user and user.role.lower() != "admin" and recruiter_candidate_record_ids:
            # Filter candidates by recruiter's candidate IDs using IN clause
            candidate_ids_list = list(recruiter_candidate_record_ids)
            if candidate_ids_list:
                placeholders = ','.join([':id' + str(i) for i in range(len(candidate_ids_list))])
                params = {f'id{i}': cid for i, cid in enumerate(candidate_ids_list)}
                all_candidates = db.execute(
                    text(f"SELECT id, candidate_email FROM candidate_records WHERE id IN ({placeholders}) AND candidate_email IS NOT NULL"),
                    params
                ).fetchall()
            else:
                all_candidates = []
        else:
            all_candidates = db.execute(
                text("SELECT id, candidate_email FROM candidate_records WHERE candidate_email IS NOT NULL")
            ).fetchall()
        
        # Find communication and coding assessments
        comm_assessment = db.query(Assessment).filter(Assessment.type.ilike('communication')).first()
        coding_assessment = db.query(Assessment).filter(Assessment.type.ilike('coding')).first()
        
        for candidate_id, candidate_email in all_candidates:
            if not candidate_email:
                continue
            
            # Check for communication results
            if comm_assessment:
                # Check if this candidate-assessment combo already exists
                if (candidate_id, comm_assessment.id) not in existing_combinations:
                    comm_result = db.execute(
                        text("""
                            SELECT total_score, passed, submitted_at
                            FROM communication_assessment_results 
                            WHERE LOWER(email) = LOWER(:email)
                            ORDER BY submitted_at DESC
                            LIMIT 1
                        """),
                        {"email": candidate_email}
                    ).first()
                    
                    if comm_result and comm_result[2]:  # Has submitted_at
                        assignment_dict = {
                            "id": None,  # No assignment ID
                            "candidate_id": candidate_id,
                            "assessment_id": comm_assessment.id,
                            "due_date": None,
                            "status": "Completed",
                            "actual_status": "Completed",
                            "completed_at": comm_result[2].isoformat() if comm_result[2] else None,
                            "score": float(comm_result[0]) if comm_result[0] is not None else 0,
                            "question_count": None,
                            "test_status": "Qualified" if (comm_result[1] is True) else "Regret"
                        }
                        result.append(assignment_dict)
                        existing_combinations.add((candidate_id, comm_assessment.id))
                        print(f"✅ Added communication result for {candidate_email} (no assignment)")
            
            # Check for coding results
            if coding_assessment:
                # Check if this candidate-assessment combo already exists
                if (candidate_id, coding_assessment.id) not in existing_combinations:
                    coding_result = db.execute(
                        text("""
                            SELECT COUNT(*) as submission_count, 
                                   SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                                   MAX(timestamp) as last_submission
                            FROM coding_assessment_results 
                            WHERE LOWER(candidate_email) = LOWER(:email)
                        """),
                        {"email": candidate_email}
                    ).first()
                    
                    if coding_result and coding_result[0] and coding_result[0] > 0:
                        assignment_dict = {
                            "id": None,  # No assignment ID
                            "candidate_id": candidate_id,
                            "assessment_id": coding_assessment.id,
                            "due_date": None,
                            "status": "Completed",
                            "actual_status": "Completed",
                            "completed_at": coding_result[2].isoformat() if coding_result[2] else None,
                            "score": int(coding_result[1] or 0),
                            "question_count": None,
                            "test_status": "Qualified" if (coding_result[1] or 0) >= 1 else "Regret"
                        }
                        result.append(assignment_dict)
                        existing_combinations.add((candidate_id, coding_assessment.id))
                        print(f"✅ Added coding result for {candidate_email} (no assignment)")
                    
    except Exception as e:
        print(f"❌ Error adding missing results: {e}")
        import traceback
        traceback.print_exc()
    
    return result
