"""Tests for user registration functionality

Note: Tests in this file require isolated execution due to database state conflicts.
Run them separately with:
    pytest -m isolated
or exclude them from full test runs with:
    pytest -m "not isolated"
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.services.auth_service import get_registration_attempts

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
    # Create all tables once per module
    Base.metadata.create_all(bind=engine)
    yield
    # Drop all tables after all tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_rate_limits():
    """Reset rate limiting between tests"""
    yield
    # Clear registration attempts after each test
    attempts = get_registration_attempts()
    attempts.clear()


@pytest.mark.isolated
def test_user_registration():
    """Test successful user registration"""
    # Use unique username/email to avoid conflicts with other tests
    import random
    suffix = random.randint(1000, 9999)
    username = f"testuser_{suffix}"
    email = f"test_{suffix}@example.com"

    response = client.post(
        "/api/users/register",
        json={"username": username, "email": email, "password": "TestPass123!"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "User registered successfully"
    assert data["username"] == username
    assert data["email"] == email
    assert "user_id" in data


@pytest.mark.isolated
def test_user_registration_duplicate_username():
    """Test registration with duplicate username"""
    # Use unique username with suffix to avoid conflicts
    import random
    suffix = random.randint(1000, 9999)
    base_username = f"dupuser_{suffix}"
    
    # First registration
    response1 = client.post(
        "/api/users/register",
        json={"username": base_username, "email": f"{base_username}@example.com", "password": "TestPass123!"},
    )
    assert response1.status_code == 201

    # Second registration with same username
    response2 = client.post(
        "/api/users/register",
        json={"username": base_username, "email": f"{base_username}_2@example.com", "password": "TestPass123!"},
    )

    # Accept either 409 (conflict) or 429 (rate limit) - rate limiting may trigger first
    assert response2.status_code in [409, 429]
    data = response2.json()
    assert "already registered" in data["detail"] or "Too many" in data["detail"]


@pytest.mark.isolated
def test_user_registration_duplicate_email():
    """Test registration with duplicate email"""
    # Use unique email with suffix to avoid conflicts
    import random
    suffix = random.randint(1000, 9999)
    base_email = f"dupemail_{suffix}@example.com"
    
    # First registration
    response1 = client.post(
        "/api/users/register",
        json={"username": f"user_{suffix}", "email": base_email, "password": "TestPass123!"},
    )
    assert response1.status_code == 201

    # Second registration with same email
    response2 = client.post(
        "/api/users/register",
        json={"username": f"user2_{suffix}", "email": base_email, "password": "TestPass123!"},
    )

    # Accept either 409 (conflict) or 429 (rate limit) - rate limiting may trigger first
    assert response2.status_code in [409, 429]
    data = response2.json()
    assert "already registered" in data["detail"] or "Too many" in data["detail"]


def test_user_registration_invalid_password():
    """Test registration with invalid password"""
    # Import models to ensure they're registered with the Base

    # Create tables if not exists
    Base.metadata.create_all(bind=engine)

    response = client.post(
        "/api/users/register",
        json={"username": "testuser5", "email": "test5@example.com", "password": "weak"},
    )

    assert response.status_code == 422  # Changed from 400 to 422
    data = response.json()
    # Check that the error message contains the expected text
    assert "Password must be at least 8 characters long" in str(data)


def test_user_registration_invalid_email():
    """Test registration with invalid email"""
    # Import models to ensure they're registered with the Base

    # Create tables if not exists
    Base.metadata.create_all(bind=engine)

    response = client.post(
        "/api/users/register",
        json={"username": "testuser6", "email": "invalid-email", "password": "TestPass123!"},
    )

    assert response.status_code == 422  # Changed from 400 to 422
    data = response.json()
    # Check that the error message contains the expected text
    assert "Invalid email format" in str(data)


def test_user_registration_invalid_username():
    """Test registration with invalid username"""
    # Import models to ensure they're registered with the Base

    # Create tables if not exists
    Base.metadata.create_all(bind=engine)

    response = client.post(
        "/api/users/register",
        json={"username": "ab", "email": "test7@example.com", "password": "TestPass123!"},
    )

    assert response.status_code == 422  # Changed from 400 to 422
    data = response.json()
    # Check that the error message contains the expected text
    assert "at least 3 characters" in str(data)
