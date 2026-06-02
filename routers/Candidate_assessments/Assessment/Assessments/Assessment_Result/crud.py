from sqlalchemy.orm import Session
import model.models
from schema import schemas

def get_candidates(db: Session):
    return db.query(model.models.Candidate).all()

def get_candidate(db: Session, candidate_id: int):
    return db.query(model.models.Candidate).filter(model.models.Candidate.id == candidate_id).first()
