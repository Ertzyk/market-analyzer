import sys
import os

# 🔥 Najpierw dodajemy ścieżkę backendu do Pythona
BASE_DIR = os.path.dirname(os.path.dirname(__file__))   # .../market-analyzer/backend
sys.path.append(BASE_DIR)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 🔥 Teraz importy działają
from main import app
from db import Base, get_db

# Baza testowa (SQLite)
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Reset bazy testowej
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c