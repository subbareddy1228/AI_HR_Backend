from sqlalchemy import Column, Integer, String, Float, Date, Enum
from core.database import Base
import enum


class StatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_Name = Column(String, nullable=False)
    total_deal_value = Column(Float, nullable=False)
    deals = Column(Integer, nullable=False)
    stages = Column(String, nullable=False)
    created_date = Column(Date, nullable=False)

    status = Column(
        Enum(
            StatusEnum,
            name="pipeline_status_enum",      
            values_callable=lambda x: [e.value for e in x]  
        ),
        nullable=False,
        default=StatusEnum.active
    )
