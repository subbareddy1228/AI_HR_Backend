from fastapi import APIRouter
from .offer_template_router import router as template_router
from .offer_tracking_router import router as tracking_router

# Main router for offers
router = APIRouter(prefix="/api/offers", tags=["Offers"])

# Include sub-routers
router.include_router(template_router)
router.include_router(tracking_router)

