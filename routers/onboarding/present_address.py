from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from schema.onboarding.present_address import PresentAddressCreate, PresentAddressResponse
from services.present_address_service import create_present_address, get_present_address

router = APIRouter(prefix="/present-address", tags=["Present Address"])

@router.post("/", response_model=PresentAddressResponse)
def create_address(data: PresentAddressCreate, db: Session = Depends(get_db)):
    return create_present_address(db, data)

@router.get("/{address_id}", response_model=PresentAddressResponse)
def read_address(address_id: int, db: Session = Depends(get_db)):
    address = get_present_address(db, address_id)
    if not address:
        raise HTTPException(status_code=404, detail="Present address not found")
    return address
