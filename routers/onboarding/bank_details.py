from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from schema.onboarding.bank_details import BankDetailsCreate, BankDetailsResponse
from services.bank_service import create_bank_details
from core.database import get_db
from utils.validators import validate_ifsc

router = APIRouter(prefix="/bank-details", tags=["Bank Details"])


@router.post("/", response_model=BankDetailsResponse)
async def submit_bank_details(
    data: BankDetailsCreate,
    db: AsyncSession = Depends(get_db),
):
    if not validate_ifsc(data.ifsc_code):
        raise HTTPException(status_code=400, detail="Invalid IFSC Code")

    return await create_bank_details(db, data)
