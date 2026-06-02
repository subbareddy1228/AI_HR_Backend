import random
import ssl
import smtplib
import json
import re
import time
import os
import openai
from dotenv import load_dotenv
from typing import Optional, Dict,Tuple
from email.mime.text import MIMEText

#  Load environment 
load_dotenv()

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#  OpenAI Setup 
openai.api_key = OPENAI_API_KEY

#  OTP 
otp_store: Dict[str, Dict] = {}  # store OTPs

def generate_otp(length: int = 6) -> str:
    """Generate a numeric OTP of specified length."""
    return ''.join(random.choices("0123456789", k=length))

def send_email(to: str, subject: str, body: str) -> Tuple[bool, str]:
    """Send email using Gmail SMTP SSL. Returns (success, message)."""
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        return True, f" Email sent successfully to {to}"
    except Exception as e:
        return False, f" Email error while sending to {to}: {e}"

#  AI Exam 
def generate_full_exam(candidate_email: str, candidate_name: str) -> Optional[Dict]:
    """Generate a professional communication exam using OpenAI API."""
    prompt = f"""
Generate a professional communication exam for candidate {candidate_name}.
Return ONLY valid JSON with these keys:
1. reading_paragraph: 150-200 words unique paragraph.
2. reading_mcqs: list of 5 questions, each with "question" and "options" (list of 4 choices A-D). Do NOT include answers.
3. writing_prompt: unique writing topic (~150 words). Do NOT include answers.
4. listening_paragraph: 1-2 sentences unique paragraph.
"""
    for attempt in range(5):
        try:
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=1500,
            )
            raw_text = resp.choices[0].message.content.strip()
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                exam_json = json.loads(match.group())
                exam_json["reading_mcqs"] = exam_json.get("reading_mcqs", [])[:5]
                return exam_json
        except Exception as e:
            print(f" Attempt {attempt+1} failed: {e}")
            time.sleep(2)
    return None

#  Scoring 
def score_text(answer: str, prompt: str, max_marks: int) -> int:
    """Score a candidate's answer using OpenAI API."""
    if not answer.strip():
        return 0
    scoring_prompt = (
        f"Evaluate this response.\nPrompt: {prompt}\nResponse: {answer}\n"
        f"Give integer score ONLY between 0 and {max_marks}."
    )
    for attempt in range(3):
        try:
            resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": scoring_prompt}],
                temperature=0,
                max_tokens=50,
            )
            match = re.search(r"\d+", resp.choices[0].message.content)
            if match:
                return min(int(match.group()), max_marks)
        except Exception as e:
            print(f" Scoring attempt {attempt+1} failed: {e}")
            time.sleep(1)
    return 0

#  Result Email 
def generate_candidate_email(candidate_name: str, passed: bool) -> Dict[str, str]:
    """Prepare email subject and body based on candidate result."""
    if passed:
        subject = "Congratulations - Levitica Technologies"
        body = f"""Dear {candidate_name},

Congratulations! 🎉 You have qualified for the next round of interviews.

Coding round link: https://levitica.com/coding-round
Date: Tomorrow 10:00 AM

Best regards,
HR Team"""
    else:
        subject = "Assessment Result - Levitica Technologies"
        body = f"""Dear {candidate_name},

Thank you for participating in the assessment. Unfortunately, you did not qualify this time.
We encourage you to reapply in the future.

Best regards,
HR Team"""
    return {"subject": subject, "body": body}
