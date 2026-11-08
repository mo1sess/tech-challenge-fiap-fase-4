from fastapi import APIRouter

from app.api.routes import clinical, demo, media, patients


api_router = APIRouter()
api_router.include_router(patients.router)
api_router.include_router(clinical.router)
api_router.include_router(media.router)
api_router.include_router(demo.router)

