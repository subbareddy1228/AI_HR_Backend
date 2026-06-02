from fastapi import APIRouter
from . import create, update, delete, search, list

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

# include routers from each file
router.include_router(create.router)
router.include_router(update.router)
router.include_router(delete.router)
router.include_router(search.router)
router.include_router(list.router)
