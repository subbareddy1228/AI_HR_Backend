from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from crud_ops import crud
from core.database import get_db
from schema import schemas 

router = APIRouter(prefix="/leave", tags=["Leave"])

@router.get("/", response_model=list[schemas.LeaveRequestOut])
def get_all_leaves(db: Session = Depends(get_db)):
    return crud.get_leaves(db)

@router.post("/", response_model=schemas.LeaveRequestOut)
def apply_leave(leave: schemas.LeaveRequestCreate, db: Session = Depends(get_db)):
    return crud.create_leave(db, leave)

@router.get("/{leave_id}", response_model=schemas.LeaveRequestOut)
def get_leave(leave_id: int, db: Session = Depends(get_db)):
    leave = crud.get_leave_by_id(db, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return leave
