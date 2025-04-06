from fastapi import APIRouter

from app.api.v1.endpoints import auth, admin, payments, merchants, reports, sms

api_router = APIRouter()

# Include all API endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(reports.router, prefix="/reports", tags=["merchant reports"])
api_router.include_router(merchants.router, prefix="/merchants", tags=["merchant profile"])
api_router.include_router(sms.router, prefix="/sms", tags=["sms processing"])