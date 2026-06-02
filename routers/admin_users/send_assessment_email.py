from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Email configuration from environment
EMAIL_USER = os.getenv("EMAIL_USER", "your-email@gmail.com")
EMAIL_PASS = os.getenv("EMAIL_PASS", "your-app-password")

class AssessmentEmailRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    subject: str
    body: str
    test_type: str
    test_link: str = None
    test_links: dict = None

@router.post("/api/send-assessment-email")
async def send_assessment_email(request: AssessmentEmailRequest):
    """
    Send assessment link to candidate via email
    """
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = request.subject
        msg['From'] = EMAIL_USER
        msg['To'] = request.to_email
        
        # Create HTML version of the email
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
                        background-color: #4F46E5;
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
                    .button {{
                        display: inline-block;
                        padding: 12px 30px;
                        margin: 20px 0;
                        background-color: #4F46E5;
                        color: white;
                        text-decoration: none;
                        border-radius: 5px;
                        font-weight: bold;
                    }}
                    .test-link {{
                        background-color: #EEF2FF;
                        padding: 15px;
                        border-left: 4px solid #4F46E5;
                        margin: 15px 0;
                        word-break: break-all;
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
                        <h2> Assessment Invitation</h2>
                    </div>
                    <div class="content">
                        <p>{request.body.replace(chr(10), '<br>')}</p>
                    </div>
                    <div class="footer">
                        <p>This is an automated email. Please do not reply.</p>
                        <p>&copy; 2024 AI Recruitment Platform. All rights reserved.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        # Attach both plain text and HTML versions
        text_part = MIMEText(request.body, 'plain')
        html_part = MIMEText(html_body, 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email via SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        
        return {
            "success": True,
            "message": f"Assessment email sent successfully to {request.to_name}",
            "to_email": request.to_email
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
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )

