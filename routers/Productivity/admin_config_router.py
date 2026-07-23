from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.database import get_db
from services.Productivity.admin_config_service import add_entity, list_entities, get_entity, update_entity, delete_entity
from schema.Productivity.admin_schemas import ProductiveEntityCreate, ProductiveEntityResponse
from core.dependencies import require_roles
from typing import List

router = APIRouter(prefix="/admin/config")

@router.post("/entities", response_model=ProductiveEntityResponse, status_code=status.HTTP_201_CREATED)
def create_entity(payload: ProductiveEntityCreate, db: Session = Depends(get_db), _=Depends(require_roles(["superadmin"]))):
    try:
        ent = add_entity(db, payload)
        return ent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/entities", response_model=List[ProductiveEntityResponse])
def get_entities(db: Session = Depends(get_db), _=Depends(require_roles(["superadmin"]))):
    return list_entities(db)

@router.get("/entities/{entity_id}", response_model=ProductiveEntityResponse)
def get_single(entity_id: int, db: Session = Depends(get_db), _=Depends(require_roles(["superadmin"]))):
    ent = get_entity(db, entity_id)
    if not ent:
        raise HTTPException(status_code=404, detail="Not found")
    return ent

@router.patch("/entities/{entity_id}", response_model=ProductiveEntityResponse)
def patch_entity(entity_id: int, payload: ProductiveEntityCreate, db: Session = Depends(get_db), _=Depends(require_roles(["superadmin"]))):
    try:
        updated = update_entity(db, entity_id, payload.model_dump())
        return updated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entity(entity_id: int, db: Session = Depends(get_db), _=Depends(require_roles(["superadmin"]))):
    try:
        delete_entity(db, entity_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {}
