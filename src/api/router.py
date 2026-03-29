# API: Main router that combines all endpoint routers

from fastapi import APIRouter

from src.api.health import router as health_router
from src.api.web import router as web_router
from src.auth.router import router as auth_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(auth_router)  # /auth/register, /auth/login, /auth/me
api_router.include_router(web_router)
