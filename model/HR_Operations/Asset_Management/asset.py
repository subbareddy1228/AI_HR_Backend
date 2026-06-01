from sqlalchemy import Column, Integer, String, Date, Numeric
from core.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)

    # --- Basic Info ---
    asset_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)

    make = Column(String(100), nullable=False)
    model = Column(String(150), nullable=False)

    serial_number = Column(String(120), unique=True, nullable=False, index=True)

    # --- Purchase Details ---
    purchase_date = Column(Date, nullable=False)
    purchase_price = Column(Numeric(12, 2), nullable=False)

    depreciation_rate = Column(Integer, nullable=False)

    # --- Physical Condition ---
    condition = Column(String(50), nullable=False)

    # --- Lifecycle Status ---
    # AVAILABLE | ALLOCATED | UNDER_MAINTENANCE | RETIRED
    status = Column(
        String(50),
        nullable=False,
        server_default="AVAILABLE"
    )

    # --- Location Info ---
    location = Column(String(150), nullable=False)
    department = Column(String(150), nullable=False)

    warranty_until = Column(Date, nullable=True)
