import io
import json
import math
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, Any, Tuple

import pdfplumber
from docx import Document
from openai import OpenAI

from .config import (
    OPENAI_API_KEY,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_FROM,
)



_client = OpenAI(api_key=OPENAI_API_KEY)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    return "\n".join(pages).strip()

def extract_text_from_docx(file_bytes: bytes) -> str:
    with io.BytesIO(file_bytes) as f:
        doc = Document(f)
    return "\n".join([p.text for p in doc.paragraphs]).strip()

def extract_text(filename: str, content: bytes) -> str:
    fname = filename.lower()
    if fname.endswith(".pdf"):
        return extract_text_from_pdf(content)
    if fname.endswith(".docx"):
        return extract_text_from_docx(content)
    raise ValueError("Unsupported file type. Use PDF or DOCX.")

 
def ai_extract_fields(resume_text: str) -> Dict[str, Any]:
    prompt = f"""
Extract the following from this resume:
- name (string)
- email (string)
- skills (array of strings)
- experience_summary (string)

Return only valid JSON.

Resume:
\"\"\"{resume_text[:8000]}\"\"\"
"""
    resp = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You return JSON only."},
                  {"role": "user", "content": prompt}],
        temperature=0.2
    )
    text = resp.choices[0].message.content.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        text = text[text.find("{"): text.rfind("}")+1]
        data = json.loads(text)
    return {
        "name": data.get("name", ""),
        "email": data.get("email", ""),
        "skills": data.get("skills", []),
        "experience_summary": data.get("experience_summary", "")
    }

def ai_generate_jd(role: str, experience_level: str) -> str:
    prompt = f"""
Write a job description for '{role}' at '{experience_level}' level.
Include overview, responsibilities, required skills, and preferred qualifications.
Keep under 350 words.
"""
    resp = _client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return resp.choices[0].message.content.strip()

def _embedding(text: str) -> list:
    emb = _client.embeddings.create(
        model="text-embedding-3-large",
        input=text[:8000]
    )
    return emb.data[0].embedding

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot / (na * nb) if na and nb else 0.0

def ai_similarity_score(resume_text: str, jd_text: str) -> float:
    e1 = _embedding(resume_text)
    e2 = _embedding(jd_text)
    sim = _cosine(e1, e2)
    return round(sim * 100, 2)


def send_email_smtp(to_name: str, to_email: str, score: float, role: str) -> Tuple[bool, str]:
    subject = f"Your Resume Screening Result for {role}"
    body = f"""Hi {to_name or 'Candidate'},

Your resume scored {score:.1f} for the {role} position in our AI screening.

Best regards,
Talent Team
"""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            # Port 587 (Gmail) uses STARTTLS
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls(context=context)
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        return True, "sent"
    except Exception as e:
        return False, str(e)
