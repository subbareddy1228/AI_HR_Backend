

from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class PFStatementStatus(str, Enum):
    PAID    = "paid"
    PENDING = "pending"
    FAILED  = "failed"


class RemittanceStatus(str, Enum):
    PAID    = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"


class ECRStatus(str, Enum):
    SUBMITTED = "submitted"
    PENDING   = "pending"
    FAILED    = "failed"


class VPFStatus(str, Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    PAUSED   = "paused"


class UANStatus(str, Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"
    PENDING  = "pending"


class StatutoryConfigBase(BaseModel):

    config_name:          Optional[str]     = "default"
    pf_wage_limit:        Optional[Decimal] = Decimal("15000.00")
    esi_wage_limit:       Optional[Decimal] = Decimal("21000.00")
    pf_employee_rate:     Optional[float]   = 12.0
    pf_employer_rate:     Optional[float]   = 12.0
    esi_employee_rate:    Optional[float]   = 0.75
    esi_employer_rate:    Optional[float]   = 3.25
    lwf_employee:         Optional[Decimal] = Decimal("25.00")
    lwf_employer:         Optional[Decimal] = Decimal("75.00")
    professional_tax_slab: Optional[str]    = None

    eps_contribution_rate:  Optional[float] = 8.33
    edli_contribution_rate: Optional[float] = 0.5

    pf_ceiling_limit:       Optional[Decimal] = Decimal("15000.00")
    pf_calc_on_ceiling:     Optional[bool]    = True
    enable_basic_pf_calc:   Optional[bool]    = True
    enable_edli_allocation: Optional[bool]    = True
    enable_vpf:             Optional[bool]    = True
    default_vpf_rate:       Optional[float]   = 0.0


class StatutoryConfigCreate(StatutoryConfigBase):
    pass


class StatutoryConfigUpdate(BaseModel):
    # Original
    pf_wage_limit:        Optional[Decimal] = None
    esi_wage_limit:       Optional[Decimal] = None
    pf_employee_rate:     Optional[float]   = None
    pf_employer_rate:     Optional[float]   = None
    esi_employee_rate:    Optional[float]   = None
    esi_employer_rate:    Optional[float]   = None
    lwf_employee:         Optional[Decimal] = None
    lwf_employer:         Optional[Decimal] = None
    professional_tax_slab: Optional[str]   = None
    # New
    eps_contribution_rate:  Optional[float]   = None
    edli_contribution_rate: Optional[float]   = None
    pf_ceiling_limit:       Optional[Decimal] = None
    pf_calc_on_ceiling:     Optional[bool]    = None
    enable_basic_pf_calc:   Optional[bool]    = None
    enable_edli_allocation: Optional[bool]    = None
    enable_vpf:             Optional[bool]    = None
    default_vpf_rate:       Optional[float]   = None


class StatutoryConfigResponse(StatutoryConfigBase):
    id:         int
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PFEligibilityRuleBase(BaseModel):
    minimum_salary:       Optional[Decimal] = None
    maximum_salary:       Optional[Decimal] = None
    allow_permanent:      bool = True
    allow_contract:       bool = True
    allow_intern:         bool = False
    allow_part_time:      bool = False
    probation_period_days: int = 0
    auto_enroll_eligible:  bool = True


class PFEligibilityRuleCreate(PFEligibilityRuleBase):
    config_id: int


class PFEligibilityRuleUpdate(BaseModel):
    minimum_salary:       Optional[Decimal] = None
    maximum_salary:       Optional[Decimal] = None
    allow_permanent:      Optional[bool]    = None
    allow_contract:       Optional[bool]    = None
    allow_intern:         Optional[bool]    = None
    allow_part_time:      Optional[bool]    = None
    probation_period_days: Optional[int]   = None
    auto_enroll_eligible:  Optional[bool]  = None


class PFEligibilityRuleResponse(PFEligibilityRuleBase):
    id:        int
    config_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PFStatementBase(BaseModel):
    employee_id:          int
    month:                int
    year:                 int
    uan_number:           Optional[str]     = None
    employee_contribution: Decimal          = Decimal("0")
    employer_contribution: Decimal          = Decimal("0")
    eps_contribution:      Decimal          = Decimal("0")
    edli_contribution:     Decimal          = Decimal("0")
    total_pf:              Decimal          = Decimal("0")
    vpf_contribution:      Decimal          = Decimal("0")
    status:               PFStatementStatus = PFStatementStatus.PENDING


class PFStatementCreate(PFStatementBase):
    pass


class PFStatementUpdate(BaseModel):
    uan_number:            Optional[str]              = None
    employee_contribution: Optional[Decimal]          = None
    employer_contribution: Optional[Decimal]          = None
    eps_contribution:      Optional[Decimal]          = None
    edli_contribution:     Optional[Decimal]          = None
    total_pf:              Optional[Decimal]          = None
    vpf_contribution:      Optional[Decimal]          = None
    status:               Optional[PFStatementStatus] = None


class PFStatementResponse(PFStatementBase):
    id:         int
    employee_name: Optional[str] = None   
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PFRemittanceSummaryBase(BaseModel):
    month:                int
    year:                 int
    total_contribution:   Decimal = Decimal("0")
    employee_contribution: Decimal = Decimal("0")
    employer_contribution: Decimal = Decimal("0")
    eps_contribution:      Decimal = Decimal("0")
    edli_contribution:     Decimal = Decimal("0")
    challan_number:       Optional[str]  = None
    remittance_date:      Optional[date] = None
    due_date:             Optional[date] = None
    status:               RemittanceStatus = RemittanceStatus.PENDING
    remarks:              Optional[str]  = None


class PFRemittanceSummaryCreate(PFRemittanceSummaryBase):
    pass


class PFRemittanceSummaryUpdate(BaseModel):
    total_contribution:   Optional[Decimal] = None
    employee_contribution: Optional[Decimal] = None
    employer_contribution: Optional[Decimal] = None
    eps_contribution:      Optional[Decimal] = None
    edli_contribution:     Optional[Decimal] = None
    challan_number:       Optional[str]              = None
    remittance_date:      Optional[date]             = None
    due_date:             Optional[date]             = None
    status:               Optional[RemittanceStatus] = None
    remarks:              Optional[str]              = None


class PFRemittanceSummaryResponse(PFRemittanceSummaryBase):
    id:         int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)



class ECRRecordBase(BaseModel):
    month:             int
    year:              int
    total_employees:   int     = 0
    total_wages:       Decimal = Decimal("0")
    epf_contribution:  Decimal = Decimal("0")
    eps_contribution:  Decimal = Decimal("0")
    edli_contribution: Decimal = Decimal("0")
    admin_charges:     Decimal = Decimal("0")
    total_amount_due:  Decimal = Decimal("0")
    status:            ECRStatus = ECRStatus.PENDING
    submitted_date:    Optional[date] = None
    ack_number:        Optional[str]  = None


class ECRRecordCreate(ECRRecordBase):
    pass


class ECRRecordUpdate(BaseModel):
    total_employees:   Optional[int]       = None
    total_wages:       Optional[Decimal]   = None
    epf_contribution:  Optional[Decimal]   = None
    eps_contribution:  Optional[Decimal]   = None
    edli_contribution: Optional[Decimal]   = None
    admin_charges:     Optional[Decimal]   = None
    total_amount_due:  Optional[Decimal]   = None
    status:            Optional[ECRStatus] = None
    submitted_date:    Optional[date]      = None
    ack_number:        Optional[str]       = None


class ECRRecordResponse(ECRRecordBase):
    id:         int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VPFRecordBase(BaseModel):
    employee_id: int
    month:       int
    year:        int
    vpf_rate:    float   = 0.0
    vpf_amount:  Decimal = Decimal("0")
    status:      VPFStatus = VPFStatus.ACTIVE


class VPFRecordCreate(VPFRecordBase):
    pass


class VPFRecordUpdate(BaseModel):
    vpf_rate:   Optional[float]     = None
    vpf_amount: Optional[Decimal]   = None
    status:     Optional[VPFStatus] = None


class VPFRecordResponse(VPFRecordBase):
    id:            int
    employee_name: Optional[str] = None  
    created_at:    Optional[datetime] = None
    updated_at:    Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UANRecordBase(BaseModel):
    employee_id:       int
    uan_number:        Optional[str]  = None
    activation_date:   Optional[date] = None
    linked_pf_account: Optional[str]  = None
    kyc_verified:      bool = False
    status:            UANStatus = UANStatus.PENDING


class UANRecordCreate(UANRecordBase):
    pass


class UANRecordUpdate(BaseModel):
    uan_number:        Optional[str]       = None
    activation_date:   Optional[date]      = None
    linked_pf_account: Optional[str]       = None
    kyc_verified:      Optional[bool]      = None
    status:            Optional[UANStatus] = None


class UANRecordResponse(UANRecordBase):
    id:            int
    employee_name: Optional[str] = None   # joined
    created_at:    Optional[datetime] = None
    updated_at:    Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StatutoryDashboard(BaseModel):

    total_pf_contribution:  Decimal
    total_esi_contribution: Decimal
    total_tds_deduction:    Decimal
    pending_declarations:   int

    current_month: int
    current_year:  int



class StatutoryCompliancePageResponse(BaseModel):
    dashboard:        StatutoryDashboard
    config:           StatutoryConfigResponse
    eligibility_rule: Optional[PFEligibilityRuleResponse] = None
    pf_statements:    List[PFStatementResponse] = []
    remittance_summary: List[PFRemittanceSummaryResponse] = []
    ecr_records:      List[ECRRecordResponse] = []
    vpf_records:      List[VPFRecordResponse] = []
    uan_records:      List[UANRecordResponse] = []