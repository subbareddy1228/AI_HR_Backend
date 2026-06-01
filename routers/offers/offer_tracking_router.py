from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_user
from model.models import User
from .services.offer_tracking_service import (
    create_offer,
    get_offers,
    get_offer,
    update_offer,
    update_offer_status,
    delete_offer,
    get_offer_stats
)
from schema.offer_tracking import (
    OfferTrackingCreate,
    OfferTrackingOut,
    OfferTrackingUpdate,
    OfferStatusUpdate
)
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from model.models import OfferStatus

load_dotenv()

router = APIRouter(prefix="/offer-tracking", tags=["Offer Tracking"])

# Email configuration
EMAIL_USER = os.getenv("EMAIL_USER", "your-email@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "your-app-password")

class SendOfferRequest(BaseModel):
    candidate_id: int
    candidate_name: str
    candidate_email: EmailStr
    template_id: Optional[int] = None
    position: str
    department: Optional[str] = None
    salary_offered: Optional[float] = None
    benefits: List[str] = []
    offer_content: str
    expiry_days: Optional[int] = 30
    notes: Optional[str] = None

@router.post("/", response_model=OfferTrackingOut)
def create_offer_endpoint(data: OfferTrackingCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Create a new offer"""
    data_dict = data.dict()
    if not data_dict.get('created_by'):
        data_dict['created_by'] = user.id
    data = OfferTrackingCreate(**data_dict)
    return create_offer(db, data)

@router.get("/", response_model=List[OfferTrackingOut])
def list_offers(
    status: Optional[str] = None,
    candidate_id: Optional[int] = None,
    position: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Get all offers with optional filters, filtered by recruiter"""
    return get_offers(db, status, candidate_id, position, user)

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get offer statistics filtered by recruiter"""
    return get_offer_stats(db, user)

@router.get("/{offer_id}", response_model=OfferTrackingOut)
def get_offer_endpoint(offer_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Get a specific offer"""
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    if user.role.lower() != "admin" and offer.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    return offer

@router.put("/{offer_id}", response_model=OfferTrackingOut)
def update_offer_endpoint(
    offer_id: int,
    data: OfferTrackingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Update an offer"""
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if user.role.lower() != "admin" and offer.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    update_dict = data.dict(exclude_unset=True)
    updated = update_offer(db, offer_id, update_dict)
    if not updated:
        raise HTTPException(status_code=404, detail="Offer not found")
    return updated

@router.patch("/{offer_id}/status", response_model=OfferTrackingOut)
def update_status_endpoint(
    offer_id: int,
    data: OfferStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Update offer status"""
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if user.role.lower() != "admin" and offer.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    updated = update_offer_status(db, offer_id, data.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Offer not found")
    return updated

@router.delete("/{offer_id}")
def delete_offer_endpoint(offer_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Delete an offer"""
    offer = get_offer(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if user.role.lower() != "admin" and offer.created_by != user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    
    success = delete_offer(db, offer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"message": "Offer deleted successfully"}

@router.post("/send-offer")
def send_offer_endpoint(request: SendOfferRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """
    Create an offer, send it via email, and update candidate stage to 'Offered'
    """
    try:
        from model.models import Candidate
        from sqlalchemy import func
        
        actual_candidate_id = request.candidate_id
        if request.candidate_email:
            # Try to find candidate in main candidate table by email
            candidate = db.query(Candidate).filter(
                func.lower(func.trim(Candidate.email)) == request.candidate_email.lower().strip()
            ).first()
            
            if candidate:
                actual_candidate_id = candidate.id
                print(f" Found candidate in main table: ID={candidate.id}, Email={candidate.email}")
            else:
                # If candidate doesn't exist in main table, create one or use None
                print(f" Candidate with email {request.candidate_email} not found in main candidate table")
                # Set candidate_id to None - the offer will still be created with candidate_name and candidate_email
                actual_candidate_id = None
        
        # Calculate expiry date
        expiry_date = None
        if request.expiry_days:
            expiry_date = (datetime.utcnow() + timedelta(days=request.expiry_days)).date()
        
        # Create offer tracking record
        offer_data = OfferTrackingCreate(
            candidate_id=actual_candidate_id,  
            template_id=request.template_id,
            candidate_name=request.candidate_name,
            candidate_email=request.candidate_email,
            position=request.position,
            department=request.department,
            salary_offered=request.salary_offered,
            benefits=request.benefits,
            offer_content=request.offer_content,
            expiry_date=expiry_date,
            notes=request.notes,
            created_by=user.id
        )
        
        offer = create_offer(db, offer_data)
        
        # Update offer status to "sent" and set sent_date
        update_offer_status(db, offer.id, OfferStatus.sent)
        
        # Update candidate stage to 'Offered' if we found the candidate
        if actual_candidate_id:
            try:
                from routers.Candidate_assessments.Assessment.utils.stage_sync import update_candidate_stage_all_tables
                update_candidate_stage_all_tables(db, request.candidate_email, 'Offered')
                print(f" Updated candidate stage to 'Offered' for candidate_id={actual_candidate_id}")
            except Exception as e:
                print(f" Could not update candidate stage: {e}")
        
        # Send email
        subject = f"Job Offer - {request.position}"
        
        # Create HTML email body
        html_body = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f9f9f9;
                    }}
                    .header {{
                        background-color: #28a745;
                        color: white;
                        padding: 20px;
                        text-align: center;
                        border-radius: 5px 5px 0 0;
                    }}
                    .content {{
                        background-color: white;
                        padding: 30px;
                        border-radius: 0 0 5px 5px;
                    }}
                    .offer-details {{
                        background-color: #f8f9fa;
                        padding: 15px;
                        border-left: 4px solid #28a745;
                        margin: 15px 0;
                    }}
                    .footer {{
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🎉 Congratulations! Job Offer</h2>
                    </div>
                    <div class="content">
                        <p>Dear {request.candidate_name},</p>
                        <p>{request.offer_content.replace(chr(10), '<br>')}</p>
                        <div class="offer-details">
                        {f'<strong>Position:</strong> {request.position}<br>' if request.position else ''}
                        {f'<strong>Department:</strong> {request.department}<br>' if request.department else ''}
                        {f'<strong>Salary:</strong> ${request.salary_offered:,.2f}<br>' if request.salary_offered else ''}
                        {f'<strong>Benefits:</strong> {", ".join(request.benefits)}<br>' if request.benefits else ''}
                        {f'<strong>Offer Valid Until:</strong> {expiry_date.strftime("%B %d, %Y")}' if expiry_date else ''}
                        </div>
                        <p>We look forward to welcoming you to our team!</p>
                        <p>Best regards,<br>Recruitment Team</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = request.candidate_email
        
        # Attach both plain text and HTML versions
        text_part = MIMEText(request.offer_content, 'plain')
        html_part = MIMEText(html_body, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email via SMTP
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_USER, EMAIL_PASS)
                server.send_message(msg)
            
            # Update candidate stage to "Offered"
            from routers.Candidate_assessments.Assessment.utils.stage_sync import update_candidate_stage_all_tables
            update_candidate_stage_all_tables(db, request.candidate_email, "Offered")
            
            return {
                "success": True,
                "message": f"Offer sent successfully to {request.candidate_name}",
                "offer_id": offer.id,
                "candidate_email": request.candidate_email
            }
        except smtplib.SMTPAuthenticationError:
            raise HTTPException(
                status_code=500,
                detail="Email authentication failed. Please check email configuration."
            )
        except smtplib.SMTPException as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email: {str(e)}"
            )
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )

