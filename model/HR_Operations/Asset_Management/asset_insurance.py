"""
Asset Insurance Model
Covers: Insurance tab — Policy ID, Asset Details, Provider, Policy Number,
Coverage Amount, Premium, Coverage Type, Validity, Claims, Status, Actions.
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Text, DateTime, func
from sqlalchemy.orm import relationship

from core.database import Base


class AssetInsurance(Base):
    __tablename__ = "asset_insurances"

    id = Column(Integer, primary_key=True, index=True)

    # ── Asset Reference ───────────────────────────────────────────────────────
    asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Policy Details ────────────────────────────────────────────────────────
    insurance_provider = Column(String(150), nullable=False)
    policy_number      = Column(String(150), unique=True, nullable=False, index=True)

    # ── Financial Details ─────────────────────────────────────────────────────
    coverage_amount = Column(Numeric(14, 2), nullable=False)
    premium_amount  = Column(Numeric(14, 2), nullable=False)

    # ── Coverage Type ─────────────────────────────────────────────────────────
    # Comprehensive | Third-Party | Fire & Theft | All-Risk | Extended Warranty
    coverage_type = Column(String(100), nullable=False, server_default="Comprehensive")

    # ── Validity Period ───────────────────────────────────────────────────────
    start_date = Column(Date, nullable=False)
    end_date   = Column(Date, nullable=False)

    # ── Claims ────────────────────────────────────────────────────────────────
    # Number of claims filed against this policy
    claims_count  = Column(Integer, nullable=False, server_default="0")
    claims_amount = Column(Numeric(14, 2), nullable=True, server_default="0")
    claims_notes  = Column(Text, nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    # Active | Expired | Cancelled | Claim Filed
    status = Column(String(50), nullable=False, server_default="Active", index=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    # ── Relationships ─────────────────────────────────────────────────────────
    asset = relationship("Asset", lazy="joined")
