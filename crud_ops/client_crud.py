from sqlalchemy.orm import Session
from typing import List, Optional

from model.client import Client
from schema.client import ClientCreate, ClientOut

def get_client(db: Session, client_id: int) -> Optional[Client]:
    return db.query(Client).filter(Client.id == client_id).first()

def get_clients(db: Session, skip: int = 0, limit: int = 100) -> List[Client]:
    return db.query(Client).offset(skip).limit(limit).all()

def create_client(db: Session, client: ClientCreate) -> Client:
    db_obj = Client(
        name=client.name,
        Project_name=client.Project_name,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
