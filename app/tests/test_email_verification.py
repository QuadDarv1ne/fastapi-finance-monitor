"""Tests for email verification functionality"""

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

def test_email_verification():
    """Test email verification flow"""
    # First register a user
    register_response = client.post("/api/users/register", json={
        "username": "testverify",
        "email": "testverify@example.com",
        "password": "TestPass123!"
    })
    
    assert register_response.status_code == 201
    
    # Try to login before verification (should fail)
    login_response = client.post("/api/users/login", data={
        "username": "testverify",
        "password": "TestPass123!"
    })
    
    assert login_response.status_code == 401
    data = login_response.json()
    assert "verify your email" in data["detail"]
    
    # TODO: Test email verification endpoint
    # This would require mocking the email sending and extracting the token

def test_resend_verification():
    """Test resending verification email"""
    # First register a user
    client.post("/api/users/register", json={
        "username": "testresend",
        "email": "testresend@example.com",
        "password": "TestPass123!"
    })
    
    # Resend verification
    response = client.post("/api/users/resend-verification", json={
        "email": "testresend@example.com"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Verification email sent successfully"

def test_resend_verification_user_not_found():
    """Test resending verification for non-existent user"""
    response = client.post("/api/users/resend-verification", json={
        "email": "nonexistent@example.com"
    })
    
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"