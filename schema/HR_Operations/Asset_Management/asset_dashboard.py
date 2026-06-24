"""
schema/HR_Operations/Asset_Management/asset_dashboard.py

Pydantic schemas for the dashboard, depreciation calculator, and status
overview -- the aggregation layer on top of the 5 existing sub-modules.
"""

from pydantic import BaseModel
from datetime import date
from typing import List, Optional


class AssetDashboardStats(BaseModel):
    total_asset_value: float
    asset_utilization_percent: float
    upcoming_maintenance: int
    expiring_insurance: int
    total_assets: int
    allocated_assets: int
    available_assets: int
    under_repair: int
    pending_returns: int


class CategoryCount(BaseModel):
    category: str
    count: int


class AssetStatusOverview(BaseModel):
    available: int
    allocated: int
    under_repair: int
    retired: int
    category_distribution: List[CategoryCount]


class DepreciationResult(BaseModel):
    asset_id: int
    purchase_price: float
    depreciation_rate: int
    method: str
    current_value: float
    yearly_depreciation: float
    accumulated_depreciation: float
    net_book_value: float
    next_calculation_date: date


class BulkReportRequest(BaseModel):
    from_date: date
    to_date: date
    report_types: Optional[List[str]] = None  # None = all 6