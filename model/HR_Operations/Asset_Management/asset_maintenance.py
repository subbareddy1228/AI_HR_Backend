# app/models/asset_maintenance.py

from sqlalchemy import Column, String, ForeignKey, Text, DateTime, Float,Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from core.database import Base


class AssetMaintenance(Base):
    __tablename__ = "asset_maintenances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    maintenance_type = Column(String, nullable=False)
    maintenance_date = Column(DateTime, nullable=False)

    cost = Column(Float, nullable=False)
    performed_by = Column(String, nullable=False)

    description = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    asset = relationship("Asset")
