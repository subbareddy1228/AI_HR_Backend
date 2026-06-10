
from sqlalchemy.orm import Session
from typing import List, Optional

from model.Productivity.productive_entity import ProductiveEntity
from schema.Productivity.admin_schemas import ProductiveEntityCreate

def add_entity(db: Session, data: ProductiveEntityCreate) -> ProductiveEntity:

    existing = db.query(ProductiveEntity).filter(ProductiveEntity.name == data.name).first()
    if existing:
        raise ValueError("Entity already exists")
    ent = ProductiveEntity(name=data.name, entity_type=data.entity_type, productive=data.productive)
    db.add(ent)
    db.commit()
    db.refresh(ent)
    return ent

def list_entities(db: Session) -> List[ProductiveEntity]:
    return db.query(ProductiveEntity).all()

def get_entity(db: Session, entity_id: int) -> Optional[ProductiveEntity]:
    return db.query(ProductiveEntity).filter(ProductiveEntity.id == entity_id).first()

def update_entity(db: Session, entity_id: int, updates: dict) -> ProductiveEntity:
    ent = get_entity(db, entity_id)
    if not ent:
        raise ValueError("Not found")
    for k, v in updates.items():
        if hasattr(ent, k):
            setattr(ent, k, v)
    db.commit()
    db.refresh(ent)
    return ent

def delete_entity(db: Session, entity_id: int) -> None:
    ent = get_entity(db, entity_id)
    if not ent:
        raise ValueError("Not found")
    db.delete(ent)
    db.commit()
