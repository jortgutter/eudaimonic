"""Database setup and session management"""
import os

from sqlalchemy import inspect
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()

# Create database directory if using SQLite
if "sqlite" in settings.SQLALCHEMY_DATABASE_URL:
    db_dir = os.path.dirname(settings.SQLALCHEMY_DATABASE_URL.replace("sqlite:///", ""))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

# Database setup with connection pooling
connect_args = {}
if "sqlite" in settings.SQLALCHEMY_DATABASE_URL:
    connect_args = {"check_same_thread": False}
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URL,
        connect_args=connect_args,
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        settings.SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )

def SessionLocal() -> Session:
    return Session(engine)

Base = SQLModel


def sync_sqlite_schema() -> None:
    """Lightweight schema sync for local development SQLite databases."""
    if "sqlite" not in settings.SQLALCHEMY_DATABASE_URL:
        return

    inspector = inspect(engine)
    if not inspector.has_table("movies"):
        return


def get_db():
    """Dependency for database session injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
