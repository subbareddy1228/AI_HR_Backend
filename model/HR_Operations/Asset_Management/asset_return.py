# app/models/asset_return.py

from sqlalchemy import Column, String, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from core.database import Base


class AssetReturn(Base):
    __tablename__ = "asset_returns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    allocation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asset_allocations.id"),
        nullable=False
    )

    return_reason = Column(String, nullable=False)
    condition_at_return = Column(String, nullable=False)

    missing_items = Column(Text)
    damage_details = Column(Text)

    returned_at = Column(DateTime, default=datetime.utcnow)

    allocation = relationship("AssetAllocation")
