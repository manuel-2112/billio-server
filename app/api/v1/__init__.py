from fastapi import APIRouter

router = APIRouter(prefix="/v1")

from app.api.v1.auth import router as auth_router
from app.api.v1.public import router as public_router

router.include_router(auth_router)
router.include_router(public_router)
