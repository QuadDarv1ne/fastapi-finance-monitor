"""Tests for user registration functionality"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_user_registration():
    """Test successful user registration"""
    # Import models to ensure they're registered with the Base
    from app import models
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    response = client.post("/api/users/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "User registered successfully"
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "user_id" in data

def test_user_registration_duplicate_username():
    """Test registration with duplicate username"""
    # Import models to ensure they're registered with the Base
    from app import models
    
    # Create tables if not exists
    Base.metadata.create_all(bind=engine)
    
    # First registration
    client.post("/api/users/register", json={
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "TestPass123!"
    })
    
    # Second registration with same username
    response = client.post("/api/users/register", json={
        "username": "testuser2",
        "email": "test3@example.com",
        "password": "TestPass123!"
    })
    
    assert response.status_code == 409
    data = response.json()
    assert data["detail"] == "Username already registered"

def test_user_registration_duplicate_email():
    """Test registration with duplicate email"""
    # Import models to ensure they're registered with the Base
    from app import models
    
    # Create tables if not exists
    Base.metadata.create_all(bind=engine)
    
    # First registration
    client.post("/api/users/register", json={
        "username": "testuser3",
        "email": "test4@example.com",
        "password": "TestPass123!"
    })
    
    # Second registration with same email
    response = client.post("/api/users/register", json={
        "username": "testuser4",
        "email": "test4@example.com",
        "password": "TestPass123!"
    })
    
    assert response.status_code == 409
    data = response.json()
    assert data["detail"] == "Email already registered"

def test_user_registration_invalid_password():
    """Test registration with invalid password"""
    # Import models to ensure they're registered with the Base
    from app import models
    
    # Create tables if not exists
    Base.metadata.create_all(bind=engine)
    
    response = client.post("/api/users/register", json={
        "username": "testuser5",
        "email": "test5@example.com",
        "password": "weak"
    })
    
    assert response.status_code == 400
    data = response.json()
    assert "Password must be at least 8 characters long" in data["detail"]

def test_user_registration_invalid_email():
    """Test registration with invalid email"""
    # Import models to ensure they're registered with the Base
    from app import models
    
    # Create tables if not exists
    Base.metadata.create_all(bind=engine)
    
    response = client.post("/api/users/register", json={
        "username": "testuser6",
        "email": "invalid-email",
        "password": "TestPass123!"
    })
    
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Invalid email format."

def test_user_registration_invalid_username():
    """Test registration with invalid username"""
    # Import models to ensure they're registered with the Base
    from app import models
    
    # Create tables if not exists
    Base.metadata.create_all(bind=engine)
    
    response = client.post("/api/users/register", json={
        "username": "ab",
        "email": "test7@example.com",
        "password": "TestPass123!"
    })
    
    assert response.status_code == 400
    data = response.json()
    assert "Invalid username format" in data["detail"]