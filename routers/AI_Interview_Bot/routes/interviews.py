from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from core.database import get_db, engine
from core.dependencies import get_current_user
from model.models import Question, Answer, InterviewCandidate, AIInterviewTemplate, User, Job, Application, Candidate
from sqlmodel import select
from ..utils.ai_analysis import score_answer
from ..utils.email_utils import generate_otp, send_otp
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import os
import shutil

router = APIRouter()
UPLOAD_DIR = "uploads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Run migration on module load to ensure columns exist
def ensure_answer_columns():
    """Ensure all required columns exist in the answers table."""
    try:
        with engine.begin() as conn:
            # Check if question_text column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'answers' 
                AND column_name = 'question_text'
            """))
            
            if result.scalar() == 0:
                conn.execute(text("""
                    ALTER TABLE answers 
                    ADD COLUMN question_text TEXT
                """))
                print("Added 'question_text' column to answers table")
            
            # Check if template_question_index column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'answers' 
                AND column_name = 'template_question_index'
            """))
            
            if result.scalar() == 0:
                conn.execute(text("""
                    ALTER TABLE answers 
                    ADD COLUMN template_question_index INTEGER
                """))
                print("Added 'template_question_index' column to answers table")
            
            # Check if audio_path column exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'answers' 
                AND column_name = 'audio_path'
            """))
            
            if result.scalar() == 0:
                conn.execute(text("""
                    ALTER TABLE answers 
                    ADD COLUMN audio_path VARCHAR
                """))
                print("Added 'audio_path' column to answers table")
            
            result = conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'answers' 
                AND column_name = 'question_id'
            """))
            
            nullable_status = result.scalar() if result.rowcount > 0 else None
            if nullable_status == 'NO':
                try:
                    conn.execute(text("""
                        ALTER TABLE answers 
                        DROP CONSTRAINT IF EXISTS answers_question_id_fkey
                    """))
                except:
                    pass
                
                conn.execute(text("""
                    ALTER TABLE answers 
                    ALTER COLUMN question_id DROP NOT NULL
                """))
                conn.execute(text("""
                    ALTER TABLE answers 
                    ADD CONSTRAINT answers_question_id_fkey 
                    FOREIGN KEY (question_id) 
                    REFERENCES questions(id)
                """))
                print("Made 'question_id' nullable in answers table")
    except Exception as e:
        print(f"⚠ Warning: Could not ensure answer table columns: {e}")
        print("  Database may not be available. The application will continue.")
        import traceback
        traceback.print_exc()

# Initialize database columns lazily (only when needed, not at import time)
# This prevents startup failures if database is not available
def init_db_columns():
    """Initialize database columns. Call this when database is ready."""
    try:
        ensure_answer_columns()
    except Exception as e:
        print(f"⚠ Warning: Could not initialize database columns: {e}")

# Don't call at import time - let it be called lazily when routes are accessed
# ensure_answer_columns()  # Removed - will be called on first route access if needed

class OTPRequest(BaseModel):
    email: EmailStr
    name: str

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

@router.post("/send_otp")
def send_otp_endpoint(request: OTPRequest, db: Session = Depends(get_db)):
    """
    Generate and send OTP to candidate's email
    """
    try:
        otp = generate_otp()
        candidate = db.query(InterviewCandidate).filter(
            InterviewCandidate.email == request.email
        ).first()
        
        if not candidate:
            candidate = InterviewCandidate(
                name=request.name,
                email=request.email,
                otp=otp,
                otp_created_at=datetime.utcnow()
            )
            db.add(candidate)
        else:
            candidate.otp = otp
            candidate.otp_created_at = datetime.utcnow()
        
        db.commit()
        db.refresh(candidate)
        try:
            send_otp(request.email, otp)
            return {
                "success": True,
                "message": "OTP sent successfully",
                "candidate_id": candidate.id
            }
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            return {
                "success": True,
                "message": "OTP generated (email sending skipped)",
                "candidate_id": candidate.id,
                "otp": otp 
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify_otp")
def verify_otp_endpoint(request: OTPVerify, db: Session = Depends(get_db)):
    """
    Verify OTP for candidate
    """
    try:
        candidate = db.query(InterviewCandidate).filter(
            InterviewCandidate.email == request.email
        ).first()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        if not candidate.otp:
            raise HTTPException(status_code=400, detail="No OTP found for this candidate")
        if candidate.otp_created_at:
            time_diff = datetime.utcnow() - candidate.otp_created_at
            if time_diff > timedelta(minutes=10):
                raise HTTPException(status_code=400, detail="OTP has expired")
        
        if candidate.otp != request.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        candidate.otp = None
        candidate.otp_created_at = None
        db.commit()
        
        return {
            "success": True,
            "message": "OTP verified successfully",
            "candidate_id": candidate.id,
            "candidate_name": candidate.name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    """
    Get all available AI Interview Templates
    """
    templates = db.query(AIInterviewTemplate).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "interview_type": t.interview_type,
            "difficulty": t.difficulty,
            "time_limit": t.time_limit,
            "question_count": len(t.questions) if t.questions else 0
        }
        for t in templates
    ]

@router.get("/get_questions")
def get_questions(
    template_id: int = Query(None, description="AI Interview Template ID"),
    db: Session = Depends(get_db)
):
    """
    Get interview questions from AI Interview Template.
    If template_id is provided, use that template's questions.
    Otherwise, use the first available template.
    """
    
    # If template_id is provided, fetch that specific template
    if template_id:
        template = db.query(AIInterviewTemplate).filter(AIInterviewTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} not found")
    else:
        # Get the first available template
        template = db.query(AIInterviewTemplate).first()
        
        # If no template exists, return an error
        if not template:
            raise HTTPException(
                status_code=404, 
                detail="No interview templates found. Please create a template first."
            )
    
    formatted_questions = []
    for idx, q in enumerate(template.questions):
        question_type = q.get("type", "video") 
        formatted_questions.append({
            "id": idx + 1,  
            "text": q.get("q", ""),
            "type": question_type,  
            "template_id": template.id,
            "template_name": template.name
        })
    
    return formatted_questions

@router.post("/submit_answer")
def submit_answer(
    candidate_id: int = Form(...),
    question_id: int = Form(...),
    question_text: str = Form(...),
    answer_text: str = Form(None),
    audio: UploadFile = File(None),
    video: UploadFile = File(None),  
    db: Session = Depends(get_db)
):
    """
    Submit answer for an interview question.
    Since questions come from templates, we need the question text for AI scoring.
    Accepts video file (primary) or audio file (if provided separately).
    """
    print(f"Received answer submission:")
    print(f"   - Candidate ID: {candidate_id}")
    print(f"   - Question ID: {question_id}")
    print(f"   - Question Text: {question_text[:50] if question_text else 'None'}...")
    print(f"   - Answer Text: {answer_text[:50] if answer_text else 'None'}...")
    print(f"   - Video file received: {video is not None}")
    print(f"   - Audio file received: {audio is not None}")
    if video:
        print(f"   - Video filename: {video.filename}")
        print(f"   - Video content_type: {getattr(video, 'content_type', 'Unknown')}")
    if audio:
        print(f"   - Audio filename: {audio.filename}")
        print(f"   - Audio content_type: {getattr(audio, 'content_type', 'Unknown')}")
    
    audio_path = None
    video_path = None
    
    # Handle video file (primary for video/audio recording)
    if video:
        try:
            # Generate unique filename with timestamp
            timestamp = int(datetime.utcnow().timestamp())
            
            # Get file extension from filename or default to .webm
            if video.filename:
                file_extension = os.path.splitext(video.filename)[1] or '.webm'
            else:
                # Check content type if filename is not available
                content_type = getattr(video, 'content_type', '') or ''
                if 'mp4' in content_type:
                    file_extension = '.mp4'
                else:
                    file_extension = '.webm'
            
            video_filename = f"video_{candidate_id}_{question_id}_{timestamp}{file_extension}"
            video_path_full = os.path.join(UPLOAD_DIR, video_filename)
            # Store relative path for database (uploads/filename)
            video_path = os.path.join("uploads", video_filename).replace("\\", "/")
            
            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            
            # Save video file
            with open(video_path_full, "wb") as buffer:
                shutil.copyfileobj(video.file, buffer)
            
            # Verify file was saved
            if os.path.exists(video_path_full) and os.path.getsize(video_path_full) > 0:
                print(f" Video saved successfully: {video_path_full} (size: {os.path.getsize(video_path_full)} bytes)")
                print(f"   Database path: {video_path}")
            else:
                print(f" Warning: Video file may not have been saved properly: {video_path_full}")
                video_path = None
        except Exception as e:
            print(f" Error saving video file: {str(e)}")
            import traceback
            traceback.print_exc()
            video_path = None
    
    # Handle audio file (if provided separately)
    if audio:
        try:
            timestamp = int(datetime.utcnow().timestamp())
            
            # Get file extension from filename or default to .webm
            if audio.filename:
                file_extension = os.path.splitext(audio.filename)[1] or '.webm'
            else:
                # Check content type if filename is not available
                content_type = getattr(audio, 'content_type', '') or ''
                if 'mp4' in content_type or 'm4a' in content_type:
                    file_extension = '.m4a'
                else:
                    file_extension = '.webm'
            
            audio_filename = f"audio_{candidate_id}_{question_id}_{timestamp}{file_extension}"
            audio_path_full = os.path.join(UPLOAD_DIR, audio_filename)
            # Store relative path for database (uploads/filename)
            audio_path = os.path.join("uploads", audio_filename).replace("\\", "/")
            
            # Ensure upload directory exists
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            
            # Save audio file
            with open(audio_path_full, "wb") as buffer:
                shutil.copyfileobj(audio.file, buffer)
            
            # Verify file was saved
            if os.path.exists(audio_path_full) and os.path.getsize(audio_path_full) > 0:
                print(f" Audio saved successfully: {audio_path_full} (size: {os.path.getsize(audio_path_full)} bytes)")
                print(f"   Database path: {audio_path}")
            else:
                print(f" Warning: Audio file may not have been saved properly: {audio_path_full}")
                audio_path = None
        except Exception as e:
            print(f" Error saving audio file: {str(e)}")
            import traceback
            traceback.print_exc()
            audio_path = None

    # Calculate AI score if text answer is provided
    score = None
    if answer_text and question_text:
        try:
            score = score_answer(question_text, answer_text)
            print(f"AI Score for candidate {candidate_id}, question {question_id}: {score}/10")
        except Exception as e:
            print(f" Error calculating AI score: {str(e)}")
            score = 0  # Default score if AI fails

    # Save answer to database
    # For template questions, question_id is just an index, not a foreign key
    # So we store question_text directly and set question_id to None
    ans = Answer(
        candidate_id=candidate_id,
        question_id=None,  # Template questions don't have Question records
        question_text=question_text,  # Store question text directly
        template_question_index=question_id,  # Store the index from template
        answer_text=answer_text,
        audio_path=audio_path,  # Store audio path (if provided separately)
        video_path=video_path,  # Store video path (primary for video/audio recording)
        score=score
    )
    db.add(ans)
    db.commit()
    db.refresh(ans)
    
    # Log saved answer details for debugging
    print(f" Answer saved to database:")
    print(f"   - Answer ID: {ans.id}")
    print(f"   - Candidate ID: {candidate_id}")
    print(f"   - Question Index: {question_id}")
    print(f"   - Question Text: {question_text[:50] if question_text else 'None'}...")
    print(f"   - Video Path: {video_path or 'None'}")
    print(f"   - Audio Path: {audio_path or 'None'}")
    print(f"   - Answer Text: {answer_text[:50] if answer_text else 'None'}...")
    print(f"   - Score: {score}")

    return {
        "message": "Answer submitted successfully",
        "score": score,
        "answer_id": ans.id,
        "video_path": video_path,
        "audio_path": audio_path
    }

@router.get("/results")
def get_interview_results(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Get all interview results with candidate information and scores, filtered by recruiter
    """
    print(f" Fetching interview results for user: {user.id} (role: {user.role})")
    
    # Get recruiter's candidate emails
    recruiter_candidate_emails = set()
    recruiter_has_jobs = False
    
    if user.role.lower() != "admin":
        # Get all job IDs for this recruiter
        job_ids = list(db.exec(select(Job.id).where(Job.recruiter_id == user.id)).all())
        print(f" Recruiter {user.id} has {len(job_ids)} jobs")
        recruiter_has_jobs = len(job_ids) > 0
        
        if job_ids:
            # Get all applications for these jobs
            applications = db.exec(select(Application).where(Application.job_id.in_(job_ids))).all()
            print(f"🔍 Found {len(applications)} applications for recruiter's jobs")
            
            # Get unique candidate emails from applications
            for app in applications:
                if app.candidate_email:
                    recruiter_candidate_emails.add(app.candidate_email.lower().strip())
            
            # Also get emails from Candidate table
            candidate_ids = list(set([app.candidate_id for app in applications if app.candidate_id]))
            if candidate_ids:
                candidates = db.exec(select(Candidate).where(Candidate.id.in_(candidate_ids))).all()
                for candidate in candidates:
                    if candidate.email:
                        recruiter_candidate_emails.add(candidate.email.lower().strip())
        
        print(f" Recruiter {user.id} has {len(recruiter_candidate_emails)} unique candidate emails from applications")
        if recruiter_candidate_emails:
            sample_emails = list(recruiter_candidate_emails)[:5]
            print(f" Sample emails: {sample_emails}")
    
    # Get all candidates who have submitted answers
    query = db.query(InterviewCandidate).join(
        Answer, InterviewCandidate.id == Answer.candidate_id
    ).distinct()
    
    # Filter by recruiter's candidate emails (unless admin)
    if user.role.lower() != "admin":
        if recruiter_candidate_emails:
            query = query.filter(
                func.lower(func.trim(InterviewCandidate.email)).in_(
                    [email.lower().strip() for email in recruiter_candidate_emails]
                )
            )
            print(f" Filtering interview candidates by {len(recruiter_candidate_emails)} emails from applications")
        elif recruiter_has_jobs:
            # Recruiter has jobs but no applications yet - return empty
            print(f" Recruiter {user.id} has jobs but no applications, returning empty results")
            return []
        else:
            # No jobs at all - return empty
            print(f" Recruiter {user.id} has no jobs, returning empty results")
            return []
    
    candidates_with_answers = query.all()
    print(f" Found {len(candidates_with_answers)} candidates with interview answers")
    
    results = []
    for candidate in candidates_with_answers:
        # Get all answers for this candidate
        answers = db.query(Answer).filter(Answer.candidate_id == candidate.id).all()
        
        # Calculate statistics
        total_score = sum(a.score or 0 for a in answers)
        max_score = len(answers) * 10
        avg_score = (total_score / max_score * 100) if max_score > 0 else 0
        
        # Format answers
        formatted_answers = []
        for answer in answers:
            formatted_answers.append({
                "question_id": answer.template_question_index or answer.question_id,
                "question_text": answer.question_text,
                "answer_text": answer.answer_text,
                "audio_path": answer.audio_path,
                "video_path": answer.video_path,
                "score": answer.score or 0
            })
        
        results.append({
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "candidate_email": candidate.email,
            "total_questions": len(answers),
            "total_score": total_score,
            "max_score": max_score,
            "avg_score": round(avg_score, 1),
            "answers": formatted_answers
        })
    
    return results

@router.get("/results/{candidate_id}")
def get_candidate_interview_result(candidate_id: int, db: Session = Depends(get_db)):
    """
    Get interview result for a specific candidate with detailed answers
    """
    candidate = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    answers = db.query(Answer).filter(Answer.candidate_id == candidate_id).all()
    
    if not answers:
        raise HTTPException(status_code=404, detail="No interview answers found for this candidate")
    
    # Calculate statistics
    total_score = sum(a.score or 0 for a in answers)
    max_score = len(answers) * 10
    avg_score = (total_score / max_score * 100) if max_score > 0 else 0
    
    # Format answers with question details
    formatted_answers = []
    for answer in answers:
        formatted_answers.append({
            "question_id": answer.template_question_index or answer.question_id,
            "question_text": answer.question_text,
            "answer_text": answer.answer_text,
            "audio_path": answer.audio_path,
            "video_path": answer.video_path,
            "score": answer.score or 0
        })
    
    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.name,
        "candidate_email": candidate.email,
        "total_questions": len(answers),
        "total_score": total_score,
        "max_score": max_score,
        "avg_score": round(avg_score, 1),
        "answers": formatted_answers
    }
