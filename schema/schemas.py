from pydantic import BaseModel, EmailStr
from typing import Optional, List,Literal
from datetime import datetime,date
from enum import Enum
from trio import TaskStatus



# Users 
class UserCreate(BaseModel):
    name: str
    username: Optional[str] = None    
    email: EmailStr
    password: str
    role: Literal["recruiter", "company", "superadmin"]
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_id: Optional[str] = None


class UserRead(BaseModel):
    id: int
    name: str
    email: str
    role: str

# Jobs
class JobBase(BaseModel):
    title: str
    department: str
    employment_type: str
    location: Optional[str] = None
    is_remote: bool = False
    description: str
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    benefits: Optional[List[str]] = []
    skills: Optional[List[str]] = []
    expiry_date: Optional[datetime] = None
    reference_id: Optional[str] = None
    jd_file: Optional[str] = None
    is_draft: bool = False

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    requirements: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    skills: Optional[List[str]] = None
    benefits: Optional[List[str]] = None
    expiry_date: Optional[datetime] = None
    reference_id: Optional[str] = None
    jd_file: Optional[str] = None
    is_draft: Optional[bool] = None

class JobRead(JobBase):
    id: int
    recruiter_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# Candidates
class CandidateCreate(BaseModel):
    name: str
    role: str
    email: EmailStr
    skills: Optional[str] = None
    stage: Optional[str] = "Applied"
    resume_url: Optional[str] = None
    notes: Optional[str] = None
    recruiter_comments: Optional[str] = None

class CandidateRead(CandidateCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True



from pydantic import BaseModel
from typing import Optional

class Profile(BaseModel):
    id: int
    name: str
    role: str
    profile_image_url: str

    class Config:
        from_attributes = True

class JobSearch(BaseModel):
    id: int
    title: str
    company: str
    location: str

    class Config:
        from_attributes = True

class JobSearchCreate(BaseModel):
    title: str
    company: str
    location: str

class SavedJobs(BaseModel):
    id: int
    title: str
    company: str
    location: str

    class Config:
        from_attributes = True

class SavedJobsCreate(BaseModel):
    title: str
    company: str
    location: str

class RecentApplications(BaseModel):
    id: int
    job_title: str
    company: str
    status: str
    applied_days_ago: int

    class Config:
        from_attributes = True

class RecentApplicationsCreate(BaseModel):
    job_title: str
    company: str
    status: str
    applied_days_ago: int

class RecommendedJobSections(BaseModel):
    id: int
    title: str
    company: str
    location: str

    class Config:
        from_attributes = True

class RecommendedJobSectionsCreate(BaseModel):
    title: str
    company: str
    location: str

class Applications(BaseModel):
    id: int
    job_title: str
    company: str
    status: str
    applied_days_ago: Optional[int] = None

    class Config:
        from_attributes = True

class ApplicationsCreate(BaseModel):
    job_title: str
    company: str
    status: str
    applied_days_ago: Optional[int]

class Notifications(BaseModel):
    id: int
    message: str
    is_read: int

    class Config:
        from_attributes = True

class NotificationsCreate(BaseModel):
    message: str
    is_read: Optional[int] = 0



class StageBase(BaseModel):
    name: str
    order: int


class StageCreate(StageBase):
    pass
                                                                                             

class StageUpdate(BaseModel):
    name: Optional[str] = None
    order: Optional[int] = None


class StageOut(StageBase):
    id: int

    model_config = {"from_attributes": True}


class CandidateBase(BaseModel):
    name: str
    role: str
    status: str
    stage_id: int


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    stage_id: Optional[int] = None


class CandidateOut(CandidateBase):
    id: int

    model_config = {"from_attributes": True}


class AnswerSchema(BaseModel):
    question_text: str
    text_response: str
    ai_score: Optional[float]
    ai_feedback: Optional[str]
    class Config:
        orm_mode = True

class NoteSchema(BaseModel):
    notes: Optional[str]
    class Config:
        orm_mode = True

class CandidateSchema(BaseModel):
    id: int
    name: str
    email: str
    role: str
    location: Optional[str]
    experience_level: Optional[str]
    overall_ai_score: Optional[float]
    assessment_score: Optional[float]
    final_score: Optional[float]
    answers: List[AnswerSchema] = []
    notes: List[NoteSchema] = []
    class Config:
        orm_mode = True

# Attendance & Leave

class LeaveStatus(str, Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"

class AttendanceCreate(BaseModel):
    date: date
    status: str

class AttendanceOut(BaseModel):
    id: int
    date: date
    status: str

    class Config:
        orm_mode = True

class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    reason: str

class LeaveRequestOut(BaseModel):
    id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus

    class Config:
        orm_mode = True



# Document Schemas
class DocumentBase(BaseModel):
    title: str

class DocumentCreate(DocumentBase):
    pass  

class Document(DocumentBase):
    id: int
    filename: str
    file_path: str

    class Config:
        orm_mode = True 



# Signature Schemas
class SignatureBase(BaseModel):
    name: str

class SignatureCreate(SignatureBase):
    pass  

class Signature(SignatureBase):
    id: int
    filename: str
    file_path: str

    class Config:
        orm_mode = True

# Candidate schemas
class CandidateCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    joining_date: Optional[date]

class CandidateOut(CandidateCreate):
    id: int
    class Config:
        orm_mode = True

# Document schemas
class DocumentCreate(BaseModel):
    name: str

class DocumentOut(DocumentCreate):
    id: int
    class Config:
        orm_mode = True

# Upload schemas
class UploadCreate(BaseModel):
    candidate_id: int
    document_id: int
    file_path: str

class UploadOut(UploadCreate):
    id: int
    class Config:
        orm_mode = True

# Task schemas

class TaskStatus(str, Enum):
    pending = "Pending"
    in_progress = "In Progress"
    completed = "Completed"

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assignee: str
    status: Optional[TaskStatus] = TaskStatus.pending
    due_date: Optional[date] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[str] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[date] = None

class TaskOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    assignee: str
    status: TaskStatus
    due_date: Optional[date]

    model_config = {
        "from_attributes": True
    }

