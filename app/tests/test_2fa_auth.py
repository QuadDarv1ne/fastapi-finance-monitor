"""Tests for 2FA TOTP authentication"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import User, Base
from app.services.auth_service import AuthService
from app.services.two_factor_auth_service import (
    TwoFactorAuthService,
    is_2fa_attempt_allowed,
    record_2fa_attempt,
    get_2fa_attempts,
)


@pytest.fixture
def test_db():
    """Create test database session with thread-safe SQLite"""
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
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
        username="testuser_2fa",
        email="test_2fa@example.com",
        hashed_password=AuthService.get_password_hash("TestPassword123!@#"),
        is_active=True,
        is_verified=True,
        is_2fa_enabled=False,
        totp_secret=None,
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_generate_secret():
    """Test TOTP secret generation"""
    secret = TwoFactorAuthService.generate_secret()
    
    assert secret is not None
    assert isinstance(secret, str)
    assert len(secret) == 32  # Base32 secret length


def test_generate_secret_uniqueness():
    """Test that generated secrets are unique"""
    secrets = [TwoFactorAuthService.generate_secret() for _ in range(10)]
    assert len(set(secrets)) == 10  # All secrets should be unique


def test_get_provisioning_uri(test_user: User):
    """Test provisioning URI generation"""
    secret = TwoFactorAuthService.generate_secret()
    uri = TwoFactorAuthService.get_provisioning_uri(
        username=test_user.username,
        email=test_user.email,
        secret=secret,
    )
    
    assert uri is not None
    assert uri.startswith("otpauth://totp/")
    # Email is URL encoded
    assert "test_2fa%40example.com" in uri or "FastAPI%20Finance%20Monitor" in uri
    assert "issuer=FastAPI%20Finance%20Monitor" in uri


def test_verify_otp_valid(test_user: User):
    """Test OTP verification with valid code"""
    secret = TwoFactorAuthService.generate_secret()
    
    # Get current OTP (for testing only)
    current_otp = TwoFactorAuthService.get_current_otp(secret)
    
    # Verify OTP
    is_valid = TwoFactorAuthService.verify_otp(secret, current_otp)
    assert is_valid == True


def test_verify_otp_invalid(test_user: User):
    """Test OTP verification with invalid code"""
    secret = TwoFactorAuthService.generate_secret()
    
    # Try invalid OTP
    is_valid = TwoFactorAuthService.verify_otp(secret, "000000")
    assert is_valid == False


def test_verify_otp_wrong_code(test_user: User):
    """Test OTP verification with wrong code"""
    secret = TwoFactorAuthService.generate_secret()
    
    # Try wrong OTP (not current, not previous, not next)
    is_valid = TwoFactorAuthService.verify_otp(secret, "123456")
    assert is_valid == False


def test_generate_backup_codes():
    """Test backup codes generation"""
    codes = TwoFactorAuthService.generate_backup_codes(count=10)
    
    assert len(codes) == 10
    assert all(isinstance(code, str) for code in codes)
    assert all(len(code) >= 6 for code in codes)  # At least 6 characters


def test_generate_backup_codes_unique():
    """Test that backup codes are unique"""
    codes = TwoFactorAuthService.generate_backup_codes(count=20)
    assert len(set(codes)) == 20  # All codes should be unique


def test_verify_backup_code_valid():
    """Test backup code verification with valid code"""
    codes = TwoFactorAuthService.generate_backup_codes(count=10)
    
    # Verify first code
    is_valid = TwoFactorAuthService.verify_backup_code(codes, codes[0])
    assert is_valid == True


def test_verify_backup_code_invalid():
    """Test backup code verification with invalid code"""
    codes = TwoFactorAuthService.generate_backup_codes(count=10)
    
    # Try invalid code
    is_valid = TwoFactorAuthService.verify_backup_code(codes, "INVALID")
    assert is_valid == False


def test_verify_backup_code_case_insensitive():
    """Test backup code verification is case insensitive"""
    codes = TwoFactorAuthService.generate_backup_codes(count=10)
    
    # Verify with lowercase
    is_valid = TwoFactorAuthService.verify_backup_code(codes, codes[0].lower())
    assert is_valid == True


def test_is_2fa_setup_required():
    """Test 2FA setup requirement check"""
    # 2FA enabled but no secret - setup required
    assert TwoFactorAuthService.is_2fa_setup_required(True, None) == True
    
    # 2FA enabled with secret - setup complete
    assert TwoFactorAuthService.is_2fa_setup_required(True, "SECRET123") == False
    
    # 2FA disabled - no setup required
    assert TwoFactorAuthService.is_2fa_setup_required(False, None) == False
    assert TwoFactorAuthService.is_2fa_setup_required(False, "SECRET123") == False


def test_2fa_rate_limiting(test_user: User):
    """Test 2FA rate limiting"""
    user_id = test_user.id
    
    # Clear any existing attempts
    from app.services.two_factor_auth_service import _2fa_attempts
    _2fa_attempts.clear()
    
    # Should allow first 5 attempts
    for i in range(5):
        assert is_2fa_attempt_allowed(user_id) == True
        record_2fa_attempt(user_id)
    
    # 6th attempt should be blocked
    assert is_2fa_attempt_allowed(user_id) == False
    
    # Check attempt count
    assert get_2fa_attempts(user_id) == 5


def test_2fa_rate_limiting_window(test_user: User):
    """Test 2FA rate limiting window"""
    user_id = test_user.id
    
    from app.services.two_factor_auth_service import _2fa_attempts
    from datetime import timedelta
    
    _2fa_attempts.clear()
    
    # Record attempt
    record_2fa_attempt(user_id)
    assert get_2fa_attempts(user_id) == 1
    
    # Simulate time passing (5 minutes + 1 second)
    # In real scenario, old attempts would be cleaned up
    # For testing, we just verify the cleanup logic works
    _2fa_attempts[str(user_id)] = [
        datetime.now(timezone.utc).timestamp() - 400  # 400 seconds ago (> 5 min)
    ]
    
    # Should be allowed after window expires
    assert is_2fa_attempt_allowed(user_id) == True


def test_get_current_otp():
    """Test getting current OTP (for testing)"""
    secret = TwoFactorAuthService.generate_secret()
    otp = TwoFactorAuthService.get_current_otp(secret)
    
    assert otp is not None
    assert isinstance(otp, str)
    assert len(otp) == 6
    assert otp.isdigit()


def test_otp_verification_with_window(test_user: User):
    """Test OTP verification with time window"""
    secret = TwoFactorAuthService.generate_secret()
    
    # Get current OTP
    current_otp = TwoFactorAuthService.get_current_otp(secret)
    
    # Should verify with default window (1 period before/after)
    is_valid = TwoFactorAuthService.verify_otp(secret, current_otp, window=1)
    assert is_valid == True


def test_qr_code_generation(test_user: User):
    """Test QR code generation"""
    secret = TwoFactorAuthService.generate_secret()
    
    qr_data = TwoFactorAuthService.generate_qr_code_data(
        username=test_user.username,
        email=test_user.email,
        secret=secret,
    )
    
    # QR code should be either data URI or otpauth URI
    assert qr_data is not None
    assert isinstance(qr_data, str)
    # If qrcode library is installed, should be base64 PNG
    # Otherwise, should be otpauth URI
    assert qr_data.startswith("data:image/png;base64,") or qr_data.startswith("otpauth://")
