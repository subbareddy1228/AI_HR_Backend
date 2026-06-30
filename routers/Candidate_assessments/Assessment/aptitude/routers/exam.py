from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from urllib.parse import quote_plus
from core.database import get_db
from model.models import LegacyQuestion as Question
from model.models import LegacyCandidate as Candidate
from model.models import Assignment, Assessment
from ..schemas.exam import ExamStartRequest, SubmitExam
from ..schemas.candidate import CandidateCreate, OTPVerify
from ..utils import generate_otp, send_email, assign_questions
from ...utils.stage_sync import update_candidate_stage_both_tables
import os

router = APIRouter()

TEMP_OTPS = {}


def get_base_url():
    """Get the base URL for the frontend application"""
    return os.getenv("FRONTEND_URL", "http://localhost:3000")


@router.post("/send")
def send_otp(data: CandidateCreate, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter_by(email=data.email).first()
    if not candidate:
        candidate = Candidate(
            name=data.name,
            email=data.email,
            status="Pending",
            score=0,
            verified=0,          
            answers={}
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

    otp_code = generate_otp()
    TEMP_OTPS[candidate.email] = otp_code
    send_email(candidate.email, "Your OTP", f"Your OTP is: {otp_code}")
    return {"message": "OTP sent successfully"}


@router.post("/verify")
def verify_otp(data: OTPVerify, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter_by(email=data.email).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if TEMP_OTPS.get(data.email) != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    candidate.verified = 1 
    db.commit()
    TEMP_OTPS.pop(data.email, None)
    return {"message": "OTP verified successfully"}


@router.get("/instructions")
def instructions(email: str = None, db: Session = Depends(get_db)):
    """
    Get exam instructions. If email is provided, try to find the assigned assessment
    to get the correct question count.
    """
    question_count = 25 
    time_limit_seconds = 1800  
    
    
    if email:
        try:
            candidate_record_result = db.execute(
                text("SELECT id FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
                {"email": email}
            ).first()
            
            if candidate_record_result:
                candidate_record_id = candidate_record_result[0]
                
                
                aptitude_assignment = db.query(Assignment).join(Assessment).filter(
                    Assignment.candidate_id == candidate_record_id,
                    Assessment.type == "aptitude"
                ).first()
                
                if aptitude_assignment:
                    assessment = db.query(Assessment).filter(Assessment.id == aptitude_assignment.assessment_id).first()
                    if assessment and assessment.question_count > 0:
                        question_count = assessment.question_count
                        
                        time_limit_seconds = question_count * 60
        except Exception as e:
            print(f"Warning: Could not get assessment instructions: {e}")
    
    return {
        "round_name": "Aptitude Test",
        "time_limit_seconds": time_limit_seconds,
        "total_questions": question_count,
        "instructions": f"Answer all {question_count} MCQs in {time_limit_seconds // 60} minutes. Do not refresh the page."
    }

@router.get("/get_set/{set_no}")
def get_set(set_no: int, db: Session = Depends(get_db)):
    questions = db.query(Question).filter(Question.set_no == set_no).all()
    if not questions:
        raise HTTPException(status_code=404, detail=f"No questions found for set {set_no}")
    return questions

@router.post("/start")
def start_exam(data: ExamStartRequest, db: Session = Depends(get_db)):
    
    candidate = db.query(Candidate).filter_by(id=data.student_id).first()
    
    
    if not candidate and data.email:
        candidate = db.query(Candidate).filter_by(email=data.email).first()
    
    if not candidate:
        
        candidate = Candidate(
            id=data.student_id,
            name="Exam Candidate",
            email=data.email if data.email else f"candidate_{data.student_id}@exam.com",
            status="Pending",
            score=0,
            verified=1,
            answers={}
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)
    
    
    candidate_email = candidate.email if candidate.email else (data.email if data.email else None)
    if candidate_email:
        try:
            candidate_record_result = db.execute(
                text("SELECT id, stage FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
                {"email": candidate_email}
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
        
    

    actual_student_id = candidate.id

    
    question_count = 25  
    try:
       
        candidate_record_result = db.execute(
            text("SELECT id FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
            {"email": candidate_email}
        ).first()
        
        if candidate_record_result:
            candidate_record_id = candidate_record_result[0]
            
            
            aptitude_assignment = db.query(Assignment).join(Assessment).filter(
                Assignment.candidate_id == candidate_record_id,
                Assessment.type == "aptitude"
            ).first()
            
            if aptitude_assignment:
                assessment = db.query(Assessment).filter(Assessment.id == aptitude_assignment.assessment_id).first()
                if assessment and assessment.question_count > 0:
                    question_count = assessment.question_count
                    print(f"✅ Using Assessment question_count: {question_count} for assessment '{assessment.name}'")
    except Exception as e:
        print(f"Warning: Could not find assigned assessment, using default question_count: {e}")

    question_objs = assign_questions(actual_student_id, question_count)
    if not question_objs:
        raise HTTPException(
            status_code=404, 
            detail="No questions available. Please run 'python init_aptitude_questions.py' to load questions into the database."
        )

    
    candidate.answers = {str(i + 1): q.id for i, q in enumerate(question_objs)}
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    
   
    try:
        if candidate.email:
            update_candidate_stage_both_tables(db, candidate.email, "Screening")
    except Exception as e:
        print(f"Warning: Could not update candidate stage: {e}")
        

    exam_view = [{"no": i + 1, "question": q.question, "options": q.options} for i, q in enumerate(question_objs)]
    return {"questions": exam_view, "candidate_id": candidate.id}

@router.post("/submit")
def submit_exam(data: SubmitExam, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter_by(id=data.student_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    assigned_qids = candidate.answers
    if not assigned_qids:
        raise HTTPException(status_code=400, detail="Exam not started or questions missing")

    score = 0
    for q_no_str, selected_option in data.answers.items():
        q_id = assigned_qids.get(str(q_no_str))
        if not q_id:
            continue
        q_obj = db.query(Question).filter_by(id=q_id).first()
        if q_obj and selected_option == q_obj.answer:
            score += 1

    
    total_questions = len(assigned_qids)
    passing_score = max(1, int(total_questions * 0.6))  
    
    candidate.score = score
    candidate.status = "Qualified" if score >= passing_score else "Regret"
    candidate.answers = data.answers

    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    
    
    try:
        
        candidate_record_result = db.execute(
            text("SELECT id, candidate_name FROM candidate_records WHERE candidate_email = :email LIMIT 1"),
            {"email": candidate.email}
        ).first()
        
        if candidate_record_result:
            candidate_record_id = candidate_record_result[0]
            candidate_name = candidate_record_result[1] if len(candidate_record_result) > 1 else candidate.name
            
            
            aptitude_assessments = db.query(Assessment).filter(
                Assessment.type == "aptitude"
            ).all()
            
            for assessment in aptitude_assessments:
                assignment = db.query(Assignment).filter(
                    Assignment.candidate_id == candidate_record_id,
                    Assignment.assessment_id == assessment.id
                ).first()
                
                if assignment and assignment.status != "Completed":
                    assignment.status = "Completed"
                    db.add(assignment)
            
            db.commit()
            
            
            if candidate.status == "Qualified":
                try:
                    communication_link = f"{get_base_url()}/assessment/communication?name={quote_plus(candidate_name)}&email={quote_plus(candidate.email)}"
                    
                    total_questions = len(candidate.answers) if candidate.answers else 25
                    
                    email_body = f"""Dear {candidate_name},

🎉 Congratulations! You have successfully passed the Aptitude Test with a score of {score}/{total_questions}.

You are now invited to take the next stage of our assessment:

📢 Communication Assessment
🔗 Test Link: {communication_link}

Instructions:
1. Click on the link above to start your communication assessment
2. You will receive an OTP for verification
3. The test includes Reading, Writing, and Listening sections
4. Complete the test in one sitting

Best of luck!

Best regards,
HR Team - Recruitment"""
                    
                    send_email(candidate.email, "✅ Aptitude Test Passed - Next: Communication Assessment", email_body)
                    print(f"✅ Sent Communication test link to {candidate.email}")
                except Exception as email_error:
                    print(f"Warning: Could not send next assessment email: {email_error}")
            else:
                
                try:
                    update_candidate_stage_both_tables(db, candidate.email, "Rejected")
                except Exception as stage_error:
                    print(f"Warning: Could not update candidate stage: {stage_error}")
                
                
                try:
                    
                    total_questions = len(candidate.answers) if candidate.answers else 25
                    passing_score = max(1, int(total_questions * 0.6))
                    
                    email_body = f"""Dear {candidate_name},

Thank you for taking the Aptitude Test. Unfortunately, you did not meet the qualifying criteria this time (Score: {score}/{total_questions}, Required: {passing_score}/{total_questions}).

We encourage you to enhance your skills and reapply in the future.

Best regards,
HR Team - Recruitment"""
                    
                    send_email(candidate.email, "Aptitude Test Results", email_body)
                except Exception as email_error:
                    print(f"Warning: Could not send rejection email: {email_error}")
                    
    except Exception as e:
        print(f"Warning: Could not update assignment status: {e}")
       

    return {"score": score, "status": candidate.status}
