# schema/HR_Operations/transfer.py
# Pydantic schemas for all 5 tabs of Transfer & Movement Management

from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, List


# ─────────────────────────────────────────────────────────────────────────────
#  Shared embedded employee info
# ─────────────────────────────────────────────────────────────────────────────
class EmployeeBasic(BaseModel):
    id:             int
    first_name:     str
    last_name:      Optional[str] = None
    employee_code:  Optional[str] = None
    designation:    Optional[str] = None
    department:     Optional[str] = None
    location:       Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ═════════════════════════════════════════════════════════════════════════════
#  TRANSFER  CRUD
# ═════════════════════════════════════════════════════════════════════════════

class TransferCreate(BaseModel):
    employee_id:        int
    from_department:    str
    to_department:      str
    from_location:      Optional[str] = None
    to_location:        Optional[str] = None
    from_designation:   Optional[str] = None   # for Promotion Transfer
    to_designation:     Optional[str] = None
    # Internal Transfer | Location Transfer | Promotion Transfer | Department Transfer
    transfer_type:      str
    effective_date:     date
    request_date:       Optional[date] = None
    reason:             Optional[str]  = None
    remarks:            Optional[str]  = None


class TransferUpdate(BaseModel):
    from_department:    Optional[str]  = None
    to_department:      Optional[str]  = None
    from_location:      Optional[str]  = None
    to_location:        Optional[str]  = None
    from_designation:   Optional[str]  = None
    to_designation:     Optional[str]  = None
    transfer_type:      Optional[str]  = None
    effective_date:     Optional[date] = None
    # Status: Pending | Approved | Rejected | Completed
    status:             Optional[str]  = None
    approved_by:        Optional[int]  = None
    approved_date:      Optional[date] = None
    reason:             Optional[str]  = None
    remarks:            Optional[str]  = None
    employee_record_updated: Optional[bool] = None


class TransferResponse(BaseModel):
    id:                 int
    transfer_code:      Optional[str]
    employee_id:        int
    employee:           Optional[EmployeeBasic] = None
    from_department:    str
    to_department:      str
    from_location:      Optional[str]
    to_location:        Optional[str]
    from_designation:   Optional[str]
    to_designation:     Optional[str]
    transfer_type:      str
    effective_date:     date
    request_date:       Optional[date]
    status:             str
    approved_by:        Optional[int]
    approved_date:      Optional[date]
    reason:             Optional[str]
    remarks:            Optional[str]
    employee_record_updated: bool
    created_at:         datetime
    updated_at:         datetime

    model_config = ConfigDict(from_attributes=True)


# ═════════════════════════════════════════════════════════════════════════════
#  PENDING APPROVALS  (Tab 2 — same table, status filter)
# ═════════════════════════════════════════════════════════════════════════════

class ApprovalAction(BaseModel):
    """Used for approve / reject quick actions."""
    status:      str           # Approved | Rejected
    approved_by: Optional[int] = None
    remarks:     Optional[str] = None


# ═════════════════════════════════════════════════════════════════════════════
#  ORGANIZATION CHART — Transfer Analytics  (Tab 4)
# ═════════════════════════════════════════════════════════════════════════════

class DepartmentFlow(BaseModel):
    department:    str
    transfers_in:  int
    transfers_out: int
    net_change:    int          # transfers_in - transfers_out

class LocationFlow(BaseModel):
    location:      str
    transfers_in:  int
    transfers_out: int
    net_change:    int

class TopRoute(BaseModel):
    from_department: str
    from_location:   Optional[str]
    to_department:   str
    to_location:     Optional[str]
    transfer_count:  int
    status:          str        # Active / Inactive

class OrgChartAnalytics(BaseModel):
    department_flows: List[DepartmentFlow]
    location_flows:   List[LocationFlow]
    top_routes:       List[TopRoute]


# ═════════════════════════════════════════════════════════════════════════════
#  REPORTS & ANALYTICS  (Tab 5)
# ═════════════════════════════════════════════════════════════════════════════

class TransferTypeDistribution(BaseModel):
    transfer_type:   str
    count:           int
    percentage:      float

class DepartmentStat(BaseModel):
    department:      str
    transfers_in:    int
    transfers_out:   int
    net_change:      int

class StatusDistribution(BaseModel):
    status:          str
    count:           int

class TransferReport(BaseModel):
    total_transfers:      int
    approval_rate_pct:    float
    departments_involved: int
    locations_involved:   int
    type_distribution:    List[TransferTypeDistribution]
    department_stats:     List[DepartmentStat]
    status_distribution:  List[StatusDistribution]
