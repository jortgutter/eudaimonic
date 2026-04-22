"""Backend tests configuration and fixtures"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from main import app
from app.db.database import Base, get_db


# Use in-memory SQLite for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


def override_get_db():
    """Database dependency override for tests"""
    try:
        db = Session(engine)
        yield db
    finally:
        db.close()


@pytest.fixture()
def db():
    """Create test database and tables"""
    SQLModel.metadata.create_all(bind=engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    """Create test FastAPI client"""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
