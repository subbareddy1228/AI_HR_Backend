
from __future__ import annotations
from pydantic import BaseModel, EmailStr, field_validator, model_validator, ConfigDict
from typing import Optional
from decimal import Decimal
from datetime import date




class AddressSchema(BaseModel):
    line1:   Optional[str] = None
    line2:   Optional[str] = None
    city:    Optional[str] = None
    state:   Optional[str] = None
    pincode: Optional[str] = None
    country: Optional[str] = None


class EmergencyContactSchema(BaseModel):
    id:       Optional[int] = None
    name:     str
    relation: Optional[str] = None
    phone:    Optional[str] = None
    priority: Optional[str] = "Primary"   


class FamilyMemberSchema(BaseModel):
    id:          Optional[int] = None
    name:        str
    relation:    Optional[str] = None
    dateOfBirth: Optional[str] = None     
    dob:         Optional[str] = None     
    contactNo:   Optional[str] = None


class NomineeSchema(BaseModel):
    id:                 Optional[int] = None
    name:               str
    relation:           Optional[str] = None
    phone:              Optional[str] = None
    contactNo:          Optional[str] = None
    percentage:         Optional[int] = 0
    isNomineeAccepted:  Optional[bool] = False




class PanSchema(BaseModel):
    number:   Optional[str] = None
    verified: Optional[bool] = False


class AadhaarSchema(BaseModel):
    number:   Optional[str] = None
    verified: Optional[bool] = False


class PassportSchema(BaseModel):
    number:     Optional[str] = None
    expiryDate: Optional[str] = None
    verified:   Optional[bool] = False


class VoterIdSchema(BaseModel):
    number:   Optional[str] = None
    verified: Optional[bool] = False


class IdentificationSchema(BaseModel):
    pan:      Optional[PanSchema]     = None
    aadhaar:  Optional[AadhaarSchema] = None
    passport: Optional[PassportSchema] = None
    voterId:  Optional[VoterIdSchema]  = None




class PersonalInfoSchema(BaseModel):
    dateOfBirth:       Optional[str]   = None
    gender:            Optional[str]   = None
    bloodGroup:        Optional[str]   = None
    maritalStatus:     Optional[str]   = None
    nationality:       Optional[str]   = None
    languages:         Optional[list[str]] = None
    profilePhoto:      Optional[str]   = None   
    personalEmail:     Optional[str]   = None
    phonePrimary:      Optional[str]   = None
    phoneSecondary:    Optional[str]   = None
    phoneEmergency:    Optional[str]   = None
    currentAddress:    Optional[AddressSchema]  = None
    permanentAddress:  Optional[AddressSchema]  = None
    emergencyContacts: Optional[list[EmergencyContactSchema]] = None
    familyMembers:     Optional[list[FamilyMemberSchema]]     = None
    nominees:          Optional[list[NomineeSchema]]          = None
    identification:    Optional[IdentificationSchema]         = None

    
    panNumber:     Optional[str] = None
    aadhaarNumber: Optional[str] = None




class ReportingManagerSchema(BaseModel):
    direct:     Optional[str] = None
    functional: Optional[str] = None


class EmploymentInfoSchema(BaseModel):
    employeeId:         Optional[str]  = None
    dateOfJoining:      Optional[str]  = None
    confirmationDate:   Optional[str]  = None
    probationPeriod:    Optional[int]  = 6       
    employmentType:     Optional[str]  = "Permanent"
    employmentStatus:   Optional[str]  = "Active"
    department:         Optional[str]  = None
    subDepartment:      Optional[str]  = None
    costCenter:         Optional[str]  = None
    designation:        Optional[str]  = None
    grade:              Optional[str]  = None
    level:              Optional[str]  = None    
    location:           Optional[str]  = None
    locationId:         Optional[int]  = None    # branch/office id (CompanyLocation)
    branchName:         Optional[str]  = None    # resolved branch name, read-only on responses
    workplaceType:      Optional[str]  = "Office"  
    workEmail:          Optional[str]  = None
    extensionNumber:    Optional[str]  = None
    deskLocation:       Optional[str]  = None
    employeeCategory:   Optional[str]  = "Staff"
    noticePeriod:       Optional[int]  = 30     
    reportingManager:   Optional[ReportingManagerSchema] = None
    hrBusinessPartner:  Optional[str]  = None




class JobHistoryItemSchema(BaseModel):
    id:              Optional[int]     = None
    date:            Optional[str]     = None    
    endDate:         Optional[str]     = None    
    type:            Optional[str]     = None   
    organisation:    Optional[str]     = None
    department:      Optional[str]     = None
    designation:     Optional[str]     = None
    location:        Optional[str]     = None
    manager:         Optional[str]     = None
    salaryChange:    Optional[Decimal] = None
    notes:           Optional[str]     = None
    achievements:    Optional[str]     = None
    reasonForLeaving: Optional[str]   = None




class CTCBreakdownSchema(BaseModel):
    basic:               Optional[Decimal] = Decimal("0")
    hra:                 Optional[Decimal] = Decimal("0")
    specialAllowance:    Optional[Decimal] = Decimal("0")
    transportAllowance:  Optional[Decimal] = Decimal("0")
    medicalAllowance:    Optional[Decimal] = Decimal("0")
    otherAllowances:     Optional[Decimal] = Decimal("0")
    providentFund:       Optional[Decimal] = Decimal("0")
    gratuity:            Optional[Decimal] = Decimal("0")
    otherDeductions:     Optional[Decimal] = Decimal("0")


class BankAccountSchema(BaseModel):
    accountNumber: Optional[str] = None
    ifscCode:      Optional[str] = None
    bankName:      Optional[str] = None
    branch:        Optional[str] = None
    accountType:   Optional[str] = "Savings"   


class BankAccountsSchema(BaseModel):
    primary:   Optional[BankAccountSchema] = None
    secondary: Optional[BankAccountSchema] = None


class TaxDeclarationSchema(BaseModel):
    regime:   Optional[str]  = "New"   
    declared: Optional[bool] = False


class VariablePaySchema(BaseModel):
    eligible:   Optional[bool]    = False
    percentage: Optional[Decimal] = Decimal("0")


class BonusEligibilitySchema(BaseModel):
    eligible: Optional[bool]    = False
    amount:   Optional[Decimal] = Decimal("0")


class SalaryRevisionItemSchema(BaseModel):
    id:                 Optional[int]     = None
    effectiveDate:      Optional[str]     = None
    previousCTC:        Optional[Decimal] = Decimal("0")
    newCTC:             Optional[Decimal] = Decimal("0")
    percentageIncrease: Optional[Decimal] = Decimal("0")
    approvedBy:         Optional[str]     = None
    status:             Optional[str]     = "Pending"


class SalaryInfoSchema(BaseModel):
    currentCTC:            Optional[Decimal]             = Decimal("0")
    salaryStructure:       Optional[str]                 = None
    ctcBreakdown:          Optional[CTCBreakdownSchema]  = None
    paymentMode:           Optional[str]                 = "Bank Transfer"
    pfAccountNumber:       Optional[str]                 = None
    uan:                   Optional[str]                 = None
    esiNumber:             Optional[str]                 = None
    esiMedicalNominee:     Optional[str]                 = None
    taxDeclaration:        Optional[TaxDeclarationSchema]    = None
    variablePay:           Optional[VariablePaySchema]       = None
    bonusEligibility:      Optional[BonusEligibilitySchema]  = None
    bankAccounts:          Optional[BankAccountsSchema]      = None
    salaryRevisionHistory: Optional[list[SalaryRevisionItemSchema]] = None




class StatutoryPanSchema(BaseModel):
    number:       Optional[str]  = None
    verified:     Optional[bool] = False
    verifiedDate: Optional[str]  = None


class StatutoryAadhaarSchema(BaseModel):
    number:       Optional[str]  = None
    verified:     Optional[bool] = False
    verifiedDate: Optional[str]  = None


class PFMembershipSchema(BaseModel):
    enrolled:       Optional[bool] = False
    accountNumber:  Optional[str]  = None
    uan:            Optional[str]  = None
    enrollmentDate: Optional[str]  = None
    accountType:    Optional[str]  = None   


class ESIRegistrationSchema(BaseModel):
    enrolled:       Optional[bool] = False
    number:         Optional[str]  = None
    enrollmentDate: Optional[str]  = None


class ProfessionalTaxSchema(BaseModel):
    applicable: Optional[bool] = False
    state:      Optional[str]  = None
    ptNumber:   Optional[str]  = None


class LabourWelfareFundSchema(BaseModel):
    enrolled:       Optional[bool] = False
    enrollmentDate: Optional[str]  = None


class GratuitySchema(BaseModel):
    eligible:        Optional[bool] = False
    eligibilityDate: Optional[str]  = None


class BonusActSchema(BaseModel):
    applicable: Optional[bool] = False


class ShopsEstablishmentSchema(BaseModel):
    registered:          Optional[bool] = False
    registrationNumber:  Optional[str]  = None
    registrationDate:    Optional[str]  = None


class StatutoryInfoSchema(BaseModel):
    pan:                   Optional[StatutoryPanSchema]        = None
    aadhaar:               Optional[StatutoryAadhaarSchema]    = None
    pfMembership:          Optional[PFMembershipSchema]        = None
    esiRegistration:       Optional[ESIRegistrationSchema]     = None
    professionalTax:       Optional[ProfessionalTaxSchema]     = None
    labourWelfareFund:     Optional[LabourWelfareFundSchema]   = None
    gratuity:              Optional[GratuitySchema]            = None
    bonusAct:              Optional[BonusActSchema]            = None
    shopsAndEstablishment: Optional[ShopsEstablishmentSchema]  = None



class EmployeeCreateRequest(BaseModel):
    

    
    name:           Optional[str]     = None
    email:          Optional[str]     = None
    phone:          Optional[str]     = None
    department:     Optional[str]     = None
    designation:    Optional[str]     = None
    location:       Optional[str]     = None
    employmentType: Optional[str]     = None
    status:         Optional[str]     = "Active"
    joinDate:       Optional[str]     = None
    salary:         Optional[Decimal] = None
    employeeId:     Optional[str]     = None

    # 5 tabs
    personalInfo:   Optional[PersonalInfoSchema]   = None
    employmentInfo: Optional[EmploymentInfoSchema] = None
    jobHistory:     Optional[list[JobHistoryItemSchema]] = None
    salaryInfo:     Optional[SalaryInfoSchema]     = None
    statutoryInfo:  Optional[StatutoryInfoSchema]  = None

    @model_validator(mode="after")
    def at_least_name_or_email(self):
        has_name  = bool(self.name)
        has_email = bool(self.email)
        has_work_email = bool(
            self.employmentInfo and self.employmentInfo.workEmail
        )
        if not has_name and not has_email and not has_work_email:
            raise ValueError("At least one of 'name', 'email', or employmentInfo.workEmail is required.")
        return self


class EmployeeUpdateRequest(BaseModel):
    

    name:           Optional[str]     = None
    email:          Optional[str]     = None
    phone:          Optional[str]     = None
    department:     Optional[str]     = None
    designation:    Optional[str]     = None
    location:       Optional[str]     = None
    employmentType: Optional[str]     = None
    status:         Optional[str]     = None
    joinDate:       Optional[str]     = None
    salary:         Optional[Decimal] = None

    personalInfo:   Optional[PersonalInfoSchema]   = None
    employmentInfo: Optional[EmploymentInfoSchema] = None
    jobHistory:     Optional[list[JobHistoryItemSchema]] = None
    salaryInfo:     Optional[SalaryInfoSchema]     = None
    statutoryInfo:  Optional[StatutoryInfoSchema]  = None




class EmployeeListItem(BaseModel):
    
    id:             int
    employeeId:     str
    name:           str
    email:          Optional[str]
    phone:          Optional[str]
    department:     Optional[str]
    designation:    Optional[str]
    location:       Optional[str]
    locationId:     Optional[int] = None
    branchName:     Optional[str] = None
    employmentType: Optional[str]
    status:         Optional[str]
    joinDate:       Optional[str]
    salary:         Optional[float]

    model_config = ConfigDict(from_attributes=True)


class EmployeeFullResponse(EmployeeListItem):
    
    personalInfo:   Optional[dict] = None
    employmentInfo: Optional[dict] = None
    jobHistory:     Optional[list] = None
    salaryInfo:     Optional[dict] = None
    statutoryInfo:  Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeStatsResponse(BaseModel):
    
    totalEmployees:  int
    activeEmployees: int
    departments:     int
    avgSalary:       Optional[float]

    model_config = ConfigDict(from_attributes=True)


class DeleteResponse(BaseModel):
    message: str


class ActivationResponse(BaseModel):
    id:        int
    is_active: bool
    message:   str