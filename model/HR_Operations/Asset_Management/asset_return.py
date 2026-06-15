"""
Asset Return Model
Covers: Returns tab — Return ID, Asset Details, Employee Details, Return Date,
Reason, Condition, Penalty, Certificate, Status, Actions.
"""

from sqlalchemy import Column, String, ForeignKey, Text, DateTime, Numeric, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from core.database import Base


class AssetReturn(Base):
    __tablename__ = "asset_returns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ── Allocation Reference ──────────────────────────────────────────────────
    allocation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("asset_allocations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Return Details ────────────────────────────────────────────────────────
    return_reason       = Column(String(255), nullable=False)
    # Good | Damaged | Missing Parts | Beyond Repair
    condition_at_return = Column(String(50), nullable=False)
    missing_items       = Column(Text, nullable=True)
    damage_details      = Column(Text, nullable=True)

    # ── Penalty ───────────────────────────────────────────────────────────────
    # Monetary penalty for damage / missing items
    penalty_amount  = Column(Numeric(12, 2), nullable=True, server_default="0")
    penalty_reason  = Column(Text, nullable=True)

    # ── Clearance Certificate ─────────────────────────────────────────────────
    # True once HR issues a clearance certificate to the employee
    certificate_issued    = Column(Boolean, nullable=False, server_default="false")
    certificate_issued_at = Column(DateTime(timezone=True), nullable=True)
    certificate_issued_by = Column(String(255), nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    # Pending | Processed | Disputed
    status = Column(String(50), nullable=False, server_default="Processed")

    # ── Timestamps ────────────────────────────────────────────────────────────
    returned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    allocation = relationship("AssetAllocation", lazy="joined")
