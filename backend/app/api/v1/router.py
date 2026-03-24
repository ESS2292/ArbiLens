from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.billing import router as billing_router
from app.api.v1.endpoints.comparisons import router as comparisons_router
from app.api.v1.endpoints.documents import router as documents_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.users import router as users_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(documents_router, prefix="/documents", tags=["documents"])
router.include_router(reports_router, prefix="/reports", tags=["reports"])
router.include_router(comparisons_router, prefix="/comparisons", tags=["comparisons"])
router.include_router(billing_router, prefix="/billing", tags=["billing"])
