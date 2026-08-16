from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.router import api_v1_router
from src.api.v1.banners import banner_router
from src.db.database import init_db


def create_app() -> FastAPI:
    init_db()

    app = FastAPI(
        title="Gacha Banner Tracker API",
        description="API for tracking gacha banners across multiple games (Genshin Impact, Honkai: Star Rail, etc.)",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_v1_router, prefix="/api")
    app.include_router(banner_router)

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "ok"}

    return app


app = create_app()
