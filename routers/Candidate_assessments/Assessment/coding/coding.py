from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from .utils import (
    generate_otp, send_email, ai_or_fallback_questions,
    save_submission, get_db_connection, run_code_detailed,
    generate_ai_email, generate_ai_manager_link
)
from routers.Candidate_assessments.Assessment.utils.stage_sync import update_candidate_stage_both_tables
from datetime import datetime, timedelta
import json

router = APIRouter()

#  OTP store with expiration 
# { email: {"otp": "123456", "expires": datetime } }
otp_store = {}
OTP_VALIDITY_MINUTES = 5

def store_otp(email, otp):
    otp_store[email] = {
        "otp": otp,
        "expires": datetime.utcnow() + timedelta(minutes=OTP_VALIDITY_MINUTES)
    }

def verify_otp_func(email, otp):
    entry = otp_store.get(email)
    if not entry:
        return False
    if datetime.utcnow() > entry["expires"]:
        otp_store.pop(email, None)
        return False
    if entry["otp"] == otp:
        otp_store.pop(email, None)
        return True
    return False

#  Models 
class OTPRequest(BaseModel):
    name: str
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class CodeSubmission(BaseModel):
    name: str
    email: str
    question_title: str
    language: str
    code: str

class FinalizeRequest(BaseModel):
    name: str
    email: str

#  OTP 
@router.post("/send-otp")
def send_otp(data: OTPRequest):
    otp = generate_otp()
    store_otp(data.email, otp)  # store with expiration
    send_email(data.email, "Levitica OTP", f"Hello {data.name}, OTP: {otp}\nValid 5 minutes.")
    return {"message": "OTP sent successfully"}

@router.post("/verify-otp")
def verify_otp_route(data: VerifyOTPRequest):
    verified = verify_otp_func(data.email, data.otp)
    return {"verified": verified}

#  Questions 
@router.get("/questions")
def get_questions(email: str = None):
    #  REJECTION CHECK: Prevent rejected candidates from taking assessments
    if email:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT stage FROM candidate_records 
                WHERE candidate_email = %s LIMIT 1
            """, (email,))
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result and result[0] and result[0].lower() == "rejected":
                raise HTTPException(
                    status_code=403,
                    detail="You have been rejected in the resume screening stage. You cannot proceed with assessments."
                )
        except HTTPException:
            raise
        except Exception as e:
            print(f"Warning: Could not check candidate stage: {e}")
            # Continue if check fails (don't block legitimate candidates)
    
    questions = ai_or_fallback_questions()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coding_questions (
                id SERIAL PRIMARY KEY,
                title TEXT,
                description TEXT,
                test_cases JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for q in questions:
            cur.execute(
                "INSERT INTO coding_questions(title, description, test_cases) VALUES (%s,%s,%s)",
                (q["title"], q["description"], json.dumps(q["test_cases"]))
            )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Save questions error:", e)
    return {"questions": questions}

#  Run Code 
@router.post("/run_code")
def run_code_endpoint(data: CodeSubmission):
    success, output = run_code_detailed(data.language, data.code)
    return {"success": success, "output": output or "No output"}

#  Submit Code 
@router.post("/submit")
def submit_code(data: CodeSubmission):
    #  REJECTION CHECK: Prevent rejected candidates from submitting assessments
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT stage FROM candidate_records 
            WHERE candidate_email = %s LIMIT 1
        """, (data.email,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result[0] and result[0].lower() == "rejected":
            raise HTTPException(
                status_code=403,
                detail="You have been rejected in the resume screening stage. You cannot proceed with assessments."
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Warning: Could not check candidate stage: {e}")
        # Continue if check fails (don't block legitimate candidates)
    
    success, output = run_code_detailed(data.language, data.code)
    save_submission(
        data.name, data.email, data.question_title,
        data.language, data.code, output, success
    )
    return {
        "message": "Submission saved successfully.",
        "success": success,
        "output": output or ""
    }

#  Finalize Exam 
@router.post("/finalize")
def finalize(data: FinalizeRequest, background_tasks: BackgroundTasks):
    #  REJECTION CHECK: Prevent rejected candidates from finalizing assessments
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT stage FROM candidate_records 
            WHERE candidate_email = %s LIMIT 1
        """, (data.email,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result and result[0] and result[0].lower() == "rejected":
            raise HTTPException(
                status_code=403,
                detail="You have been rejected in the resume screening stage. You cannot proceed with assessments."
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Warning: Could not check candidate stage: {e}")
        # Continue if check fails (don't block legitimate candidates)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM coding_assessment_results WHERE candidate_email=%s AND success=TRUE",
            (data.email,)
        )
        row = cur.fetchone()
        success_count = row[0] if row else 0
        cur.close()
        conn.close()
        
        # Update Assignment status to "Completed" and send next step email
        try:
            from sqlalchemy.orm import Session
            from sqlalchemy import text
            from core.database import SessionLocal
            from model.models import Assignment, Assessment
            
            db: Session = SessionLocal()
            try:
                # Get candidate_records id by email to match with assignment
                candidate_record_result = db.execute(
                    text("SELECT id, candidate_name FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
                    {"email": data.email}
                ).first()
                
                if candidate_record_result:
                    candidate_record_id = candidate_record_result[0]
                    candidate_name = candidate_record_result[1] if len(candidate_record_result) > 1 else data.name
                    
                    # Find the coding assignment for this candidate
                    coding_assessments = db.query(Assessment).filter(
                        Assessment.type == "coding"
                    ).all()
                    
                    for assessment in coding_assessments:
                        assignment = db.query(Assignment).filter(
                            Assignment.candidate_id == candidate_record_id,
                            Assignment.assessment_id == assessment.id
                        ).first()
                        
                        if assignment and assignment.status != "Completed":
                            assignment.status = "Completed"
                            db.add(assignment)
                    
                    db.commit()
                    
                    #  SEQUENTIAL FLOW: Send appropriate email based on result
                    if success_count >= 1:
                        #  STAGE MANAGEMENT: Change stage to "Interview" if passed (both tables)
                        try:
                            update_candidate_stage_both_tables(db, data.email, "Interview")
                        except Exception as stage_error:
                            print(f"Warning: Could not update candidate stage: {stage_error}")
                        
                        # Qualified - Send Interview scheduling email
                        try:
                            manager_link = generate_ai_manager_link(candidate_name, data.email)
                            email_body = f"""Dear {candidate_name},

🎉 Congratulations! You have successfully completed the Coding Assessment with {success_count} successful submission(s).

You have qualified for the next stage - Interview Round!

📅 Interview Scheduling
🔗 Schedule Link: {manager_link}

Instructions:
1. Click on the link above to schedule your interview
2. Choose a convenient time slot
3. You will receive a confirmation email with meeting details
4. Prepare to discuss your technical skills and experience

We look forward to speaking with you!

Best regards,
HR Team - Recruitment"""
                            
                            background_tasks.add_task(
                                send_email,
                                data.email,
                                "Coding Test Passed - Interview Scheduling",
                                email_body
                            )
                            print(f"Sent Interview scheduling link to {data.email}")
                        except Exception as email_error:
                            print(f"Warning: Could not send interview email: {email_error}")
                    else:
                        #  STAGE MANAGEMENT: Change stage to "Rejected" if failed (both tables)
                        try:
                            update_candidate_stage_both_tables(db, data.email, "Rejected")
                        except Exception as stage_error:
                            print(f"Warning: Could not update candidate stage: {stage_error}")
                        
                        # Regret - Send rejection email
                        try:
                            email_body = f"""Dear {candidate_name},

Thank you for completing the Coding Assessment. Unfortunately, you did not meet the qualifying criteria this time (Successful Submissions: {success_count}, Required: At least 1).

We appreciate your effort and encourage you to enhance your coding skills and reapply in the future.

Best regards,
HR Team - Recruitment"""
                            
                            background_tasks.add_task(
                                send_email,
                                data.email,
                                "Coding Assessment Results",
                                email_body
                            )
                        except Exception as email_error:
                            print(f"Warning: Could not send rejection email: {email_error}")
            finally:
                db.close()
        except Exception as e:
            print(f"Warning: Could not update assignment status: {e}")
            # Don't fail the finalization if assignment update fails

        if success_count >= 1:
            manager_link = generate_ai_manager_link(data.name, data.email)
            return {"status": "manager_round", "link": manager_link, "successful_submissions": success_count}
        else:
            return {"status": "regret"}

    except Exception as e:
        print("Finalize error:", e)
        return {"status": "error", "message": str(e)}
