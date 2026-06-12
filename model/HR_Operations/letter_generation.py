from sqlalchemy import Column, Integer, String, Date, Text, DateTime, Boolean, ForeignKey
from core.database import Base
from datetime import datetime


class LetterTemplate(Base):
    
    __tablename__ = "letter_templates"

    id = Column(Integer, primary_key=True, index=True)
    template_code = Column(String(20), unique=True, nullable=False)   
    name = Column(String(150), nullable=False)
    description = Column(String(300), nullable=True)
    category = Column(String(50), nullable=False)                      
    body_template = Column(Text, nullable=False)                       
    required_approvals = Column(String(255), nullable=True)            
    auto_approve = Column(Boolean, default=False)
    is_ai_optimised = Column(Boolean, default=True)
    times_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LetterRequest(Base):
    
    __tablename__ = "letter_requests"

    id = Column(Integer, primary_key=True, index=True)
    request_code = Column(String(30), unique=True, nullable=False)     
    template_id = Column(Integer, ForeignKey("letter_templates.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    purpose = Column(String(255), nullable=True)                       
    priority = Column(String(20), nullable=False, default="Medium")    
    status = Column(String(30), nullable=False, default="Pending")    
    requested_at = Column(DateTime, default=datetime.utcnow)
    last_action_at = Column(DateTime, nullable=True)
    sla_hours = Column(Integer, nullable=True)                         
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LetterGeneration(Base):
    
    __tablename__ = "letter_generation"

    id = Column(Integer, primary_key=True, index=True)
    letter_code = Column(String(30), unique=True, nullable=False)      
    request_id = Column(Integer, ForeignKey("letter_requests.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("letter_templates.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    letter_type = Column(String(100), nullable=False)
    letter_date = Column(Date, nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    generated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    status = Column(String(50), nullable=False, default="DRAFT")       
    verification_code = Column(String(30), nullable=True)             
    digital_signature = Column(Boolean, default=False)
    is_signed = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    last_downloaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LetterWorkflow(Base):
    
    __tablename__ = "letter_workflows"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("letter_requests.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)                      
    total_steps = Column(Integer, nullable=False)
    approver_role = Column(String(50), nullable=False)                
    approver_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    status = Column(String(30), nullable=False, default="Pending")     
    remarks = Column(Text, nullable=True)
    actioned_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class LetterSystemSettings(Base):
    
    __tablename__ = "letter_system_settings"

    id = Column(Integer, primary_key=True, index=True)
    default_digital_signature = Column(String(50), default="Enable for all letters")
    audit_trail_retention_days = Column(Integer, default=30)
    default_letter_format = Column(String(10), default="PDF")          
    default_workflow_sla_hours = Column(Integer, default=24)
    high_priority_sla_hours = Column(Integer, default=4)
    medium_priority_sla_hours = Column(Integer, default=24)
    low_priority_sla_hours = Column(Integer, default=72)
    email_on_new_request = Column(Boolean, default=True)
    email_on_approval = Column(Boolean, default=True)
    email_on_download = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
