from fastapi import APIRouter
from . import stages,candidates

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])

router.include_router(stages.router)
router.include_router(candidates.router)

