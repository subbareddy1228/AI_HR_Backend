from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from crud_ops.client_crud import (create_client,get_clients)
from schema.client import ClientCreate, ClientOut
from core.database import SessionLocal


router = APIRouter(prefix="/clients", tags=["clients"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client_route(client_in: ClientCreate, db: Session = Depends(get_db)):
    return create_client(db, client_in)


@router.get("/", response_model=List[ClientOut])
def list_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_clients(db, skip=skip, limit=limit)
