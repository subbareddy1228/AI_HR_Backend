from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from schema.onboarding.address import AddressCreate, AddressResponse
from services.address_service import create_address, get_address

router = APIRouter(prefix="/address", tags=["Permanent Address"])

@router.post("/", response_model=AddressResponse)
def add_permanent_address(address: AddressCreate, db: Session = Depends(get_db)):
    return create_address(db, address)

@router.get("/{address_id}", response_model=AddressResponse)
def fetch_address(address_id: int, db: Session = Depends(get_db)):
    address = get_address(db, address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    return address
