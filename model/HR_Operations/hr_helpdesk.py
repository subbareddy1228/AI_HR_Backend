from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Date
from core.database import Base
from datetime import datetime


class HRHelpdesk(Base):
    __tablename__ = "hr_helpdesk"

   
    id              = Column(Integer, primary_key=True, index=True)

   
    title           = Column(String(255), nullable=False)          
    description     = Column(Text, nullable=False)                 

    
    category        = Column(String(100), nullable=False)

    
    priority        = Column(String(20), nullable=False, server_default="MEDIUM")

    
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    employee_name   = Column(String(150), nullable=True)           

    
    assigned_to     = Column(Integer, ForeignKey("employees.id"), nullable=True)
    assigned_agent  = Column(String(150), nullable=True)           

   
    
    status          = Column(String(50), nullable=False, server_default="OPEN")

    
    resolution      = Column(Text, nullable=True)
    resolved_at     = Column(DateTime, nullable=True)

    due_date        = Column(Date, nullable=True)                  

    
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
