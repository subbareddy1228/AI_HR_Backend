"""
Asset Master Model
Covers: Asset Master tab - all fields shown in UI grid and Add Asset form.
Status lifecycle: AVAILABLE → ALLOCATED → UNDER_MAINTENANCE → RETIRED
"""

from sqlalchemy import Column, Integer, String, Date, Numeric, Text, DateTime, func
from core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)

    # ── Basic Info ────────────────────────────────────────────────────────────
    asset_name      = Column(String(255), nullable=False, index=True)
    category        = Column(String(100), nullable=False, index=True)
    make            = Column(String(100), nullable=False)
    model           = Column(String(150), nullable=False)
    serial_number   = Column(String(120), unique=True, nullable=False, index=True)

    # ── Purchase Details ──────────────────────────────────────────────────────
    purchase_date   = Column(Date, nullable=False)
    purchase_price  = Column(Numeric(14, 2), nullable=False)

    # ── Depreciation ─────────────────────────────────────────────────────────
    # Rate stored as integer percentage, e.g. 15 means 15 %
    depreciation_rate   = Column(Integer, nullable=False)
    # Straight-Line | Declining-Balance | Written-Down-Value
    depreciation_method = Column(String(50), nullable=False, server_default="Straight Line")
    # Useful life in years — drives SL calculation
    useful_life_years   = Column(Integer, nullable=True)

    # ── Physical Condition ────────────────────────────────────────────────────
    # New | Good | Fair | Poor
    condition = Column(String(50), nullable=False)

    # ── Lifecycle Status ──────────────────────────────────────────────────────
    # AVAILABLE | ALLOCATED | UNDER_MAINTENANCE | RETIRED
    status = Column(String(50), nullable=False, server_default="AVAILABLE", index=True)

    # ── Location Info ─────────────────────────────────────────────────────────
    location    = Column(String(150), nullable=False)
    department  = Column(String(150), nullable=False)

    # ── Warranty ──────────────────────────────────────────────────────────────
    warranty_until = Column(Date, nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = Column(Text, nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)
