from fastapi import APIRouter
from . import stages,candidates

router = APIRouter(tags=["Pipeline"])

router.include_router(stages.router)
router.include_router(candidates.router)

