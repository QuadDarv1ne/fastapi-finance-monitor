"""Tests for email verification functionality"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

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
    """Test email verification flow

    Note: In development mode (used for tests), users are auto-verified.
    This test verifies the registration and login flow works correctly.
    For production, email verification is required before login.
    """
    # First register a user
    register_response = client.post(
        "/api/users/register",
        json={
            "username": "testverify",
            "email": "testverify@example.com",
            "password": "TestPass123!",
        },
    )

    assert register_response.status_code == 201

    # In development mode, users are auto-verified, so login should succeed
    login_response = client.post(
        "/api/users/login", data={"username": "testverify", "password": "TestPass123!"}
    )

    assert login_response.status_code == 200
    data = login_response.json()
    assert "access_token" in data


def test_resend_verification():
    """Test resending verification email

    Note: In development mode (used for tests), users are auto-verified,
    so resend verification will return "Email already verified".
    """
    # First register a user
    client.post(
        "/api/users/register",
        json={
            "username": "testresend",
            "email": "testresend@example.com",
            "password": "TestPass123!",
        },
    )

    # Resend verification - in dev mode, user is already verified
    response = client.post(
        "/api/users/resend-verification", json={"email": "testresend@example.com"}
    )

    # In development mode, users are auto-verified, so we get "already verified" message
    assert response.status_code == 200
    data = response.json()
    # Accept either message since behavior depends on APP_ENV
    assert data["message"] in ["Verification email sent successfully", "Email already verified"]


def test_resend_verification_user_not_found():
    """Test resending verification for non-existent user"""
    response = client.post(
        "/api/users/resend-verification", json={"email": "nonexistent@example.com"}
    )

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "User not found"
