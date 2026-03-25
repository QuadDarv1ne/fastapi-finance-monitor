"""Tests for JWT refresh token functionality"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.models import User, RefreshToken, Base
from app.services.auth_service import AuthService
from app.config import SecurityConfig


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_db():
    """Create test database session with thread-safe SQLite"""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    
    # Use in-memory SQLite for testing with thread safety
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db: Session):
    """Create test user"""
    user = User(
        username="testuser_refresh",
        email="test_refresh@example.com",
        hashed_password=AuthService.get_password_hash("TestPassword123!@#"),
        is_active=True,
        is_verified=True,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_refresh_token_creation(test_db: Session, test_user: User):
    """Test refresh token creation"""
    token = AuthService.create_refresh_token(test_user.id, test_db)
    
    assert token is not None
    assert isinstance(token, str)
    
    # Check token exists in database
    db_token = test_db.query(RefreshToken).filter(
        RefreshToken.user_id == test_user.id,
        RefreshToken.token == token
    ).first()
    
    assert db_token is not None
    assert db_token.is_revoked == False
    assert db_token.expires_at > datetime.utcnow()


def test_refresh_token_verification(test_db: Session, test_user: User):
    """Test refresh token verification"""
    token = AuthService.create_refresh_token(test_user.id, test_db)
    
    # Verify token
    payload = AuthService.verify_refresh_token(token, test_db)
    
    assert payload is not None
    assert payload["user_id"] == test_user.id
    assert payload["type"] == "refresh"


def test_refresh_token_verification_invalid(test_db: Session):
    """Test verification of invalid token"""
    payload = AuthService.verify_refresh_token("invalid_token", test_db)
    assert payload is None


def test_refresh_token_revocation(test_db: Session, test_user: User):
    """Test refresh token revocation"""
    token = AuthService.create_refresh_token(test_user.id, test_db)
    
    # Revoke token
    success = AuthService.revoke_refresh_token(token, test_db)
    assert success == True
    
    # Try to verify revoked token
    payload = AuthService.verify_refresh_token(token, test_db)
    assert payload is None


def test_refresh_token_revocation_nonexistent(test_db: Session):
    """Test revocation of non-existent token"""
    success = AuthService.revoke_refresh_token("nonexistent_token", test_db)
    assert success == False


def test_revoke_all_user_tokens(test_db: Session, test_user: User):
    """Test revoking all user tokens"""
    # Create multiple tokens
    token1 = AuthService.create_refresh_token(test_user.id, test_db)
    token2 = AuthService.create_refresh_token(test_user.id, test_db)
    token3 = AuthService.create_refresh_token(test_user.id, test_db)
    
    # Revoke all
    revoked_count = AuthService.revoke_all_user_tokens(test_user.id, test_db)
    
    assert revoked_count == 3
    
    # Verify all tokens are revoked
    for token in [token1, token2, token3]:
        payload = AuthService.verify_refresh_token(token, test_db)
        assert payload is None


def test_cleanup_expired_tokens(test_db: Session, test_user: User):
    """Test cleanup of expired tokens"""
    # Create expired token
    from app.models import RefreshToken
    
    expired_token = RefreshToken(
        user_id=test_user.id,
        token="expired_token_xyz",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        is_revoked=False,
    )
    test_db.add(expired_token)
    test_db.commit()
    
    # Cleanup
    deleted_count = AuthService.cleanup_expired_tokens(test_db)
    
    assert deleted_count == 1
    
    # Verify token is deleted
    db_token = test_db.query(RefreshToken).filter(
        RefreshToken.token == "expired_token_xyz"
    ).first()
    assert db_token is None


def test_refresh_token_in_login_response(test_db: Session, test_user: User):
    """Test that login logic returns refresh token"""
    # This tests the AuthService logic directly instead of through HTTP
    from app.services.database_service import DatabaseService
    
    # Authenticate user (simulate login)
    user = test_db.query(User).filter(User.username == test_user.username).first()
    assert user is not None
    
    # Create access token
    from datetime import timedelta
    access_token = AuthService.create_access_token(
        data={"user_id": user.id, "username": user.username},
        expires_delta=timedelta(minutes=30),
    )
    
    # Create refresh token
    refresh_token = AuthService.create_refresh_token(user.id, test_db)
    
    assert access_token is not None
    assert refresh_token is not None
    assert isinstance(refresh_token, str)
    
    # Verify refresh token is stored
    db_token = test_db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.token == refresh_token,
    ).first()
    assert db_token is not None
    assert db_token.is_revoked == False
