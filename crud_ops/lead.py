from sqlalchemy.orm import Session
from model.lead import Lead, LeadStatus


def _normalize_status(status: str | None) -> LeadStatus | None:
    if not status:
        return None
    cleaned = status.strip()
    if not cleaned:
        return None
    if cleaned == "Not Contacted":
        cleaned = "Not_Contacted"

    for enum_value in LeadStatus:
        if enum_value.value.lower() == cleaned.lower():
            return enum_value
    return None


def get_leads(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    company: str | None = None,
    owner: str | None = None,
):
    query = db.query(Lead)

    normalized_status = _normalize_status(status)
    if normalized_status is not None:
        query = query.filter(Lead.status == normalized_status)
    if company:
        company_value = company.strip().lower()
        if company_value:
            query = query.filter(Lead.company.ilike(f"%{company_value}%"))
    if owner:
        owner_value = owner.strip().lower()
        if owner_value:
            query = query.filter(Lead.owner.ilike(f"%{owner_value}%"))

    return query.offset(skip).limit(limit).all()


def get_lead(db: Session, lead_id: int):
    return db.get(Lead, lead_id)


def create_lead(db: Session, lead_in):
    lead = Lead(**lead_in.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def update_lead(db: Session, lead_id: int, lead_in):
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    data = lead_in.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(lead, k, v)

    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead_id: int):
    lead = db.get(Lead, lead_id)
    if not lead:
        return False

    db.delete(lead)
    db.commit()
    return True
