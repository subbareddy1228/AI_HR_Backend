#!/usr/bin/env python3
"""
Database Structure Analysis
Understanding the recruiter job posting and candidate application process
"""

from core.database import SessionLocal
from model.models import User, Job, Candidate, Application

def analyze_database():
    db = SessionLocal()
    
    print("=" * 60)
    print("DATABASE STRUCTURE ANALYSIS")
    print("=" * 60)
    
    # Count records
    print(f"\n RECORD COUNTS:")
    print(f"   Users: {db.query(User).count()}")
    print(f"   Jobs: {db.query(Job).count()}")
    print(f"   Candidates: {db.query(Candidate).count()}")
    print(f"   Applications: {db.query(Application).count()}")
    
    # Recruiter details
    print(f"\n RECRUITER DETAILS:")
    user = db.query(User).filter(User.id == 4).first()
    if user:
        print(f"   ID: {user.id}")
        print(f"   Name: {user.name}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Company: {user.company_name}")
    
    # Jobs posted by recruiter
    print(f"\n JOBS POSTED BY RECRUITER:")
    jobs = db.query(Job).filter(Job.recruiter_id == 4).all()
    for job in jobs:
        print(f"   Job {job.id}: {job.title}")
        print(f"     Department: {job.department}")
        print(f"     Status: {job.status}")
        print(f"     Created: {job.created_at}")
        print(f"     Skills: {job.skills}")
    
    # Applications to each job
    print(f"\n APPLICATIONS TO EACH JOB:")
    for job in jobs:
        apps = db.query(Application).filter(Application.job_id == job.id).all()
        print(f"   Job {job.id} ({job.title}): {len(apps)} applications")
        for app in apps[:5]:  # Show first 5 applications
            print(f"     - {app.candidate_name} ({app.candidate_email})")
            print(f"       Status: {app.status}")
            print(f"       Applied: {app.applied_at}")
    
    # Candidate details
    print(f"\n CANDIDATE DETAILS:")
    candidates = db.query(Candidate).limit(5).all()
    for candidate in candidates:
        print(f"   {candidate.name}:")
        print(f"     Role: {candidate.role}")
        print(f"     Email: {candidate.email}")
        print(f"     Skills: {candidate.skills}")
        print(f"     Stage: {candidate.stage}")
        print(f"     Notes: {candidate.notes}")
    
    # Application flow analysis
    print(f"\n APPLICATION FLOW ANALYSIS:")
    print("   1. Recruiter (User) creates Job")
    print("   2. Candidate applies to Job")
    print("   3. Application record links Candidate to Job")
    print("   4. Application status tracks progress")
    
    # Relationships
    print(f"\nDATABASE RELATIONSHIPS:")
    print("   User (1) → Job (Many) [recruiter_id]")
    print("   Job (1) → Application (Many) [job_id]")
    print("   Candidate (1) → Application (Many) [candidate_id]")
    print("   Application links Job and Candidate")
    
    db.close()

if __name__ == "__main__":
    analyze_database()
