"""FastAPI application entry point"""
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.config import get_settings
from backend.app.api.v1 import router as api_v1_router
from backend.app.db.database import engine, Base, sync_sqlite_schema

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)
sync_sqlite_schema()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Movie Recommendation System API",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    api_v1_router,
    prefix=settings.API_V1_STR,
)


@app.get("/", summary="Root Endpoint")
def root():
    return {
        "message": "Welcome to the Movie Recommendation API",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    print('starting app...')

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )