# app/models/asset_allocation.py

from sqlalchemy import Column, String, ForeignKey, Text, DateTime,Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from core.database import Base


class AssetAllocation(Base):
    __tablename__ = "asset_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    employee_id = Column(String, nullable=False)
    employee_name = Column(String, nullable=False)
    department = Column(String, nullable=False)

    allocation_type = Column(String, nullable=False)
    allocation_reason = Column(Text, nullable=False)

    allocated_at = Column(DateTime, default=datetime.utcnow)
    # ACTIVE | RETURNED  -- tracks this allocation record's own lifecycle
    # (separate from Asset.status, which tracks the asset itself)
    status = Column(String, nullable=False, default="ACTIVE")


    asset = relationship("Asset")