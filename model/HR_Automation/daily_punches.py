from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Date, Time, Text, ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
import enum




class PunchSource(str, enum.Enum):
   
    REMOTE          = "Remote"
    SELFIE          = "Selfie"
    WEB_CHAT        = "Web/Chat"
    QR_SCAN         = "QR Scan"
    BIOMETRIC_FETCH = "Biometric Fetch"
    BIOMETRIC_SYNC  = "Biometric Sync"
    MANUAL          = "Manual"
    EXCEL_IMPORT    = "Excel Import"
    MISSED          = "Missed"
    TIME_RELAX      = "Time Relax"
    TRAVEL          = "Travel"
    API             = "API"


class PunchProcessStatus(str, enum.Enum):
    
    PROCESSED = "Processed"
    PENDING   = "Pending"


class AttendanceMark(str, enum.Enum):
   
    PRESENT   = "P"
    ABSENT    = "A"
    LATE      = "L"
    HALF_DAY  = "H"
    WFH       = "W"
    LEAVE     = "LV"
    HOLIDAY   = "HOL"




class DailyPunch(Base):
    
    __tablename__ = "daily_punches"

    id              = Column(Integer, primary_key=True, index=True)

    
    employee_id     = Column(Integer, ForeignKey("employee_master.id"), nullable=False, index=True)
    employee_code   = Column(String(20), nullable=True)      

    
    punch_date      = Column(Date, nullable=False, index=True)
    punch_time      = Column(Time, nullable=False)
    punch_datetime  = Column(DateTime, nullable=False, default=datetime.utcnow)

  
    punch_type      = Column(String(10), nullable=False, default="IN")  
    source          = Column(SAEnum(PunchSource), nullable=False, default=PunchSource.BIOMETRIC_SYNC)

    
    latitude        = Column(Float, nullable=True)
    longitude       = Column(Float, nullable=True)
    location_tag    = Column(String(200), nullable=True)     

    
    photo_url       = Column(String(500), nullable=True)

    
    process_status  = Column(
        SAEnum(PunchProcessStatus),
        nullable=False,
        default=PunchProcessStatus.PENDING,
    )

   
    business_unit   = Column(String(150), nullable=True)
    location_name   = Column(String(150), nullable=True)
    cost_center     = Column(String(150), nullable=True)
    department      = Column(String(150), nullable=True)

    remarks         = Column(Text, nullable=True)
    is_regularized  = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class DailyPunchSummary(Base):
    
    __tablename__ = "daily_punch_summaries"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer, ForeignKey("employee_master.id"), nullable=False, index=True)
    employee_code   = Column(String(20), nullable=True)         
    designation     = Column(String(200), nullable=True)

    summary_date    = Column(Date, nullable=False, index=True)

    
    first_in_time   = Column(Time, nullable=True)                
    last_out_time   = Column(Time, nullable=True)                
    first_in_source = Column(SAEnum(PunchSource), nullable=True)
    last_out_source = Column(SAEnum(PunchSource), nullable=True)
    first_in_photo  = Column(String(500), nullable=True)
    last_out_photo  = Column(String(500), nullable=True)
    first_in_lat    = Column(Float, nullable=True)
    first_in_lon    = Column(Float, nullable=True)
    last_out_lat    = Column(Float, nullable=True)
    last_out_lon    = Column(Float, nullable=True)

    
    duration_minutes = Column(Integer, default=0)               
    duration_display = Column(String(10), nullable=True)        

    
    attendance_mark  = Column(SAEnum(AttendanceMark), default=AttendanceMark.PRESENT)

   
    business_unit   = Column(String(150), nullable=True)
    location_name   = Column(String(150), nullable=True)
    cost_center     = Column(String(150), nullable=True)
    department      = Column(String(150), nullable=True)

    is_late         = Column(Boolean, default=False)
    has_no_punch    = Column(Boolean, default=False)   
    process_status  = Column(SAEnum(PunchProcessStatus), default=PunchProcessStatus.PENDING)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
