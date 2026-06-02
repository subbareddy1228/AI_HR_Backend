import random
import string
import smtplib
import ssl
import json
import subprocess
import tempfile
import re
from datetime import datetime, timedelta
from .config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS,
    EMAIL_USER, EMAIL_PASS, openai_client
)
import psycopg2

#  OTP 
# Store OTP with expiration: { email: {"otp": "123456", "expires": datetime } }
otp_store = {}
OTP_VALIDITY_MINUTES = 5

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def store_otp(email, otp):
    otp_store[email] = {
        "otp": otp,
        "expires": datetime.utcnow() + timedelta(minutes=OTP_VALIDITY_MINUTES)
    }

def verify_otp(email, otp):
    entry = otp_store.get(email)
    if not entry:
        return False
    # Expired OTP
    if datetime.utcnow() > entry["expires"]:
        otp_store.pop(email, None)
        return False
    if entry["otp"] == otp:
        otp_store.pop(email, None)
        return True
    return False

def send_email(receiver, subject, body):
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, receiver, f"Subject: {subject}\n\n{body}")
        return True
    except Exception as e:
        print("Email error:", e)
        return False

#  Database 
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )

def save_submission(name, email, question_title, language, code, output, success):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coding_assessment_results (
            id SERIAL PRIMARY KEY,
            candidate_name TEXT,
            candidate_email TEXT,
            question_title TEXT,
            language TEXT,
            code TEXT,
            output TEXT,
            success BOOLEAN,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        INSERT INTO coding_assessment_results(candidate_name, candidate_email, question_title, language, code, output, success)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (name, email, question_title, language, code, output, success))
    conn.commit()
    cur.close()
    conn.close()

#  AI Questions 
def ai_or_fallback_questions():
    fallback_questions = [
        {
            "title":"Longest Palindromic Substring",
            "description":"Given a string s, return the longest palindromic substring.",
            "test_cases":["Input: 'babad'", "Output: 'bab' or 'aba'", "Input: 'cbbd'", "Output: 'bb'"]
        },
        {
            "title":"Merge Intervals",
            "description":"Given a collection of intervals, merge all overlapping intervals.",
            "test_cases":["Input: [[1,3],[2,6],[8,10],[15,18]]","Output: [[1,6],[8,10],[15,18]]"]
        }
    ]
    if not openai_client:
        return fallback_questions
    try:
        prompt = (
            "Generate 2 advanced coding questions in JSON format strictly as a JSON array: "
            "[{\"title\":\"...\",\"description\":\"...\",\"test_cases\":[\"Input: ...\",\"Output: ...\"]},"
            " {\"title\":\"...\",\"description\":\"...\",\"test_cases\":[\"Input: ...\",\"Output: ...\"]}]"
        )
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7
        )
        text = resp.choices[0].message.content
        match = re.search(r"\[.*\]", text, re.DOTALL)
        return json.loads(match.group(0)) if match else fallback_questions
    except Exception:
        return fallback_questions

#  Run Code 
def run_code_detailed(language, code):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if language == "python":
                file_path = tmpdir+"/main.py"
                with open(file_path, "w") as f: f.write(code)
                cmd = ["python", file_path]
            elif language == "cpp":
                file_path = tmpdir+"/main.cpp"
                exe_path = tmpdir+"/a.out"
                with open(file_path, "w") as f: f.write(code)
                compile_proc = subprocess.run(["g++", file_path, "-o", exe_path], capture_output=True, text=True)
                if compile_proc.returncode != 0:
                    return False, compile_proc.stderr
                cmd = [exe_path]
            elif language == "java":
                file_path = tmpdir+"/Main.java"
                with open(file_path, "w") as f: f.write(code)
                compile_proc = subprocess.run(["javac", file_path], capture_output=True, text=True)
                if compile_proc.returncode != 0:
                    return False, compile_proc.stderr
                cmd = ["java", "-cp", tmpdir, "Main"]
            else:
                return False, "Unsupported language"
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            success = proc.returncode == 0
            output = (proc.stdout or "") + (proc.stderr or "")
            return success, output
    except Exception as e:
        return False, str(e)

#  AI Email 
def generate_ai_email(name, status_text):
    if not openai_client:
        return f"Dear {name},\nYou are {status_text} after the coding exam.\nWith regards, HR Team."
    prompt = f"Write a professional email to {name}. Inform them they are {status_text} after the coding exam. End with 'With regards, HR Team.'"
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"Dear {name},\nYou are {status_text} after the coding exam.\nWith regards, HR Team."

def generate_ai_manager_link(name, email):
    token = ''.join(random.choices(string.ascii_letters+string.digits, k=12))
    return f"https://schedule.example.com/meet/{token}"
