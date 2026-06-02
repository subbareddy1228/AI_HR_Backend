from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from urllib.parse import quote_plus
from routers.Candidate_assessments.Assessment.communication.utils_comm import (generate_otp,send_email,generate_full_exam,score_text,generate_candidate_email,otp_store)
from core.database import DATABASE_URL, SessionLocal as MainSessionLocal
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, text
from sqlalchemy.orm import sessionmaker, declarative_base
from model.models import Assignment, Assessment
from routers.Candidate_assessments.Assessment.utils.stage_sync import update_candidate_stage_both_tables
import datetime, json, time, os

#  Database Setup 
engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

#  model.models 
class ExamAttempt(Base):
    __tablename__ = "communication_assessment_results"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    reading_paragraph = Column(Text)
    reading_mcqs = Column(Text)
    writing_prompt = Column(Text)
    listening_paragraph = Column(Text)
    writing_answer = Column(Text)
    listening_answer = Column(Text)
    mcq_answers = Column(Text)
    writing_score = Column(Float)
    listening_score = Column(Float)
    mcq_score = Column(Float)
    total_score = Column(Float)
    passed = Column(Boolean)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

#  Database Migration: Add missing columns 
def ensure_table_columns():
    """Ensure all required columns exist in the communication_assessment_results table."""
    try:
        # Create table if it doesn't exist
        Base.metadata.create_all(bind=engine)
        
        with engine.begin() as conn:
            # Check and add 'passed' column if it doesn't exist
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'communication_assessment_results' 
                AND column_name = 'passed'
            """))
            if result.scalar() == 0:
                conn.execute(text("""
                    ALTER TABLE communication_assessment_results 
                    ADD COLUMN passed BOOLEAN
                """))
                print(" Added 'passed' column to communication_assessment_results table")
            
            # Check and add 'submitted_at' column if it doesn't exist
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'communication_assessment_results' 
                AND column_name = 'submitted_at'
            """))
            if result.scalar() == 0:
                conn.execute(text("""
                    ALTER TABLE communication_assessment_results 
                    ADD COLUMN submitted_at TIMESTAMP
                """))
                print(" Added 'submitted_at' column to communication_assessment_results table")
    except Exception as e:
        print(f" Warning: Could not ensure table columns: {e}")
        import traceback
        traceback.print_exc()

# Initialize database tables lazily (only when needed, not at import time)
# This prevents startup failures if database is not available
def init_db_tables():
    """Initialize database tables. Call this when database is ready."""
    try:
        ensure_table_columns()
    except Exception as e:
        print(f" Warning: Could not initialize database tables: {e}")

#  Router 
router = APIRouter()

# Helper function to get base URL
def get_base_url():
    """Get the base URL for the frontend application"""
    return os.getenv("FRONTEND_URL", "http://localhost:3000")

#  Request model.models 
class OTPRequest(BaseModel):
    name: str
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: str

class CommSubmission(BaseModel):
    name: str
    email: str
    writing_answer: str
    listening_answer: str
    mcq_answers: dict
 
@router.post("/send-otp")
def send_otp_route(data: OTPRequest):
    otp = generate_otp()
    otp_store[data.email] = {"otp": otp, "expires": time.time() + 300}  # 5 min expiry
    print(f"[DEBUG] OTP for {data.email}: {otp}")

    success, msg = send_email(
        data.email,
        "Levitica Communication OTP",
        f"Hello {data.name},\n\nYour OTP is: {otp}\nIt is valid for 5 minutes."
    )
    if not success:
        raise HTTPException(status_code=500, detail=msg)
    return {"message": f"OTP sent successfully to {data.email}"}

#  Verify OTP 
@router.post("/verify-otp")
def verify_otp_route(data: VerifyOTPRequest):
    record = otp_store.get(data.email)
    if not record:
        return {"verified": False, "reason": "No OTP found. Request a new one."}
    if time.time() > record["expires"]:
        otp_store.pop(data.email, None)
        return {"verified": False, "reason": "OTP expired. Request a new one."}
    if record["otp"] == data.otp:
        otp_store.pop(data.email, None)
        return {"verified": True}
    return {"verified": False, "reason": "Invalid OTP"}

#  Exam Routes 
@router.get("/exam")
def get_exam(name: str, email: str):
    # Ensure database tables are initialized
    init_db_tables()
    
    #  REJECTION CHECK: Prevent rejected candidates from taking assessments
    try:
        with SessionLocal() as session:
            candidate_record_result = session.execute(
                text("SELECT id, stage FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
                {"email": email}
            ).first()
            
            if candidate_record_result:
                candidate_stage = candidate_record_result[1] if len(candidate_record_result) > 1 else None
                if candidate_stage and candidate_stage.lower() == "rejected":
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
        with SessionLocal() as session:
            existing = session.query(ExamAttempt).filter_by(email=email).first()
            if existing:
                # Return existing exam data
                exam_data = {
                    "reading_paragraph": existing.reading_paragraph or "",
                    "reading_mcqs": json.loads(existing.reading_mcqs) if existing.reading_mcqs else [],
                    "writing_prompt": existing.writing_prompt or "",
                    "listening_paragraph": existing.listening_paragraph or ""
                }
                return {"exam": exam_data}
            
            # Generate new exam if it doesn't exist
            exam_data = generate_full_exam(email, name)
            if not exam_data:
                raise HTTPException(status_code=500, detail="Failed to generate exam. Please try again later.")
            
            attempt = ExamAttempt(
                name=name,
                email=email,
                reading_paragraph=exam_data.get("reading_paragraph", ""),
                reading_mcqs=json.dumps(exam_data.get("reading_mcqs", [])),
                writing_prompt=exam_data.get("writing_prompt", ""),
                listening_paragraph=exam_data.get("listening_paragraph", "")
            )
            session.add(attempt)
            session.commit()
            return {"exam": exam_data}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f" Error in get_exam endpoint: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/submit")
def submit_answers(data: CommSubmission):
    # Ensure database tables are initialized
    init_db_tables()
    
    #  REJECTION CHECK: Prevent rejected candidates from submitting assessments
    try:
        with SessionLocal() as session:
            candidate_record_result = session.execute(
                text("SELECT id, stage FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
                {"email": data.email}
            ).first()
            
            if candidate_record_result:
                candidate_stage = candidate_record_result[1] if len(candidate_record_result) > 1 else None
                if candidate_stage and candidate_stage.lower() == "rejected":
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
        with SessionLocal() as session:
            attempt = session.query(ExamAttempt).filter_by(email=data.email).first()
            if not attempt:
                raise HTTPException(status_code=404, detail="Exam not found")

            writing_score = score_text(data.writing_answer, attempt.writing_prompt, 10)
            listening_score = score_text(data.listening_answer, attempt.listening_paragraph, 5)
            mcq_questions = json.loads(attempt.reading_mcqs or "[]")
            mcq_answers = data.mcq_answers or {}
            mcq_score = sum(
                1 for i, q in enumerate(mcq_questions)
                if mcq_answers.get(str(i)) == q.get("answer")
            )

            total_score = writing_score + listening_score + mcq_score
            max_score = 10 + 5 + len(mcq_questions)
            passed = total_score >= 9

            attempt.writing_answer = data.writing_answer
            attempt.listening_answer = data.listening_answer
            attempt.mcq_answers = json.dumps(mcq_answers)
            attempt.writing_score = writing_score
            attempt.listening_score = listening_score
            attempt.mcq_score = mcq_score
            attempt.total_score = total_score
            attempt.passed = passed
            attempt.submitted_at = datetime.datetime.utcnow()
            session.commit()

        # Update Assignment status to "Completed" and trigger next assessment
        try:
            with MainSessionLocal() as db:
                # Get candidate_records id by email
                candidate_record_result = db.execute(
                    text("SELECT id, candidate_name FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
                    {"email": data.email}
                ).first()
                
                if candidate_record_result:
                    candidate_record_id = candidate_record_result[0]
                    candidate_name = candidate_record_result[1] if len(candidate_record_result) > 1 else data.name
                    
                    # Find and update communication assignment
                    communication_assessments = db.query(Assessment).filter(
                        Assessment.type == "communication"
                    ).all()
                    
                    for assessment in communication_assessments:
                        assignment = db.query(Assignment).filter(
                            Assignment.candidate_id == candidate_record_id,
                            Assignment.assessment_id == assessment.id
                        ).first()
                        
                        if assignment and assignment.status != "Completed":
                            assignment.status = "Completed"
                            db.add(assignment)
                    
                    db.commit()
                    
                    #  SEQUENTIAL FLOW: Send appropriate email
                    if passed:
                        # Send Coding test link
                        try:
                            coding_link = f"{get_base_url()}/assessment/coding?name={quote_plus(candidate_name)}&email={quote_plus(data.email)}"
                            email_body = f"""Dear {candidate_name},

🎉 Congratulations! You have successfully passed the Communication Assessment with a score of {total_score}/{max_score}.

You are now invited to take the final stage of our technical assessment:

💻 Coding Assessment
🔗 Test Link: {coding_link}

Instructions:
1. Click on the link above to start your coding assessment
2. You will receive an OTP for verification
3. You can write code in Python, C++, or Java
4. Complete and test your solutions thoroughly

Best of luck with the coding round!

Best regards,
HR Team - Recruitment"""
                            
                            send_email(data.email, " Communication Test Passed - Next: Coding Assessment", email_body)
                            print(f" Sent Coding test link to {data.email}")
                        except Exception as email_error:
                            print(f"Warning: Could not send next assessment email: {email_error}")
                    else:
                        #  STAGE MANAGEMENT: Change stage to "Rejected" if failed (both tables)
                        try:
                            update_candidate_stage_both_tables(db, data.email, "Rejected")
                        except Exception as stage_error:
                            print(f"Warning: Could not update candidate stage: {stage_error}")
                        
                        # Send rejection email
                        try:
                            email_body = f"""Dear {candidate_name},

Thank you for taking the Communication Assessment. Unfortunately, you did not meet the qualifying criteria this time (Score: {total_score}/{max_score}, Required: 9/{max_score}).

We encourage you to enhance your communication skills and reapply in the future.

Best regards,
HR Team - Recruitment"""
                            
                            send_email(data.email, "Communication Assessment Results", email_body)
                        except Exception as email_error:
                            print(f"Warning: Could not send rejection email: {email_error}")
        except Exception as e:
            print(f"Warning: Could not update assignment or send email: {e}")

        return {"total_score": total_score, "max_score": max_score, "passed": passed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

#  Admin Route 
@router.get("/all-exams")
def get_all_exams():
    # Ensure database tables are initialized
    init_db_tables()
    
    try:
        with SessionLocal() as session:
            attempts = session.query(ExamAttempt).all()
            results = []
            for a in attempts:
                results.append({
                    "name": a.name,
                    "email": a.email,
                    "reading_paragraph": a.reading_paragraph,
                    "reading_mcqs": json.loads(a.reading_mcqs) if a.reading_mcqs else [],
                    "writing_prompt": a.writing_prompt,
                    "listening_paragraph": a.listening_paragraph,
                    "writing_answer": a.writing_answer,
                    "listening_answer": a.listening_answer,
                    "mcq_answers": json.loads(a.mcq_answers) if a.mcq_answers else {},
                    "writing_score": a.writing_score,
                    "listening_score": a.listening_score,
                    "mcq_score": a.mcq_score,
                    "total_score": a.total_score,
                    "passed": a.passed,
                    "submitted_at": a.submitted_at
                })
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
