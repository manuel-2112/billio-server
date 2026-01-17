from fastapi import APIRouter

router = APIRouter(prefix="/v1")

from app.api.v1.auth import router as auth_router
from app.api.v1.public import router as public_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.checkout import router as checkout_router
from app.api.v1.webhooks import router as webhooks_router

router.include_router(auth_router)
router.include_router(public_router)
router.include_router(dashboard_router)
router.include_router(checkout_router)
router.include_router(webhooks_router)