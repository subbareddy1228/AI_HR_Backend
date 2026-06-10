
from sqlalchemy import (
    Column, Integer, String, Date, Text, DateTime,
    Boolean, ForeignKey, Float, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from core.database import Base




class ApprovalStatus(str, enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"


class TransferType(str, enum.Enum):
    INTER_DEPARTMENT = "Inter-department"
    INTER_LOCATION = "Inter-location"
    INTERNAL_JOB_POSTING = "Internal Job Posting"


class TransferStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_REVIEW = "in-review"


class ExitStatus(str, enum.Enum):
    INITIATED = "initiated"
    IN_PROCESS = "in-process"
    COMPLETED = "completed"


class ProbationReviewStatus(str, enum.Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"


class EmployeeStage(str, enum.Enum):
    JOINING = "joining"
    PROBATION = "probation"
    ACTIVE = "active"
    TRANSFER_PENDING = "transfer-pending"
    EXIT_PROCESS = "exit-process"
    CONTRACT_RENEWAL = "contract-renewal"
    EXITED = "exited"


class EmployeeLifecycleEvent(Base):
    __tablename__ = "employee_lifecycle_events"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=True)
    from_value = Column(String(255), nullable=True)
    to_value = Column(String(255), nullable=True)
    from_department = Column(String(255), nullable=True)
    to_department = Column(String(255), nullable=True)
    from_designation = Column(String(255), nullable=True)
    to_designation = Column(String(255), nullable=True)
    from_grade = Column(String(100), nullable=True)
    to_grade = Column(String(100), nullable=True)
    from_location = Column(String(255), nullable=True)
    to_location = Column(String(255), nullable=True)
    from_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    to_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    from_salary = Column(String(50), nullable=True)
    to_salary = Column(String(50), nullable=True)
    initiated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approval_status = Column(String(50), default="Approved")
    remarks = Column(Text, nullable=True)
    reference_document = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class OnboardingTask(Base):
   
    __tablename__ = "onboarding_tasks"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    task = Column(String(255), nullable=False)
    assigned_to = Column(String(100), nullable=False)          
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default=TaskStatus.PENDING)    
    completed_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class ProbationReview(Base):
    
    __tablename__ = "probation_reviews"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    review_date = Column(Date, nullable=False)
    manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    manager_name = Column(String(255), nullable=True)         
    status = Column(String(50), default=ProbationReviewStatus.PENDING)
    rating = Column(String(100), nullable=True)                
    remarks = Column(Text, nullable=True)
    eligibility_check_status = Column(String(50), default="Pending")  
    manager_review_status = Column(String(50), default="Pending")     
    letter_generation_status = Column(String(50), default="Pending")  
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TransferRequest(Base):
  
    __tablename__ = "transfer_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee_name = Column(String(255), nullable=True)        
    transfer_type = Column(String(100), nullable=False)        
    from_department = Column(String(255), nullable=True)
    to_department = Column(String(255), nullable=True)
    from_location = Column(String(255), nullable=True)
    to_location = Column(String(255), nullable=True)
    request_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=True)
    status = Column(String(50), default=TransferStatus.PENDING)  # pending/approved/rejected/in-review
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)
    workflow_stage = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class ExitProcess(Base):
   
    __tablename__ = "exit_processes"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee_name = Column(String(255), nullable=True)
    resignation_date = Column(Date, nullable=True)
    notice_period_start = Column(Date, nullable=True)
    notice_period_end = Column(Date, nullable=True)
    last_working_day = Column(Date, nullable=True)
    exit_type = Column(String(100), nullable=True)          
    exit_reason = Column(String(255), nullable=True)          
    exit_remarks = Column(Text, nullable=True)
    status = Column(String(50), default=ExitStatus.INITIATED) 
    it_clearance = Column(Boolean, default=False)
    admin_clearance = Column(Boolean, default=False)
    finance_clearance = Column(Boolean, default=False)
    hr_clearance = Column(Boolean, default=False)
    relieving_letter_generated = Column(Boolean, default=False)
    relieving_letter_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class ContractRenewal(Base):
  
    __tablename__ = "contract_renewals"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee_name = Column(String(255), nullable=True)
    contract_type = Column(String(100), nullable=True)       
    contract_start = Column(Date, nullable=True)
    contract_end = Column(Date, nullable=False)
    renewal_status = Column(String(50), default="pending")    
    renewed_until = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class LifecycleAnalyticsSnapshot(Base):
    
    __tablename__ = "lifecycle_analytics_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_month = Column(String(7), nullable=False, index=True)  # YYYY-MM
    new_joinings = Column(Integer, default=0)
    voluntary_exits = Column(Integer, default=0)
    involuntary_exits = Column(Integer, default=0)
    transfers = Column(Integer, default=0)
    attrition_rate = Column(Float, default=0.0)
    avg_tenure_years = Column(Float, default=0.0)
    headcount = Column(Integer, default=0)
    generated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
