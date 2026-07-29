from sqlalchemy.orm import Session
from typing import List, Optional

from model.client import Client
from schema.client import ClientCreate, ClientOut

def get_client(db: Session, client_id: int, tenant_id: Optional[int] = None) -> Optional[Client]:
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        return None
    if tenant_id is not None and client.tenant_id != tenant_id:
        return None
    return client

def get_clients(db: Session, skip: int = 0, limit: int = 100, tenant_id: Optional[int] = None) -> List[Client]:
    query = db.query(Client)
    if tenant_id is not None:
        query = query.filter(Client.tenant_id == tenant_id)
    return query.offset(skip).limit(limit).all()

def create_client(db: Session, client: ClientCreate, tenant_id: Optional[int] = None) -> Client:
    db_obj = Client(
        name=client.name,
        Project_name=client.Project_name,
        tenant_id=tenant_id,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj