from sqlalchemy.orm import Session
from model.Company_Settings.policy import Policy
from schema.Company_Settings.policy import PolicyCreate

def create_policy(db: Session, data: PolicyCreate, document_path: str | None = None):
    policy = Policy(
        title=data.title,
        category=data.category,
        version=data.version,
        effective_date=data.effective_date,
        description=data.description,
        document_path=document_path,
        status="Draft",
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy

def get_policy(db: Session, policy_id: int):
    return db.query(Policy).filter(Policy.id == policy_id).first()

def update_policy(db: Session, policy: Policy, data: dict):
    for key, value in data.items():
        setattr(policy, key, value)
    db.commit()
    db.refresh(policy)
    return policy
