from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.video_projects import router as video_projects_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(video_projects_router)
