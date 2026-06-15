"""
Asset Allocation Model
Covers: Allocations tab fields — Allocation ID, Asset Details, Employee Details,
Allocation Date, Type, Approved By, Insurance, Status, Actions.
"""

from sqlalchemy import Column, String, ForeignKey, Text, DateTime, Integer, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class AssetAllocation(Base):
    __tablename__ = "asset_allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Asset Reference ───────────────────────────────────────────────────────
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True)

    # ── Employee Info ─────────────────────────────────────────────────────────
    employee_id     = Column(String(50), nullable=False, index=True)
    employee_name   = Column(String(255), nullable=False)
    department      = Column(String(150), nullable=False)

    # ── Allocation Details ────────────────────────────────────────────────────
    # Permanent | Temporary | Project-Based
    allocation_type   = Column(String(50), nullable=False)
    allocation_reason = Column(Text, nullable=False)

    # ── Approval ──────────────────────────────────────────────────────────────
    approved_by   = Column(String(255), nullable=True)
    approved_at   = Column(DateTime(timezone=True), nullable=True)

    # ── Insurance Linkage ─────────────────────────────────────────────────────
    # Indicates whether an active insurance policy covers this allocation
    insurance_covered = Column(Boolean, nullable=False, server_default="false")

    # ── Status ────────────────────────────────────────────────────────────────
    # Active | Returned | Transferred
    status = Column(String(50), nullable=False, server_default="Active", index=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    allocated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(),
                          onupdate=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    asset = relationship("Asset", lazy="joined")
