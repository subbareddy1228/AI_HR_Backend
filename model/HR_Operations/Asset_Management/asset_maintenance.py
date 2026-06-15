"""
Asset Maintenance Model
Covers: Maintenance tab — Maintenance ID, Asset Details, Type, Date, Cost,
Performed By, Description, Warranty, Next Due, Status, Actions.
"""

from sqlalchemy import Column, String, ForeignKey, Text, DateTime, Numeric, Date, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class AssetMaintenance(Base):
    __tablename__ = "asset_maintenances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Asset Reference ───────────────────────────────────────────────────────
    asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Maintenance Details ───────────────────────────────────────────────────
    # Preventive | Corrective | Emergency | Inspection
    maintenance_type = Column(String(50), nullable=False)
    maintenance_date = Column(DateTime(timezone=True), nullable=False)
    cost             = Column(Numeric(12, 2), nullable=False)
    performed_by     = Column(String(255), nullable=False)
    description      = Column(Text, nullable=False)

    # ── Warranty on Maintenance Work ─────────────────────────────────────────
    # If the maintenance vendor provides a warranty on their work
    warranty_until = Column(Date, nullable=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    next_due_date = Column(Date, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    # Scheduled | In Progress | Completed | Cancelled
    status = Column(String(50), nullable=False, server_default="Completed")

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    asset = relationship("Asset", lazy="joined")
