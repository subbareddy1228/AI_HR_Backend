from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from datetime import date, datetime
from typing import Optional, List
from enum import Enum



class TransferType(str, Enum):
    INTERNAL_TRANSFER   = "INTERNAL_TRANSFER"
    LOCATION_TRANSFER   = "LOCATION_TRANSFER"
    PROMOTION_TRANSFER  = "PROMOTION_TRANSFER"
    DEPARTMENT_TRANSFER = "DEPARTMENT_TRANSFER"


class TransferStatus(str, Enum):
    PENDING   = "PENDING"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    COMPLETED = "COMPLETED"




class TransferCreate(BaseModel):
    employee_id:     int
    from_department: str
    to_department:   str
    from_location:   Optional[str] = None
    to_location:     Optional[str] = None
    transfer_type:   TransferType
    effective_date:  date
    reason:          Optional[str] = None

    @field_validator("transfer_type", mode="before")
    @classmethod
    def normalise_type(cls, v: str) -> str:
        """Accept 'Internal Transfer', 'INTERNAL_TRANSFER', etc."""
        return v.strip().upper().replace(" ", "_") if isinstance(v, str) else v

    @model_validator(mode="after")
    def location_required_for_location_transfer(self):
        if self.transfer_type == TransferType.LOCATION_TRANSFER:
            if not self.from_location or not self.to_location:
                raise ValueError(
                    "from_location and to_location are required for LOCATION_TRANSFER."
                )
        return self




class TransferUpdate(BaseModel):
    from_department: Optional[str]          = None
    to_department:   Optional[str]          = None
    from_location:   Optional[str]          = None
    to_location:     Optional[str]          = None
    transfer_type:   Optional[TransferType] = None
    effective_date:  Optional[date]         = None
    reason:          Optional[str]          = None
    status:          Optional[TransferStatus] = None
    approved_by:     Optional[int]          = None
    remarks:         Optional[str]          = None




class TransferApprovePayload(BaseModel):
    approved_by: int
    remarks:     Optional[str] = None


class TransferRejectPayload(BaseModel):
    reviewed_by: int
    remarks:     Optional[str] = None




class TransferBulkRow(BaseModel):
    employee_id:     int
    from_department: str
    to_department:   str
    from_location:   Optional[str] = None
    to_location:     Optional[str] = None
    transfer_type:   TransferType
    effective_date:  date
    reason:          Optional[str] = None

    @field_validator("transfer_type", mode="before")
    @classmethod
    def normalise_type(cls, v: str) -> str:
        return v.strip().upper().replace(" ", "_") if isinstance(v, str) else v


class TransferBulkUploadPayload(BaseModel):
    records: List[TransferBulkRow]




class TransferResponse(BaseModel):
    id:              int
    transfer_id:     Optional[str]
    employee_id:     int
    from_department: str
    to_department:   str
    from_location:   Optional[str]
    to_location:     Optional[str]
    transfer_type:   str
    effective_date:  date
    reason:          Optional[str]
    status:          str
    approved_by:     Optional[int]
    remarks:         Optional[str]
    created_at:      datetime
    updated_at:      datetime

    model_config = ConfigDict(from_attributes=True)




class TransferStatsSummary(BaseModel):
    
    total:              int
    pending:            int
    approved:           int
    rejected:           int
    completed:          int
    approval_rate_pct:  float
    avg_processing_days: float


class TypeDistribution(BaseModel):
    
    transfer_type: str
    count:         int
    percentage:    float


class DepartmentStats(BaseModel):
   
    department:    str
    transfers_in:  int
    transfers_out: int
    net_change:    int


class StatusDistribution(BaseModel):
    
    status:     str
    count:      int


class AnalyticsResponse(BaseModel):
    summary:               TransferStatsSummary
    type_distribution:     List[TypeDistribution]
    department_stats:      List[DepartmentStats]
    status_distribution:   List[StatusDistribution]
    departments_involved:  int
    locations_involved:    int



class DepartmentFlow(BaseModel):
    from_department: str
    to_department:   str
    count:           int


class LocationFlow(BaseModel):
    from_location: str
    to_location:   str
    count:         int


class TopRoute(BaseModel):
    from_dept:     str
    to_dept:       str
    from_location: Optional[str]
    to_location:   Optional[str]
    count:         int
    status:        str  


class OrgChartAnalyticsResponse(BaseModel):
    department_transfer_flow: List[DepartmentFlow]
    location_transfer_flow:   List[LocationFlow]
    top_transfer_routes:      List[TopRoute]



class BulkUploadResult(BaseModel):
    created_count: int
    error_count:   int
    created_ids:   List[str]
    errors:        List[dict]
