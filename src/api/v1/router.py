from fastapi import APIRouter
from src.api.v1.banners import banner_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(banner_router)
