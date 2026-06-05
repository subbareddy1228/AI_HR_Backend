# app/models/productive_entity.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum,func
from app.core.database import Base

# Optional: define allowed entity types
ENTITY_TYPE_ENUM = ("app", "website")
# ProductiveEntity Model
class ProductiveEntity(Base):
    __tablename__ = "productive_entities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)  
    entity_type = Column(Enum(*ENTITY_TYPE_ENUM, name="entity_type_enum"), nullable=False)
    productive = Column(Boolean, default=True, nullable=False)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())
