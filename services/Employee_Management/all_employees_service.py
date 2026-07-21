from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException

from model.onboarding.employee import Employee
from model.Employee_Management.employee_master import EmployeeMaster
from model.Employee_Management.employee_profile import (
    EmployeePersonalInfo,
    EmployeeEmergencyContact,
    EmployeeFamilyMember,
    EmployeeNominee,
    EmployeeIdentification,
    EmployeeEmploymentInfo,
    EmployeeJobHistory,
    EmployeeSalaryInfo,
    EmployeeBankAccount,
    EmployeeSalaryRevision,
    EmployeeStatutoryInfo,
)


def _parse_date(val) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val)[:10])
    except Exception:
        return None


def _to_float(val) -> Optional[float]:
    try:
        return float(val) if val is not None else None
    except Exception:
        return None


def _auto_employee_code(db: Session) -> str:
    count = db.execute(select(func.count(Employee.id))).scalar_one() or 0
    return f"EMP{str(count + 1).zfill(4)}"

def _build_response(emp: Employee, db: Session) -> dict:
    personal = db.execute(
        select(EmployeePersonalInfo).where(EmployeePersonalInfo.employee_id == emp.id)
    ).scalar_one_or_none()

    identification = db.execute(
        select(EmployeeIdentification).where(EmployeeIdentification.employee_id == emp.id)
    ).scalar_one_or_none()

    emerg_contacts = db.execute(
        select(EmployeeEmergencyContact).where(EmployeeEmergencyContact.employee_id == emp.id)
    ).scalars().all()

    family_members = db.execute(
        select(EmployeeFamilyMember).where(EmployeeFamilyMember.employee_id == emp.id)
    ).scalars().all()

    nominees = db.execute(
        select(EmployeeNominee).where(EmployeeNominee.employee_id == emp.id)
    ).scalars().all()

    emp_info = db.execute(
        select(EmployeeEmploymentInfo).where(EmployeeEmploymentInfo.employee_id == emp.id)
    ).scalar_one_or_none()

    job_history = db.execute(
        select(EmployeeJobHistory).where(EmployeeJobHistory.employee_id == emp.id)
        .order_by(EmployeeJobHistory.start_date)
    ).scalars().all()

    salary_info = db.execute(
        select(EmployeeSalaryInfo).where(EmployeeSalaryInfo.employee_id == emp.id)
    ).scalar_one_or_none()

    bank_accounts = db.execute(
        select(EmployeeBankAccount).where(EmployeeBankAccount.employee_id == emp.id)
    ).scalars().all()

    salary_revisions = db.execute(
        select(EmployeeSalaryRevision).where(EmployeeSalaryRevision.employee_id == emp.id)
        .order_by(EmployeeSalaryRevision.effective_date)
    ).scalars().all()

    statutory = db.execute(
        select(EmployeeStatutoryInfo).where(EmployeeStatutoryInfo.employee_id == emp.id)
    ).scalar_one_or_none()

    master = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == emp.id)
    ).scalar_one_or_none()


    bank_dict = {"primary": {}, "secondary": None}
    for ba in bank_accounts:
        entry = {
            "accountNumber": ba.account_number or "",
            "ifscCode": ba.ifsc_code or "",
            "bankName": ba.bank_name or "",
            "branch": ba.branch or "",
            "accountType": ba.account_type or "Savings",
        }
        if ba.account_type_label == "secondary":
            bank_dict["secondary"] = entry
        else:
            bank_dict["primary"] = entry

    full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()
    emp_code = (emp_info.employee_code if emp_info and emp_info.employee_code else emp.employee_code or "")
    work_email = (emp_info.work_email if emp_info else emp.official_email or "")
    designation = (emp_info.designation if emp_info else emp.designation or "")
    department = (emp_info.department if emp_info else emp.department or "")
    location = (emp_info.location if emp_info else emp.location or "")
    emp_type = (emp_info.employment_type if emp_info else (master.employment_type if master else "Permanent"))
    emp_status = (emp_info.employment_status if emp_info else (master.employment_status if master else "Active"))
    join_date = str(emp_info.date_of_joining) if (emp_info and emp_info.date_of_joining) else (str(emp.joining_date) if emp.joining_date else "")
    salary = _to_float(salary_info.current_ctc) if salary_info else (_to_float(master.salary) if master else 0)

    return {
        "id": emp.id,
        "employeeId": emp_code,
        "name": full_name,
        "email": work_email,
        "phone": (personal.phone_primary if personal else emp.mobile_number or ""),
        "department": department,
        "designation": designation,
        "location": location,
        "employmentType": emp_type,
        "status": emp_status,
        "joinDate": join_date,
        "salary": salary,

       
        "personalInfo": {
            "dateOfBirth": str(personal.date_of_birth) if (personal and personal.date_of_birth) else "",
            "gender": (personal.gender if personal else ""),
            "bloodGroup": (personal.blood_group if personal else ""),
            "maritalStatus": (personal.marital_status if personal else ""),
            "nationality": (personal.nationality if personal else ""),
            "languages": (personal.languages if personal and personal.languages else []),
            "profilePhoto": (personal.profile_photo if personal else ""),
            "personalEmail": (personal.personal_email if personal else ""),
            "phonePrimary": (personal.phone_primary if personal else emp.mobile_number or ""),
            "phoneSecondary": (personal.phone_secondary if personal else ""),
            "phoneEmergency": (personal.phone_emergency if personal else ""),
            "currentAddress": {
                "line1":   (personal.curr_line1   if personal else ""),
                "line2":   (personal.curr_line2   if personal else ""),
                "city":    (personal.curr_city    if personal else ""),
                "state":   (personal.curr_state   if personal else ""),
                "pincode": (personal.curr_pincode if personal else ""),
                "country": (personal.curr_country if personal else ""),
            },
            "permanentAddress": {
                "line1":   (personal.perm_line1   if personal else ""),
                "line2":   (personal.perm_line2   if personal else ""),
                "city":    (personal.perm_city    if personal else ""),
                "state":   (personal.perm_state   if personal else ""),
                "pincode": (personal.perm_pincode if personal else ""),
                "country": (personal.perm_country if personal else ""),
            },
            "emergencyContacts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "relation": c.relation or "",
                    "phone": c.phone or "",
                    "priority": c.priority or "Primary",
                }
                for c in emerg_contacts
            ],
            "familyMembers": [
                {
                    "id": m.id,
                    "name": m.name,
                    "relation": m.relation or "",
                    "dob": str(m.date_of_birth) if m.date_of_birth else "",
                    "dateOfBirth": str(m.date_of_birth) if m.date_of_birth else "",
                    "contactNo": m.contact_no or "",
                }
                for m in family_members
            ],
            "nominees": [
                {
                    "id": n.id,
                    "name": n.name,
                    "relation": n.relation or "",
                    "phone": n.phone or "",
                    "contactNo": n.phone or "",
                    "percentage": n.percentage or 0,
                    "isNomineeAccepted": n.is_nominee_accepted or False,
                }
                for n in nominees
            ],
            "identification": {
                "pan": {
                    "number": (identification.pan_number if identification else ""),
                    "verified": (identification.pan_verified if identification else False),
                },
                "aadhaar": {
                    "number": (identification.aadhaar_number if identification else ""),
                    "verified": (identification.aadhaar_verified if identification else False),
                },
                "passport": {
                    "number": (identification.passport_number if identification else ""),
                    "expiryDate": str(identification.passport_expiry_date) if (identification and identification.passport_expiry_date) else "",
                    "verified": (identification.passport_verified if identification else False),
                },
                "voterId": {
                    "number": (identification.voter_id_number if identification else ""),
                    "verified": (identification.voter_id_verified if identification else False),
                },
            },
        },

       
        "employmentInfo": {
            "employeeId": emp_code,
            "dateOfJoining": join_date,
            "confirmationDate": str(emp_info.confirmation_date) if (emp_info and emp_info.confirmation_date) else "",
            "probationPeriod": (emp_info.probation_period if emp_info else 6),
            "employmentType": emp_type,
            "employmentStatus": emp_status,
            "department": department,
            "subDepartment": (emp_info.sub_department if emp_info else ""),
            "costCenter": (emp_info.cost_center if emp_info else emp.cost_center or ""),
            "designation": designation,
            "grade": (emp_info.grade if emp_info else emp.grade or ""),
            "level": (emp_info.level if emp_info else ""),
            "location": location,
            "workplaceType": (emp_info.workplace_type if emp_info else "Office"),
            "workEmail": work_email,
            "extensionNumber": (emp_info.extension_number if emp_info else ""),
            "deskLocation": (emp_info.desk_location if emp_info else ""),
            "employeeCategory": (emp_info.employee_category if emp_info else "Staff"),
            "noticePeriod": (emp_info.notice_period if emp_info else 30),
            "reportingManager": {
                "direct": (emp_info.direct_manager if emp_info else ""),
                "functional": (emp_info.functional_manager if emp_info else ""),
            },
            "hrBusinessPartner": (emp_info.hr_business_partner if emp_info else ""),
        },

       
        "jobHistory": [
            {
                "id": jh.id,
                "date": str(jh.start_date) if jh.start_date else "",
                "endDate": jh.end_date or "",
                "type": jh.history_type or "",
                "organisation": jh.organisation or "",
                "department": jh.department or "",
                "designation": jh.designation or "",
                "location": jh.location or "",
                "manager": jh.manager or "",
                "salaryChange": _to_float(jh.salary_change),
                "notes": jh.notes or "",
                "achievements": jh.achievements or "",
                "reasonForLeaving": jh.reason_for_leaving or "",
            }
            for jh in job_history
        ],

       
        "salaryInfo": {
            "currentCTC": _to_float(salary_info.current_ctc) if salary_info else 0,
            "salaryStructure": (salary_info.salary_structure if salary_info else ""),
            "ctcBreakdown": {
                "basic": _to_float(salary_info.basic) if salary_info else 0,
                "hra": _to_float(salary_info.hra) if salary_info else 0,
                "specialAllowance": _to_float(salary_info.special_allowance) if salary_info else 0,
                "transportAllowance": _to_float(salary_info.transport_allowance) if salary_info else 0,
                "medicalAllowance": _to_float(salary_info.medical_allowance) if salary_info else 0,
                "otherAllowances": _to_float(salary_info.other_allowances) if salary_info else 0,
                "providentFund": _to_float(salary_info.provident_fund) if salary_info else 0,
                "gratuity": _to_float(salary_info.gratuity) if salary_info else 0,
                "otherDeductions": _to_float(salary_info.other_deductions) if salary_info else 0,
            },
            "paymentMode": (salary_info.payment_mode if salary_info else "Bank Transfer"),
            "pfAccountNumber": (salary_info.pf_account_number if salary_info else ""),
            "uan": (salary_info.uan if salary_info else ""),
            "esiNumber": (salary_info.esi_number if salary_info else ""),
            "esiMedicalNominee": (salary_info.esi_medical_nominee if salary_info else ""),
            "taxDeclaration": {
                "regime": (salary_info.tax_regime if salary_info else "New"),
                "declared": (salary_info.tax_declared if salary_info else False),
            },
            "variablePay": {
                "eligible": (salary_info.variable_pay_eligible if salary_info else False),
                "percentage": _to_float(salary_info.variable_pay_pct) if salary_info else 0,
            },
            "bonusEligibility": {
                "eligible": (salary_info.bonus_eligible if salary_info else False),
                "amount": _to_float(salary_info.bonus_amount) if salary_info else 0,
            },
            "bankAccounts": bank_dict,
            "salaryRevisionHistory": [
                {
                    "id": sr.id,
                    "effectiveDate": str(sr.effective_date) if sr.effective_date else "",
                    "previousCTC": _to_float(sr.previous_ctc),
                    "newCTC": _to_float(sr.new_ctc),
                    "percentageIncrease": _to_float(sr.percentage_increase),
                    "approvedBy": sr.approved_by or "",
                    "status": sr.status or "Pending",
                }
                for sr in salary_revisions
            ],
        },

       
        "statutoryInfo": {
            "pan": {
                "number": (statutory.pan_number if statutory else ""),
                "verified": (statutory.pan_verified if statutory else False),
                "verifiedDate": str(statutory.pan_verified_date) if (statutory and statutory.pan_verified_date) else "",
            },
            "aadhaar": {
                "number": (statutory.aadhaar_number if statutory else ""),
                "verified": (statutory.aadhaar_verified if statutory else False),
                "verifiedDate": str(statutory.aadhaar_verified_date) if (statutory and statutory.aadhaar_verified_date) else "",
            },
            "pfMembership": {
                "enrolled": (statutory.pf_enrolled if statutory else False),
                "accountNumber": (statutory.pf_account_number if statutory else ""),
                "uan": (statutory.pf_uan if statutory else ""),
                "enrollmentDate": str(statutory.pf_enrollment_date) if (statutory and statutory.pf_enrollment_date) else "",
                "accountType": (statutory.pf_account_type if statutory else ""),
            },
            "esiRegistration": {
                "enrolled": (statutory.esi_enrolled if statutory else False),
                "number": (statutory.esi_number if statutory else ""),
                "enrollmentDate": str(statutory.esi_enrollment_date) if (statutory and statutory.esi_enrollment_date) else "",
            },
            "professionalTax": {
                "applicable": (statutory.pt_applicable if statutory else False),
                "state": (statutory.pt_state if statutory else ""),
                "ptNumber": (statutory.pt_number if statutory else ""),
            },
            "labourWelfareFund": {
                "enrolled": (statutory.lwf_enrolled if statutory else False),
                "enrollmentDate": str(statutory.lwf_enrollment_date) if (statutory and statutory.lwf_enrollment_date) else "",
            },
            "gratuity": {
                "eligible": (statutory.gratuity_eligible if statutory else False),
                "eligibilityDate": str(statutory.gratuity_eligibility_date) if (statutory and statutory.gratuity_eligibility_date) else "",
            },
            "bonusAct": {
                "applicable": (statutory.bonus_act_applicable if statutory else False),
            },
            "shopsAndEstablishment": {
                "registered": (statutory.shops_registered if statutory else False),
                "registrationNumber": (statutory.shops_registration_number if statutory else ""),
                "registrationDate": str(statutory.shops_registration_date) if (statutory and statutory.shops_registration_date) else "",
            },
        },
    }


def list_all_employees(
    db: Session,
    tenant_id: Optional[int],
    is_active: Optional[bool] = None,
    department: Optional[str] = None,
    search: Optional[str] = None,
) -> list:
    stmt = select(Employee)
    if tenant_id is not None:  
        stmt = stmt.where(Employee.tenant_id == tenant_id)
    if is_active is not None:
        stmt = stmt.where(Employee.is_active == is_active)
    if department and department not in ("All Departments", "All", ""):
        stmt = stmt.where(Employee.department == department)
    if search:
        s = f"%{search.strip().lower()}%"
        from sqlalchemy import or_, func as sf
        stmt = stmt.where(
            or_(
                sf.lower(Employee.first_name).like(s),
                sf.lower(Employee.last_name).like(s),
                sf.lower(Employee.official_email).like(s),
                sf.lower(Employee.employee_code).like(s),
            )
        )
    employees = db.execute(stmt.order_by(Employee.first_name)).scalars().all()
    return [_build_response(emp, db) for emp in employees]


def get_employee(db: Session, employee_id: int, tenant_id: Optional[int]) -> dict:
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
   
    if tenant_id is not None and emp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _build_response(emp, db)


def create_employee(db: Session, payload: dict, tenant_id: int) -> dict:
    personal_data = payload.get("personalInfo", {})
    emp_info_data = payload.get("employmentInfo", {})
    salary_data   = payload.get("salaryInfo", {})
    statutory_data = payload.get("statutoryInfo", {})
    job_history_data = payload.get("jobHistory", [])

    identification = personal_data.get("identification", {})
    pan_data    = identification.get("pan", {})
    aadhaar_data = identification.get("aadhaar", {})

   
    name_parts = (payload.get("name", "") or "").strip().split(" ", 1)
    first_name = name_parts[0]
    last_name  = name_parts[1] if len(name_parts) > 1 else None

    mobile = (
        personal_data.get("phonePrimary")
        or payload.get("phone")
        or emp_info_data.get("workEmail", "")[:15]  # fallback
    )

    emp_code = (
        emp_info_data.get("employeeId")
        or payload.get("employeeId")
        or _auto_employee_code(db)
    )

  
    existing_code = db.execute(
        select(Employee).where(Employee.employee_code == emp_code)
    ).scalar_one_or_none()
    if existing_code:
        emp_code = _auto_employee_code(db)

    if mobile:
        existing_mobile = db.execute(
            select(Employee).where(Employee.mobile_number == mobile)
        ).scalar_one_or_none()
        if existing_mobile:
            raise HTTPException(
                status_code=409,
                detail=f"An employee with mobile number {mobile} already exists."
            )

    from model.onboarding.employee import GenderEnum
    gender_val = personal_data.get("gender", "").lower()
    gender_map = {"male": GenderEnum.male, "female": GenderEnum.female, "transgender": GenderEnum.transgender}
    gender_enum = gender_map.get(gender_val, GenderEnum.male)

    join_date = _parse_date(emp_info_data.get("dateOfJoining") or payload.get("joinDate"))
    if not join_date:
        join_date = date.today()

    emp = Employee(
        first_name=first_name,
        last_name=last_name,
        gender=gender_enum,
        employee_code=emp_code,
        mobile_number=mobile or "0000000000",
        official_email=emp_info_data.get("workEmail") or payload.get("email"),
        joining_date=join_date,
        confirmation_date=_parse_date(emp_info_data.get("confirmationDate")),
        date_of_birth=_parse_date(personal_data.get("dateOfBirth")),
        department=emp_info_data.get("department") or payload.get("department"),
        designation=emp_info_data.get("designation") or payload.get("designation"),
        location=emp_info_data.get("location") or payload.get("location"),
        grade=emp_info_data.get("grade"),
        cost_center=emp_info_data.get("costCenter"),
        business_unit=emp_info_data.get("employeeCategory"),
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(emp)
    db.flush()  

  
    curr_addr = personal_data.get("currentAddress", {})
    perm_addr = personal_data.get("permanentAddress", {})

    p_info = EmployeePersonalInfo(
        employee_id=emp.id,
        date_of_birth=_parse_date(personal_data.get("dateOfBirth")),
        gender=personal_data.get("gender"),
        blood_group=personal_data.get("bloodGroup"),
        marital_status=personal_data.get("maritalStatus"),
        nationality=personal_data.get("nationality"),
        languages=personal_data.get("languages") or [],
        profile_photo=personal_data.get("profilePhoto"),
        personal_email=personal_data.get("personalEmail") or payload.get("email"),
        phone_primary=personal_data.get("phonePrimary") or payload.get("phone"),
        phone_secondary=personal_data.get("phoneSecondary"),
        phone_emergency=personal_data.get("phoneEmergency"),
        curr_line1=curr_addr.get("line1"), curr_line2=curr_addr.get("line2"),
        curr_city=curr_addr.get("city"), curr_state=curr_addr.get("state"),
        curr_pincode=curr_addr.get("pincode"), curr_country=curr_addr.get("country"),
        perm_line1=perm_addr.get("line1"), perm_line2=perm_addr.get("line2"),
        perm_city=perm_addr.get("city"), perm_state=perm_addr.get("state"),
        perm_pincode=perm_addr.get("pincode"), perm_country=perm_addr.get("country"),
    )
    db.add(p_info)

   
    for c in (personal_data.get("emergencyContacts") or []):
        if c.get("name"):
            db.add(EmployeeEmergencyContact(
                employee_id=emp.id,
                name=c["name"],
                relation=c.get("relation"),
                phone=c.get("phone"),
                priority=c.get("priority", "Primary"),
            ))

   
    for m in (personal_data.get("familyMembers") or []):
        if m.get("name"):
            db.add(EmployeeFamilyMember(
                employee_id=emp.id,
                name=m["name"],
                relation=m.get("relation"),
                date_of_birth=_parse_date(m.get("dateOfBirth") or m.get("dob")),
                contact_no=m.get("contactNo"),
            ))

   
    for n in (personal_data.get("nominees") or []):
        if n.get("name"):
            db.add(EmployeeNominee(
                employee_id=emp.id,
                name=n["name"],
                relation=n.get("relation"),
                phone=n.get("phone") or n.get("contactNo"),
                percentage=n.get("percentage", 0),
                is_nominee_accepted=n.get("isNomineeAccepted", False),
            ))

   
    db.add(EmployeeIdentification(
        employee_id=emp.id,
        pan_number=pan_data.get("number"),
        pan_verified=pan_data.get("verified", False),
        aadhaar_number=aadhaar_data.get("number"),
        aadhaar_verified=aadhaar_data.get("verified", False),
        passport_number=identification.get("passport", {}).get("number"),
        passport_expiry_date=_parse_date(identification.get("passport", {}).get("expiryDate")),
        voter_id_number=identification.get("voterId", {}).get("number"),
    ))

   
    reporting = emp_info_data.get("reportingManager", {})
    db.add(EmployeeEmploymentInfo(
        employee_id=emp.id,
        employee_code=emp_code,
        date_of_joining=join_date,
        confirmation_date=_parse_date(emp_info_data.get("confirmationDate")),
        probation_period=emp_info_data.get("probationPeriod", 6),
        employment_type=emp_info_data.get("employmentType") or payload.get("employmentType", "Permanent"),
        employment_status=emp_info_data.get("employmentStatus") or payload.get("status", "Active"),
        department=emp_info_data.get("department") or payload.get("department"),
        sub_department=emp_info_data.get("subDepartment"),
        cost_center=emp_info_data.get("costCenter"),
        designation=emp_info_data.get("designation") or payload.get("designation"),
        grade=emp_info_data.get("grade"),
        level=emp_info_data.get("level"),
        location=emp_info_data.get("location") or payload.get("location"),
        workplace_type=emp_info_data.get("workplaceType", "Office"),
        work_email=emp_info_data.get("workEmail") or payload.get("email"),
        extension_number=emp_info_data.get("extensionNumber"),
        desk_location=emp_info_data.get("deskLocation"),
        employee_category=emp_info_data.get("employeeCategory", "Staff"),
        notice_period=emp_info_data.get("noticePeriod", 30),
        direct_manager=reporting.get("direct"),
        functional_manager=reporting.get("functional"),
        hr_business_partner=emp_info_data.get("hrBusinessPartner"),
    ))

  
    for jh in (job_history_data or []):
        if jh.get("date") or jh.get("type"):
            db.add(EmployeeJobHistory(
                employee_id=emp.id,
                start_date=_parse_date(jh.get("date")),
                end_date=jh.get("endDate"),
                history_type=jh.get("type"),
                organisation=jh.get("organisation"),
                department=jh.get("department"),
                designation=jh.get("designation"),
                location=jh.get("location"),
                manager=jh.get("manager"),
                salary_change=jh.get("salaryChange"),
                notes=jh.get("notes"),
                achievements=jh.get("achievements"),
                reason_for_leaving=jh.get("reasonForLeaving"),
            ))

   
    ctc_bd = salary_data.get("ctcBreakdown", {})
    bank_accounts_data = salary_data.get("bankAccounts", {})
    tax_decl = salary_data.get("taxDeclaration", {})
    var_pay = salary_data.get("variablePay", {})
    bonus = salary_data.get("bonusEligibility", {})

    current_ctc = salary_data.get("currentCTC") or payload.get("salary") or 0

    db.add(EmployeeSalaryInfo(
        employee_id=emp.id,
        current_ctc=current_ctc,
        salary_structure=salary_data.get("salaryStructure"),
        basic=ctc_bd.get("basic", 0),
        hra=ctc_bd.get("hra", 0),
        special_allowance=ctc_bd.get("specialAllowance", 0),
        transport_allowance=ctc_bd.get("transportAllowance", 0),
        medical_allowance=ctc_bd.get("medicalAllowance", 0),
        other_allowances=ctc_bd.get("otherAllowances", 0),
        provident_fund=ctc_bd.get("providentFund", 0),
        gratuity=ctc_bd.get("gratuity", 0),
        other_deductions=ctc_bd.get("otherDeductions", 0),
        payment_mode=salary_data.get("paymentMode", "Bank Transfer"),
        pf_account_number=salary_data.get("pfAccountNumber"),
        uan=salary_data.get("uan"),
        esi_number=salary_data.get("esiNumber"),
        esi_medical_nominee=salary_data.get("esiMedicalNominee"),
        tax_regime=tax_decl.get("regime", "New"),
        tax_declared=tax_decl.get("declared", False),
        variable_pay_eligible=var_pay.get("eligible", False),
        variable_pay_pct=var_pay.get("percentage", 0),
        bonus_eligible=bonus.get("eligible", False),
        bonus_amount=bonus.get("amount", 0),
    ))

    
    primary_bank = bank_accounts_data.get("primary", {})
    if primary_bank.get("accountNumber"):
        db.add(EmployeeBankAccount(
            employee_id=emp.id,
            account_type_label="primary",
            account_number=primary_bank.get("accountNumber"),
            ifsc_code=primary_bank.get("ifscCode"),
            bank_name=primary_bank.get("bankName"),
            branch=primary_bank.get("branch"),
            account_type=primary_bank.get("accountType", "Savings"),
        ))

    secondary_bank = bank_accounts_data.get("secondary")
    if secondary_bank and secondary_bank.get("accountNumber"):
        db.add(EmployeeBankAccount(
            employee_id=emp.id,
            account_type_label="secondary",
            account_number=secondary_bank.get("accountNumber"),
            ifsc_code=secondary_bank.get("ifscCode"),
            bank_name=secondary_bank.get("bankName"),
            branch=secondary_bank.get("branch"),
            account_type=secondary_bank.get("accountType", "Savings"),
        ))

 
    for rev in (salary_data.get("salaryRevisionHistory") or []):
        if rev.get("effectiveDate"):
            db.add(EmployeeSalaryRevision(
                employee_id=emp.id,
                effective_date=_parse_date(rev.get("effectiveDate")),
                previous_ctc=rev.get("previousCTC", 0),
                new_ctc=rev.get("newCTC", 0),
                percentage_increase=rev.get("percentageIncrease", 0),
                approved_by=rev.get("approvedBy"),
                status=rev.get("status", "Pending"),
            ))

   
    pf_data  = statutory_data.get("pfMembership", {})
    esi_data = statutory_data.get("esiRegistration", {})
    pt_data  = statutory_data.get("professionalTax", {})
    lwf_data = statutory_data.get("labourWelfareFund", {})
    grat_data = statutory_data.get("gratuity", {})
    shops_data = statutory_data.get("shopsAndEstablishment", {})

    pan_stat    = statutory_data.get("pan", {})
    aadhaar_stat = statutory_data.get("aadhaar", {})

    db.add(EmployeeStatutoryInfo(
        employee_id=emp.id,
        pan_number=pan_stat.get("number") or pan_data.get("number"),
        pan_verified=pan_stat.get("verified", False),
        pan_verified_date=_parse_date(pan_stat.get("verifiedDate")),
        aadhaar_number=aadhaar_stat.get("number") or aadhaar_data.get("number"),
        aadhaar_verified=aadhaar_stat.get("verified", False),
        aadhaar_verified_date=_parse_date(aadhaar_stat.get("verifiedDate")),
        pf_enrolled=pf_data.get("enrolled", False),
        pf_account_number=pf_data.get("accountNumber"),
        pf_uan=pf_data.get("uan"),
        pf_enrollment_date=_parse_date(pf_data.get("enrollmentDate")),
        pf_account_type=pf_data.get("accountType"),
        esi_enrolled=esi_data.get("enrolled", False),
        esi_number=esi_data.get("number"),
        esi_enrollment_date=_parse_date(esi_data.get("enrollmentDate")),
        pt_applicable=pt_data.get("applicable", False),
        pt_state=pt_data.get("state"),
        pt_number=pt_data.get("ptNumber"),
        lwf_enrolled=lwf_data.get("enrolled", False),
        lwf_enrollment_date=_parse_date(lwf_data.get("enrollmentDate")),
        gratuity_eligible=grat_data.get("eligible", False),
        gratuity_eligibility_date=_parse_date(grat_data.get("eligibilityDate")),
        bonus_act_applicable=statutory_data.get("bonusAct", {}).get("applicable", False),
        shops_registered=shops_data.get("registered", False),
        shops_registration_number=shops_data.get("registrationNumber"),
        shops_registration_date=_parse_date(shops_data.get("registrationDate")),
    ))


    db.add(EmployeeMaster(
        employee_id=emp.id,
        salary=current_ctc,
        currency="INR",
        employment_type=emp_info_data.get("employmentType") or payload.get("employmentType", "Full-Time"),
        employment_status=emp_info_data.get("employmentStatus") or payload.get("status", "Active"),
        notice_period_days=emp_info_data.get("noticePeriod", 30),
        work_location=emp_info_data.get("location") or payload.get("location"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))

    db.commit()
    db.refresh(emp)
    return _build_response(emp, db)


def update_employee(db: Session, employee_id: int, payload: dict, tenant_id: Optional[int]) -> dict:
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if tenant_id is not None and emp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    personal_data  = payload.get("personalInfo", {})
    emp_info_data  = payload.get("employmentInfo", {})
    salary_data    = payload.get("salaryInfo", {})
    statutory_data = payload.get("statutoryInfo", {})
    job_history_data = payload.get("jobHistory", [])
    identification = personal_data.get("identification", {})
    pan_data       = identification.get("pan", {})
    aadhaar_data   = identification.get("aadhaar", {})

   
    name_parts = (payload.get("name", "") or "").strip().split(" ", 1)
    if name_parts[0]:
        emp.first_name = name_parts[0]
        emp.last_name = name_parts[1] if len(name_parts) > 1 else None

    if emp_info_data.get("workEmail") or payload.get("email"):
        emp.official_email = emp_info_data.get("workEmail") or payload.get("email")
    if personal_data.get("phonePrimary") or payload.get("phone"):
        new_phone = personal_data.get("phonePrimary") or payload.get("phone")
        # only update if different to avoid unique constraint errors
        if new_phone != emp.mobile_number:
            emp.mobile_number = new_phone
    if emp_info_data.get("dateOfJoining"):
        emp.joining_date = _parse_date(emp_info_data.get("dateOfJoining"))
    if emp_info_data.get("department") or payload.get("department"):
        emp.department = emp_info_data.get("department") or payload.get("department")
    if emp_info_data.get("designation") or payload.get("designation"):
        emp.designation = emp_info_data.get("designation") or payload.get("designation")
    if emp_info_data.get("location") or payload.get("location"):
        emp.location = emp_info_data.get("location") or payload.get("location")
    if emp_info_data.get("grade"):
        emp.grade = emp_info_data.get("grade")
    if emp_info_data.get("costCenter"):
        emp.cost_center = emp_info_data.get("costCenter")

  
    p_info = db.execute(
        select(EmployeePersonalInfo).where(EmployeePersonalInfo.employee_id == employee_id)
    ).scalar_one_or_none()

    curr_addr = personal_data.get("currentAddress", {})
    perm_addr = personal_data.get("permanentAddress", {})

    if p_info:
        if personal_data.get("dateOfBirth"): p_info.date_of_birth = _parse_date(personal_data["dateOfBirth"])
        if personal_data.get("gender"):       p_info.gender = personal_data["gender"]
        if personal_data.get("bloodGroup"):   p_info.blood_group = personal_data["bloodGroup"]
        if personal_data.get("maritalStatus"): p_info.marital_status = personal_data["maritalStatus"]
        if personal_data.get("nationality"):   p_info.nationality = personal_data["nationality"]
        if "languages" in personal_data:       p_info.languages = personal_data["languages"]
        if personal_data.get("profilePhoto"):  p_info.profile_photo = personal_data["profilePhoto"]
        if personal_data.get("personalEmail"): p_info.personal_email = personal_data["personalEmail"]
        if personal_data.get("phonePrimary"):  p_info.phone_primary = personal_data["phonePrimary"]
        if personal_data.get("phoneSecondary"): p_info.phone_secondary = personal_data["phoneSecondary"]
        if personal_data.get("phoneEmergency"): p_info.phone_emergency = personal_data["phoneEmergency"]
        if curr_addr:
            p_info.curr_line1 = curr_addr.get("line1", p_info.curr_line1)
            p_info.curr_line2 = curr_addr.get("line2", p_info.curr_line2)
            p_info.curr_city  = curr_addr.get("city",  p_info.curr_city)
            p_info.curr_state = curr_addr.get("state", p_info.curr_state)
            p_info.curr_pincode = curr_addr.get("pincode", p_info.curr_pincode)
            p_info.curr_country = curr_addr.get("country", p_info.curr_country)
        if perm_addr:
            p_info.perm_line1 = perm_addr.get("line1", p_info.perm_line1)
            p_info.perm_line2 = perm_addr.get("line2", p_info.perm_line2)
            p_info.perm_city  = perm_addr.get("city",  p_info.perm_city)
            p_info.perm_state = perm_addr.get("state", p_info.perm_state)
            p_info.perm_pincode = perm_addr.get("pincode", p_info.perm_pincode)
            p_info.perm_country = perm_addr.get("country", p_info.perm_country)
        p_info.updated_at = datetime.utcnow()
    else:
        db.add(EmployeePersonalInfo(
            employee_id=employee_id,
            date_of_birth=_parse_date(personal_data.get("dateOfBirth")),
            gender=personal_data.get("gender"),
            blood_group=personal_data.get("bloodGroup"),
            marital_status=personal_data.get("maritalStatus"),
            nationality=personal_data.get("nationality"),
            languages=personal_data.get("languages") or [],
            profile_photo=personal_data.get("profilePhoto"),
            personal_email=personal_data.get("personalEmail"),
            phone_primary=personal_data.get("phonePrimary"),
            phone_secondary=personal_data.get("phoneSecondary"),
            phone_emergency=personal_data.get("phoneEmergency"),
            curr_line1=curr_addr.get("line1"), curr_line2=curr_addr.get("line2"),
            curr_city=curr_addr.get("city"), curr_state=curr_addr.get("state"),
            curr_pincode=curr_addr.get("pincode"), curr_country=curr_addr.get("country"),
            perm_line1=perm_addr.get("line1"), perm_line2=perm_addr.get("line2"),
            perm_city=perm_addr.get("city"), perm_state=perm_addr.get("state"),
            perm_pincode=perm_addr.get("pincode"), perm_country=perm_addr.get("country"),
        ))

   
    if "emergencyContacts" in personal_data:
        db.execute(
            EmployeeEmergencyContact.__table__.delete().where(
                EmployeeEmergencyContact.employee_id == employee_id
            )
        )
        for c in (personal_data["emergencyContacts"] or []):
            if c.get("name"):
                db.add(EmployeeEmergencyContact(
                    employee_id=employee_id, name=c["name"],
                    relation=c.get("relation"), phone=c.get("phone"),
                    priority=c.get("priority", "Primary"),
                ))

    if "familyMembers" in personal_data:
        db.execute(
            EmployeeFamilyMember.__table__.delete().where(
                EmployeeFamilyMember.employee_id == employee_id
            )
        )
        for m in (personal_data["familyMembers"] or []):
            if m.get("name"):
                db.add(EmployeeFamilyMember(
                    employee_id=employee_id, name=m["name"],
                    relation=m.get("relation"),
                    date_of_birth=_parse_date(m.get("dateOfBirth") or m.get("dob")),
                    contact_no=m.get("contactNo"),
                ))

    if "nominees" in personal_data:
        db.execute(
            EmployeeNominee.__table__.delete().where(
                EmployeeNominee.employee_id == employee_id
            )
        )
        for n in (personal_data["nominees"] or []):
            if n.get("name"):
                db.add(EmployeeNominee(
                    employee_id=employee_id, name=n["name"],
                    relation=n.get("relation"),
                    phone=n.get("phone") or n.get("contactNo"),
                    percentage=n.get("percentage", 0),
                    is_nominee_accepted=n.get("isNomineeAccepted", False),
                ))


    id_rec = db.execute(
        select(EmployeeIdentification).where(EmployeeIdentification.employee_id == employee_id)
    ).scalar_one_or_none()
    if id_rec:
        if pan_data.get("number"):       id_rec.pan_number = pan_data["number"]
        if "verified" in pan_data:       id_rec.pan_verified = pan_data["verified"]
        if aadhaar_data.get("number"):   id_rec.aadhaar_number = aadhaar_data["number"]
        if "verified" in aadhaar_data:   id_rec.aadhaar_verified = aadhaar_data["verified"]
        passport = identification.get("passport", {})
        if passport.get("number"):       id_rec.passport_number = passport["number"]
        if passport.get("expiryDate"):   id_rec.passport_expiry_date = _parse_date(passport["expiryDate"])
        voter = identification.get("voterId", {})
        if voter.get("number"):          id_rec.voter_id_number = voter["number"]
        id_rec.updated_at = datetime.utcnow()


    ei = db.execute(
        select(EmployeeEmploymentInfo).where(EmployeeEmploymentInfo.employee_id == employee_id)
    ).scalar_one_or_none()
    reporting = emp_info_data.get("reportingManager", {})
    if ei:
        for field, value in [
            ("employment_type", emp_info_data.get("employmentType")),
            ("employment_status", emp_info_data.get("employmentStatus")),
            ("department", emp_info_data.get("department")),
            ("sub_department", emp_info_data.get("subDepartment")),
            ("cost_center", emp_info_data.get("costCenter")),
            ("designation", emp_info_data.get("designation")),
            ("grade", emp_info_data.get("grade")),
            ("level", emp_info_data.get("level")),
            ("location", emp_info_data.get("location")),
            ("workplace_type", emp_info_data.get("workplaceType")),
            ("work_email", emp_info_data.get("workEmail")),
            ("extension_number", emp_info_data.get("extensionNumber")),
            ("desk_location", emp_info_data.get("deskLocation")),
            ("employee_category", emp_info_data.get("employeeCategory")),
            ("notice_period", emp_info_data.get("noticePeriod")),
            ("direct_manager", reporting.get("direct")),
            ("functional_manager", reporting.get("functional")),
            ("hr_business_partner", emp_info_data.get("hrBusinessPartner")),
        ]:
            if value is not None:
                setattr(ei, field, value)
        if emp_info_data.get("dateOfJoining"):
            ei.date_of_joining = _parse_date(emp_info_data["dateOfJoining"])
        if emp_info_data.get("confirmationDate"):
            ei.confirmation_date = _parse_date(emp_info_data["confirmationDate"])
        if emp_info_data.get("probationPeriod") is not None:
            ei.probation_period = emp_info_data["probationPeriod"]
        ei.updated_at = datetime.utcnow()

  
    if job_history_data is not None:
        db.execute(
            EmployeeJobHistory.__table__.delete().where(
                EmployeeJobHistory.employee_id == employee_id
            )
        )
        for jh in job_history_data:
            if jh.get("date") or jh.get("type"):
                db.add(EmployeeJobHistory(
                    employee_id=employee_id,
                    start_date=_parse_date(jh.get("date")),
                    end_date=jh.get("endDate"),
                    history_type=jh.get("type"),
                    organisation=jh.get("organisation"),
                    department=jh.get("department"),
                    designation=jh.get("designation"),
                    location=jh.get("location"),
                    manager=jh.get("manager"),
                    salary_change=jh.get("salaryChange"),
                    notes=jh.get("notes"),
                    achievements=jh.get("achievements"),
                    reason_for_leaving=jh.get("reasonForLeaving"),
                ))


    si = db.execute(
        select(EmployeeSalaryInfo).where(EmployeeSalaryInfo.employee_id == employee_id)
    ).scalar_one_or_none()
    if si and salary_data:
        ctc_bd = salary_data.get("ctcBreakdown", {})
        tax_decl = salary_data.get("taxDeclaration", {})
        var_pay = salary_data.get("variablePay", {})
        bonus = salary_data.get("bonusEligibility", {})
        if salary_data.get("currentCTC") is not None: si.current_ctc = salary_data["currentCTC"]
        if salary_data.get("salaryStructure"):    si.salary_structure = salary_data["salaryStructure"]
        if ctc_bd.get("basic") is not None:       si.basic = ctc_bd["basic"]
        if ctc_bd.get("hra") is not None:         si.hra = ctc_bd["hra"]
        if ctc_bd.get("specialAllowance") is not None: si.special_allowance = ctc_bd["specialAllowance"]
        if ctc_bd.get("transportAllowance") is not None: si.transport_allowance = ctc_bd["transportAllowance"]
        if ctc_bd.get("medicalAllowance") is not None: si.medical_allowance = ctc_bd["medicalAllowance"]
        if ctc_bd.get("otherAllowances") is not None: si.other_allowances = ctc_bd["otherAllowances"]
        if ctc_bd.get("providentFund") is not None: si.provident_fund = ctc_bd["providentFund"]
        if ctc_bd.get("gratuity") is not None:    si.gratuity = ctc_bd["gratuity"]
        if ctc_bd.get("otherDeductions") is not None: si.other_deductions = ctc_bd["otherDeductions"]
        if salary_data.get("paymentMode"):        si.payment_mode = salary_data["paymentMode"]
        if salary_data.get("pfAccountNumber"):    si.pf_account_number = salary_data["pfAccountNumber"]
        if salary_data.get("uan"):                si.uan = salary_data["uan"]
        if salary_data.get("esiNumber"):          si.esi_number = salary_data["esiNumber"]
        if salary_data.get("esiMedicalNominee"):  si.esi_medical_nominee = salary_data["esiMedicalNominee"]
        if "regime" in tax_decl:    si.tax_regime = tax_decl["regime"]
        if "declared" in tax_decl:  si.tax_declared = tax_decl["declared"]
        if "eligible" in var_pay:   si.variable_pay_eligible = var_pay["eligible"]
        if "percentage" in var_pay: si.variable_pay_pct = var_pay["percentage"]
        if "eligible" in bonus:     si.bonus_eligible = bonus["eligible"]
        if "amount" in bonus:       si.bonus_amount = bonus["amount"]
        si.updated_at = datetime.utcnow()


        bank_accounts_data = salary_data.get("bankAccounts", {})
        if bank_accounts_data:
            db.execute(
                EmployeeBankAccount.__table__.delete().where(
                    EmployeeBankAccount.employee_id == employee_id
                )
            )
            primary_bank = bank_accounts_data.get("primary", {})
            if primary_bank.get("accountNumber"):
                db.add(EmployeeBankAccount(
                    employee_id=employee_id, account_type_label="primary",
                    account_number=primary_bank.get("accountNumber"),
                    ifsc_code=primary_bank.get("ifscCode"),
                    bank_name=primary_bank.get("bankName"),
                    branch=primary_bank.get("branch"),
                    account_type=primary_bank.get("accountType", "Savings"),
                ))
            secondary_bank = bank_accounts_data.get("secondary")
            if secondary_bank and secondary_bank.get("accountNumber"):
                db.add(EmployeeBankAccount(
                    employee_id=employee_id, account_type_label="secondary",
                    account_number=secondary_bank.get("accountNumber"),
                    ifsc_code=secondary_bank.get("ifscCode"),
                    bank_name=secondary_bank.get("bankName"),
                    branch=secondary_bank.get("branch"),
                    account_type=secondary_bank.get("accountType", "Savings"),
                ))

        # Salary revisions — full replace
        if "salaryRevisionHistory" in salary_data:
            db.execute(
                EmployeeSalaryRevision.__table__.delete().where(
                    EmployeeSalaryRevision.employee_id == employee_id
                )
            )
            for rev in salary_data["salaryRevisionHistory"]:
                if rev.get("effectiveDate"):
                    db.add(EmployeeSalaryRevision(
                        employee_id=employee_id,
                        effective_date=_parse_date(rev.get("effectiveDate")),
                        previous_ctc=rev.get("previousCTC", 0),
                        new_ctc=rev.get("newCTC", 0),
                        percentage_increase=rev.get("percentageIncrease", 0),
                        approved_by=rev.get("approvedBy"),
                        status=rev.get("status", "Pending"),
                    ))

 
    stat = db.execute(
        select(EmployeeStatutoryInfo).where(EmployeeStatutoryInfo.employee_id == employee_id)
    ).scalar_one_or_none()
    if stat and statutory_data:
        pan_stat = statutory_data.get("pan", {})
        aadhaar_stat = statutory_data.get("aadhaar", {})
        pf_data  = statutory_data.get("pfMembership", {})
        esi_data = statutory_data.get("esiRegistration", {})
        pt_data  = statutory_data.get("professionalTax", {})
        lwf_data = statutory_data.get("labourWelfareFund", {})
        grat_data = statutory_data.get("gratuity", {})
        shops_data = statutory_data.get("shopsAndEstablishment", {})
        bonus_act = statutory_data.get("bonusAct", {})

        for field, val in [
            ("pan_number", pan_stat.get("number")),
            ("pan_verified", pan_stat.get("verified")),
            ("aadhaar_number", aadhaar_stat.get("number")),
            ("aadhaar_verified", aadhaar_stat.get("verified")),
            ("pf_enrolled", pf_data.get("enrolled")),
            ("pf_account_number", pf_data.get("accountNumber")),
            ("pf_uan", pf_data.get("uan")),
            ("pf_account_type", pf_data.get("accountType")),
            ("esi_enrolled", esi_data.get("enrolled")),
            ("esi_number", esi_data.get("number")),
            ("pt_applicable", pt_data.get("applicable")),
            ("pt_state", pt_data.get("state")),
            ("pt_number", pt_data.get("ptNumber")),
            ("lwf_enrolled", lwf_data.get("enrolled")),
            ("gratuity_eligible", grat_data.get("eligible")),
            ("bonus_act_applicable", bonus_act.get("applicable")),
            ("shops_registered", shops_data.get("registered")),
            ("shops_registration_number", shops_data.get("registrationNumber")),
        ]:
            if val is not None:
                setattr(stat, field, val)
        if pan_stat.get("verifiedDate"):   stat.pan_verified_date = _parse_date(pan_stat["verifiedDate"])
        if aadhaar_stat.get("verifiedDate"): stat.aadhaar_verified_date = _parse_date(aadhaar_stat["verifiedDate"])
        if pf_data.get("enrollmentDate"):   stat.pf_enrollment_date = _parse_date(pf_data["enrollmentDate"])
        if esi_data.get("enrollmentDate"):  stat.esi_enrollment_date = _parse_date(esi_data["enrollmentDate"])
        if lwf_data.get("enrollmentDate"):  stat.lwf_enrollment_date = _parse_date(lwf_data["enrollmentDate"])
        if grat_data.get("eligibilityDate"): stat.gratuity_eligibility_date = _parse_date(grat_data["eligibilityDate"])
        if shops_data.get("registrationDate"): stat.shops_registration_date = _parse_date(shops_data["registrationDate"])
        stat.updated_at = datetime.utcnow()


    master = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()
    if master:
        if salary_data.get("currentCTC") is not None:
            master.salary = salary_data["currentCTC"]
        if emp_info_data.get("employmentType"):
            master.employment_type = emp_info_data["employmentType"]
        if emp_info_data.get("employmentStatus"):
            master.employment_status = emp_info_data["employmentStatus"]
        if emp_info_data.get("noticePeriod") is not None:
            master.notice_period_days = emp_info_data["noticePeriod"]
        if emp_info_data.get("location"):
            master.work_location = emp_info_data["location"]
        master.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(emp)
    return _build_response(emp, db)


def delete_employee(db: Session, employee_id: int, tenant_id: Optional[int], hard: bool = False) -> dict:
    emp = db.execute(select(Employee).where(Employee.id == employee_id)).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if tenant_id is not None and emp.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    if hard:
       
        for table in [
            EmployeePersonalInfo, EmployeeEmergencyContact, EmployeeFamilyMember,
            EmployeeNominee, EmployeeIdentification, EmployeeEmploymentInfo,
            EmployeeJobHistory, EmployeeSalaryInfo, EmployeeBankAccount,
            EmployeeSalaryRevision, EmployeeStatutoryInfo, EmployeeMaster
        ]:
            db.execute(table.__table__.delete().where(table.employee_id == employee_id))
        db.delete(emp)
        db.commit()
        return {"message": f"Employee {employee_id} permanently deleted."}
    else:
        emp.is_active = False
        master = db.execute(
            select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
        ).scalar_one_or_none()
        if master:
            master.employment_status = "Terminated"
            master.updated_at = datetime.utcnow()
        ei = db.execute(
            select(EmployeeEmploymentInfo).where(EmployeeEmploymentInfo.employee_id == employee_id)
        ).scalar_one_or_none()
        if ei:
            ei.employment_status = "Terminated"
            ei.updated_at = datetime.utcnow()
        db.commit()
        return {"message": f"Employee {employee_id} deactivated and set to Terminated."}
    