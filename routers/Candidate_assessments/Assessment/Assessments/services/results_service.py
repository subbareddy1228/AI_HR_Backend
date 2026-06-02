"""
Service to fetch all assessment results directly from result tables
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from model.models import LegacyCandidate, User, Job, Application
from sqlmodel import select
from typing import List, Dict, Any, Optional


def get_all_assessment_results(db: Session, user: Optional[User] = None) -> List[Dict[str, Any]]:
    """
    Fetch all assessment results directly from the three result tables:
    - aptitude_assessment_results
    - communication_assessment_results
    - coding_assessment_results
    
    Groups results by candidate email and returns all three stages.
    Filtered by recruiter if user is provided.
    """
    # Get recruiter's candidate emails
    recruiter_candidate_emails = set()
    
    if user and user.role.lower() != "admin":
        job_ids = list(db.exec(select(Job.id).where(Job.recruiter_id == user.id)).all())
        print(f"🔍 Recruiter {user.id} has {len(job_ids)} jobs")
        if job_ids:
            applications = db.exec(select(Application).where(Application.job_id.in_(job_ids))).all()
            print(f"🔍 Found {len(applications)} applications for recruiter {user.id}")
            for app in applications:
                if app.candidate_email:
                    recruiter_candidate_emails.add(app.candidate_email.lower().strip())
            candidate_ids = list(set([app.candidate_id for app in applications if app.candidate_id]))
            if candidate_ids:
                from model.models import Candidate
                candidates = db.exec(select(Candidate).where(Candidate.id.in_(candidate_ids))).all()
                for candidate in candidates:
                    if candidate.email:
                        recruiter_candidate_emails.add(candidate.email.lower().strip())
        
        print(f"🔍 Recruiter {user.id} has {len(recruiter_candidate_emails)} unique candidate emails")
        if recruiter_candidate_emails:
            print(f"🔍 Sample emails: {list(recruiter_candidate_emails)[:5]}")
    
    # If user is not admin and has no candidates, return empty list
    if user and user.role.lower() != "admin" and not recruiter_candidate_emails:
        print(f"⚠️ Recruiter {user.id} has no candidates, returning empty results")
        return []
    
    candidate_results_map = {}
    
    # 1. Fetch Aptitude Results
    try:
        query = db.query(LegacyCandidate).filter(
            LegacyCandidate.status.isnot(None),
            LegacyCandidate.status != ''
        )
        
        # Filter by recruiter's candidate emails (unless admin)
        if user and user.role.lower() != "admin" and recruiter_candidate_emails:
            from sqlalchemy import func
            query = query.filter(
                func.lower(func.trim(LegacyCandidate.email)).in_(
                    [email.lower().strip() for email in recruiter_candidate_emails]
                )
            )
        elif user and user.role.lower() != "admin":
            # Non-admin with no candidates should get no results
            query = query.filter(False)  # This will return empty results
        
        aptitude_results = query.all()
        
        for result in aptitude_results:
            email = result.email.lower() if result.email else None
            if not email:
                continue
                
            if email not in candidate_results_map:
                candidate_results_map[email] = {
                    "candidate_email": result.email,
                    "candidate_name": result.name,
                    "aptitude": None,
                    "communication": None,
                    "coding": None
                }
            
            # Calculate question count from answers
            question_count = 25  # default
            if result.answers:
                if isinstance(result.answers, dict):
                    question_count = len(result.answers)
            
            candidate_results_map[email]["aptitude"] = {
                "score": result.score,
                "status": "Completed",  # If status exists, test is completed
                "test_status": result.status,  # Qualified/Regret
                "question_count": question_count,
                "completed_at": None  # Aptitude table doesn't have timestamp
            }
    except Exception as e:
        print(f"❌ Error fetching aptitude results: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. Fetch Communication Results
    try:
        if user and user.role.lower() != "admin":
            if recruiter_candidate_emails:
                # Filter by recruiter's candidate emails
                placeholders = ','.join([f':email{i}' for i in range(len(recruiter_candidate_emails))])
                params = {f'email{i}': email for i, email in enumerate(recruiter_candidate_emails)}
                comm_results = db.execute(
                    text(f"""
                        SELECT email, name, total_score, passed, submitted_at
                        FROM communication_assessment_results
                        WHERE LOWER(TRIM(email)) IN ({placeholders})
                        ORDER BY submitted_at DESC
                    """),
                    params
                ).fetchall()
            else:
                # Non-admin with no candidates should get no results
                comm_results = []
        else:
            # Admin gets all results
            comm_results = db.execute(
                text("""
                    SELECT email, name, total_score, passed, submitted_at
                    FROM communication_assessment_results
                    ORDER BY submitted_at DESC
                """)
            ).fetchall()
        
        for row in comm_results:
            email = row[0].lower() if row[0] else None
            if not email:
                continue
                
            if email not in candidate_results_map:
                candidate_results_map[email] = {
                    "candidate_email": row[0],
                    "candidate_name": row[1] if row[1] else 'Unknown',
                    "aptitude": None,
                    "communication": None,
                    "coding": None
                }
            
            # Handle passed field - could be boolean, string, or integer
            passed_value = row[3]
            is_passed = False
            if passed_value is True or passed_value == 1 or (isinstance(passed_value, str) and passed_value.lower() in ['true', '1', 'yes']):
                is_passed = True
            
            candidate_results_map[email]["communication"] = {
                "score": float(row[2]) if row[2] is not None else 0,
                "status": "Completed",
                "test_status": "Qualified" if is_passed else "Regret",
                "question_count": None,  # Communication doesn't track question count
                "completed_at": row[4].isoformat() if row[4] else None
            }
    except Exception as e:
        print(f"❌ Error fetching communication results: {e}")
        import traceback
        traceback.print_exc()
    
    # 3. Fetch Coding Results
    try:
        if user and user.role.lower() != "admin":
            if recruiter_candidate_emails:
                # Filter by recruiter's candidate emails
                placeholders = ','.join([f':email{i}' for i in range(len(recruiter_candidate_emails))])
                params = {f'email{i}': email for i, email in enumerate(recruiter_candidate_emails)}
                coding_results = db.execute(
                    text(f"""
                        SELECT candidate_email, candidate_name,
                               COUNT(*) as submission_count,
                               SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                               MAX(timestamp) as last_submission
                        FROM coding_assessment_results
                        WHERE LOWER(TRIM(candidate_email)) IN ({placeholders})
                        GROUP BY candidate_email, candidate_name
                    """),
                    params
                ).fetchall()
            else:
                # Non-admin with no candidates should get no results
                coding_results = []
        else:
            # Admin gets all results
            coding_results = db.execute(
                text("""
                    SELECT candidate_email, candidate_name,
                           COUNT(*) as submission_count,
                           SUM(CASE WHEN success = TRUE THEN 1 ELSE 0 END) as success_count,
                           MAX(timestamp) as last_submission
                    FROM coding_assessment_results
                    GROUP BY candidate_email, candidate_name
                """)
            ).fetchall()
        
        for row in coding_results:
            email = row[0].lower() if row[0] else None
            if not email:
                continue
                
            if email not in candidate_results_map:
                candidate_results_map[email] = {
                    "candidate_email": row[0],
                    "candidate_name": row[1] if row[1] else 'Unknown',
                    "aptitude": None,
                    "communication": None,
                    "coding": None
                }
            
            submission_count = row[2] or 0
            success_count = row[3] or 0
            
            if submission_count > 0:
                candidate_results_map[email]["coding"] = {
                    "score": int(success_count),
                    "status": "Completed",
                    "test_status": "Qualified" if success_count >= 1 else "Regret",
                    "question_count": None,  # Coding doesn't track question count in results
                    "completed_at": row[4].isoformat() if row[4] else None,
                    "submission_count": int(submission_count),
                    "success_count": int(success_count)
                }
    except Exception as e:
        print(f"❌ Error fetching coding results: {e}")
        import traceback
        traceback.print_exc()
    
    # Add candidate_id by looking up from candidate_records
    try:
        for email, candidate_data in candidate_results_map.items():
            candidate_record = db.execute(
                text("SELECT id FROM candidate_records WHERE LOWER(candidate_email) = LOWER(:email) LIMIT 1"),
                {"email": candidate_data["candidate_email"]}
            ).first()
            
            if candidate_record:
                candidate_data["candidate_id"] = candidate_record[0]
            else:
                candidate_data["candidate_id"] = None
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch candidate_id for some candidates: {e}")
    
    # Convert map to list
    results_list = list(candidate_results_map.values())
    
    print(f"✅ Fetched results for {len(results_list)} candidates")
    if user and user.role.lower() != "admin":
        print(f"🔒 Filtered results for recruiter {user.id}: {len(results_list)} candidates")
        if results_list:
            sample_emails = [r.get('candidate_email', 'N/A') for r in results_list[:3]]
            print(f"🔍 Sample result emails: {sample_emails}")
    
    return results_list

