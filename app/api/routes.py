"""API routes for the FastAPI Finance Monitor application"""

import asyncio
import csv
import io
import logging
import os
import re
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db

# Import custom exceptions
from app.exceptions.custom_exceptions import (
    AuthenticationError,
    CacheError,
    DatabaseError,
    DataFetchError,
    FinanceMonitorError,
    NetworkError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

# Import request/response models
from app.models import (
    AssetAddRequest,
    EmailVerificationRequest,
    PortfolioCreateRequest,
    TwoFactorAuthDisableRequest,
    TwoFactorAuthEnableRequest,
    TwoFactorAuthResponse,
    TwoFactorAuthVerifyRequest,
    TwoFactorAuthVerifyResponse,
    UserRegistrationRequest,
)
from app.services.auth_service import AuthService, get_current_user
from app.services.cache_service import get_cache_service
from app.services.data_fetcher import DataFetcher
from app.services.database_service import DatabaseService
from app.services.monitoring_service import get_monitoring_service
from app.services.redis_cache_service import get_redis_cache_service
from app.services.two_factor_auth_service import (
    TwoFactorAuthService,
    is_2fa_attempt_allowed,
    record_2fa_attempt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Singleton DataFetcher instance for reuse across requests
_data_fetcher_instance = None


def get_data_fetcher():
    """Get or create DataFetcher singleton instance"""
    global _data_fetcher_instance
    if _data_fetcher_instance is None:
        _data_fetcher_instance = DataFetcher()
    return _data_fetcher_instance


def _convert_period_to_days(period: str) -> int:
    """Convert period string (1d, 5d, 1mo, etc.) to number of days"""
    period_map = {
        "1d": 1,
        "5d": 5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "10y": 3650,
        "ytd": 365,
        "max": 3650,
    }
    return period_map.get(period, 30)  # Default to 30 days if unknown


_SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9._\-]{1,30}$")


def _validate_symbol(symbol: str) -> str:
    """Validate and normalize an asset symbol.

    Symbols may contain letters, digits, dots, underscores and dashes
    (max 30 chars).  Returns the upper-cased symbol or raises ValueError.
    """
    symbol = symbol.strip()
    if not _SYMBOL_PATTERN.match(symbol):
        raise ValueError(
            "Invalid symbol: only letters, digits, '.', '_', '-' allowed (max 30 chars)"
        )
    return symbol.upper()


def _sanitize_filename(symbol: str) -> str:
    """Sanitize a symbol for use in a Content-Disposition filename."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", symbol)


def _convert_days_to_yf_period(days: int) -> str:
    """Convert number of days to the nearest yfinance period string."""
    period_map = [
        (1, "1d"),
        (5, "5d"),
        (30, "1mo"),
        (90, "3mo"),
        (180, "6mo"),
        (365, "1y"),
        (730, "2y"),
        (1825, "5y"),
        (3650, "10y"),
    ]
    for threshold, label in period_map:
        if days <= threshold:
            return label
    return "max"


def _convert_interval_to_yf(interval: str) -> str:
    """Convert human-readable interval to yfinance interval string."""
    interval_map = {
        "hourly": "1h",
        "daily": "1d",
        "weekly": "1wk",
    }
    return interval_map.get(interval, "1d")


# Health check endpoint
@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Basic health check endpoint"""
    # Initialize variables with default values
    cache_status = "unhealthy"
    redis_status = "unhealthy"

    try:
        # Check database connection
        db_service = DatabaseService(db)
        db_service.get_user_by_username("admin")  # This will return None but test the connection

        # Check cache service
        cache_service = get_cache_service()
        try:
            cache_stats = await cache_service.get_stats()
            cache_status = "healthy" if cache_stats else "unhealthy"
        except Exception:
            cache_status = "unhealthy"

        # Check Redis connection
        redis_service = get_redis_cache_service()
        try:
            redis_stats = await redis_service.get_stats()
            redis_status = "healthy" if redis_stats else "unhealthy"
        except Exception:
            redis_status = "unhealthy"

        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "services": {"database": "healthy", "cache": cache_status, "redis": redis_status},
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is unhealthy"
        )


# Detailed health check endpoint
@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check endpoint"""
    # Initialize variables with default values
    cache_stats = None
    redis_stats = None
    db_status = "healthy"
    cache_status = "healthy"
    redis_status = "healthy"

    try:
        # Check database connection
        db_service = DatabaseService(db)
        try:
            # Try to perform a simple database operation
            db_service.get_user_by_username(
                "admin"
            )  # This will return None but test the connection
            db_status = "healthy"
        except DatabaseError as e:
            db_status = f"unhealthy: {e!s}"
        except Exception as e:
            db_status = f"unhealthy: {e!s}"

        # Check cache service
        cache_service = get_cache_service()
        try:
            cache_stats = await cache_service.get_stats()
            cache_status = "healthy" if cache_stats else "unhealthy"
        except CacheError as e:
            cache_status = f"unhealthy: {e!s}"
        except Exception as e:
            cache_status = f"unhealthy: {e!s}"

        # Check Redis connection
        redis_service = get_redis_cache_service()
        try:
            redis_stats = await redis_service.get_stats()
            redis_status = "healthy" if redis_stats else "unhealthy"
        except CacheError as e:
            redis_status = f"unhealthy: {e!s}"
        except Exception as e:
            redis_status = f"unhealthy: {e!s}"

        # Get monitoring stats
        monitoring_service = get_monitoring_service()
        monitoring_stats = monitoring_service.get_all_metrics()

        return {
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "services": {
                "database": db_status,
                "cache": cache_status,
                "redis": redis_status,
                "monitoring": "healthy",
            },
            "stats": {"cache": cache_stats, "redis": redis_stats, "monitoring": monitoring_stats},
        }
    except FinanceMonitorError as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is unhealthy"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service is unhealthy"
        )


# User registration endpoint
@router.post("/users/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegistrationRequest, request: Request, db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        username = user_data.username
        email = user_data.email
        password = user_data.password

        logger.info(f"Attempting to register user: {username}, email: {email}")

        # Rate limiting check for registration
        client_ip = (
            request.client.host if hasattr(request, "client") and request.client else "unknown"
        )
        if not AuthService.is_registration_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later.",
            )

        # Check if user already exists
        db_service = DatabaseService(db)
        existing_user = db_service.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already registered"
            )

        existing_email = db_service.get_user_by_email(email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
            )

        # Record registration attempt
        AuthService.record_registration_attempt(client_ip)

        # Create new user
        logger.info(f"Creating user: {username}")
        new_user = db_service.create_user(username, email, password)
        logger.info(f"User created successfully: {new_user.id}")

        return {
            "message": "User registered successfully",
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
        }
    except HTTPException:
        raise
    except ValidationError as e:
        # Handle validation errors
        logger.error(f"Validation error during registration: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DatabaseError as e:
        logger.error(f"Database error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user. Please try again later.",
        )


# User login endpoint
@router.post("/users/login")
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    otp: str | None = None,  # Optional OTP for 2FA
    db: Session = Depends(get_db),
):
    """Login user and return access token

    If 2FA is enabled:
    1. First call with username/password only
    2. If 2FA required, response will include 'requires_2fa': true
    3. Second call with username/password + otp to complete login
    """
    try:
        # Authenticate user
        db_service = DatabaseService(db)
        user = db_service.authenticate_user(form_data.username, form_data.password)

        if not user:
            # Log failed login attempts for security monitoring
            logger.warning(f"Failed login attempt for username: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user has verified their email
        # For backward compatibility, default to True if is_verified attribute doesn't exist
        is_verified = getattr(user, "is_verified", True)
        if not is_verified:
            logger.warning(f"Login attempt for unverified user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your email address before logging in",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if 2FA is enabled
        is_2fa_enabled = getattr(user, "is_2fa_enabled", False)

        if is_2fa_enabled:
            # If no OTP provided, return 2FA required response
            if not otp:
                logger.info(f"2FA required for user {user.username} (ID: {user.id})")
                return {
                    "requires_2fa": True,
                    "message": "2FA is enabled. Please provide OTP code.",
                    "user_id": user.id,
                    "username": user.username,
                }

            # Verify OTP
            totp_secret = getattr(user, "totp_secret", None)
            if not totp_secret:
                logger.error(f"2FA enabled but no secret found for user {user.username}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="2FA configuration error. Please contact support.",
                )

            is_valid = TwoFactorAuthService.verify_otp(totp_secret, otp)
            if not is_valid:
                logger.warning(f"Invalid 2FA OTP for user {user.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid 2FA code",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            logger.info(f"2FA verified for user {user.username} (ID: {user.id})")

        # Create access token
        access_token_expires = timedelta(
            minutes=30
        )  # Use hardcoded value instead of class attribute
        access_token = AuthService.create_access_token(
            data={"user_id": user.id, "username": user.username}, expires_delta=access_token_expires
        )

        # Create refresh token
        refresh_token = AuthService.create_refresh_token(user.id, db)

        # Log successful login
        logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": access_token_expires.total_seconds(),
            "user_id": user.id,
            "username": user.username,
            "requires_2fa": False,
        }
    except HTTPException:
        raise
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging in user. Please try again later.",
        )


# Email verification endpoint
@router.post("/users/verify-email")
async def verify_email(verification_data: EmailVerificationRequest, db: Session = Depends(get_db)):
    """Verify user email address"""
    try:
        # Verify the token
        email = AuthService.verify_email_verification_token(verification_data.token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Find user by email
        db_service = DatabaseService(db)
        user = db_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Update user verification status
        user.is_verified = True
        db.commit()
        db.refresh(user)

        logger.info(f"User {user.username} (ID: {user.id}) verified their email address")

        return {
            "message": "Email verified successfully",
            "user_id": user.id,
            "username": user.username,
        }
    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying email. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying email. Please try again later.",
        )


@router.post("/users/resend-verification")
async def resend_verification(request: dict, db: Session = Depends(get_db)):
    """Resend email verification email"""
    try:
        email = request.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")

        # Find user by email
        db_service = DatabaseService(db)
        user = db_service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check if already verified
        if getattr(user, "is_verified", True):
            return {"message": "Email already verified"}

        # Generate verification token
        token = AuthService.generate_email_verification_token(email)

        # In a real implementation, send email with token
        # For now, just log it
        logger.info(f"Verification token for {email}: {token}")

        return {"message": "Verification email sent successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resending verification email. Please try again later.",
        )


# Refresh token endpoint
@router.post("/users/refresh")
async def refresh_access_token(request: dict, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    try:
        refresh_token = request.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required",
            )

        # Verify refresh token
        payload = AuthService.verify_refresh_token(refresh_token, db)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("user_id")

        # Get user from database
        db_service = DatabaseService(db)
        user = db_service.get_user(int(user_id)) if user_id is not None else None

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create new access token
        access_token_expires = timedelta(minutes=30)
        access_token = AuthService.create_access_token(
            data={"user_id": user.id, "username": user.username},
            expires_delta=access_token_expires,
        )

        logger.info(f"Access token refreshed for user {user.username} (ID: {user.id})")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": access_token_expires.total_seconds(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error refreshing access token. Please try again later.",
        )


# Logout endpoint
@router.post("/users/logout")
async def logout_user(
    request: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout user by revoking refresh token"""
    try:
        refresh_token = request.get("refresh_token")

        if refresh_token:
            # Revoke specific token
            AuthService.revoke_refresh_token(refresh_token, db)
            logger.info(
                f"User {current_user['username']} (ID: {current_user['user_id']}) logged out"
            )
        else:
            # Revoke all tokens (logout from all devices)
            revoked_count = AuthService.revoke_all_user_tokens(current_user["user_id"], db)
            logger.info(
                f"User {current_user['username']} (ID: {current_user['user_id']}) "
                f"logged out from all devices ({revoked_count} tokens revoked)"
            )

        return {"message": "Logged out successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging out user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging out user. Please try again later.",
        )


# 2FA Endpoints
@router.post("/users/2fa/enable", response_model=TwoFactorAuthResponse)
async def enable_2fa(
    request: TwoFactorAuthEnableRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable 2FA for current user

    Step 1: Generate secret and QR code
    Step 2: User scans QR code with authenticator app
    Step 3: User verifies with OTP (call /users/2fa/verify)
    """
    try:
        # Verify password first
        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Verify password
        if not AuthService.verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password",
            )

        # Re-enabling over an active 2FA setup would silently invalidate the
        # existing secret and lock the user out - require disable first.
        if user.is_2fa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is already enabled. Disable it before re-configuring.",
            )

        # Generate new TOTP secret
        secret = TwoFactorAuthService.generate_secret()

        # Generate QR code
        qr_code = TwoFactorAuthService.generate_qr_code_data(
            username=user.username,
            email=user.email,
            secret=secret,
        )

        # Generate backup codes
        backup_codes = TwoFactorAuthService.generate_backup_codes(count=10)

        # Store secret temporarily (will be activated after verification)
        # For security, we store it only after OTP verification
        user.totp_secret = secret
        user.is_2fa_enabled = False  # Will be enabled after verification
        db.commit()

        logger.info(f"2FA setup initiated for user {user.username} (ID: {user.id})")

        return TwoFactorAuthResponse(
            is_enabled=False,
            secret=secret,
            qr_code=qr_code,
            backup_codes=backup_codes,
            message="Scan QR code with authenticator app and verify with OTP",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling 2FA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error enabling 2FA. Please try again later.",
        )


@router.post("/users/2fa/verify", response_model=TwoFactorAuthVerifyResponse)
async def verify_2fa(
    request: TwoFactorAuthVerifyRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify 2FA setup or login

    For setup: Activates 2FA after scanning QR code
    For login: Returns new access token if OTP is valid
    """
    try:
        # Rate limiting check
        if not is_2fa_attempt_allowed(current_user["user_id"]):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many 2FA attempts. Please try again in 5 minutes.",
            )

        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check if user has 2FA secret
        if not user.totp_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA not set up. Call /users/2fa/enable first.",
            )

        # Verify OTP
        is_valid = TwoFactorAuthService.verify_otp(user.totp_secret or "", request.otp)

        if not is_valid:
            # Only failed attempts count toward the rate limit, so legitimate
            # users are never locked out by successful verifications.
            record_2fa_attempt(current_user["user_id"])
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP code",
            )

        # If 2FA was not enabled yet, enable it now
        if not user.is_2fa_enabled:
            user.is_2fa_enabled = True
            db.commit()
            logger.info(f"2FA enabled for user {user.username} (ID: {user.id})")

            return TwoFactorAuthVerifyResponse(
                success=True,
                message="2FA enabled successfully",
            )

        # If 2FA already enabled, this is a login verification
        # Create new access token
        access_token_expires = timedelta(minutes=30)
        access_token = AuthService.create_access_token(
            data={"user_id": user.id, "username": user.username},
            expires_delta=access_token_expires,
        )

        logger.info(f"2FA verified for user {user.username} (ID: {user.id})")

        return TwoFactorAuthVerifyResponse(
            success=True,
            message="2FA verified successfully",
            access_token=access_token,
            token_type="bearer",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying 2FA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying 2FA. Please try again later.",
        )


@router.post("/users/2fa/disable")
async def disable_2fa(
    request: TwoFactorAuthDisableRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disable 2FA for current user"""
    try:
        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check if 2FA is enabled
        if not user.is_2fa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="2FA is not enabled",
            )

        # Verify OTP
        is_valid = TwoFactorAuthService.verify_otp(user.totp_secret or "", request.otp)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid OTP code",
            )

        # Disable 2FA
        user.is_2fa_enabled = False
        user.totp_secret = None
        db.commit()

        logger.info(f"2FA disabled for user {user.username} (ID: {user.id})")

        return {"message": "2FA disabled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling 2FA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error disabling 2FA. Please try again later.",
        )


@router.get("/users/2fa/status")
async def get_2fa_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get 2FA status for current user"""
    try:
        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return {
            "is_2fa_enabled": user.is_2fa_enabled,
            "is_setup_complete": user.is_2fa_enabled and user.totp_secret is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting 2FA status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving 2FA status. Please try again later.",
        )


# Get user profile endpoint
@router.get("/users/profile")
async def get_user_profile(
    current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get current user profile"""
    try:
        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Handle the created_at field properly
        created_at_value = None
        if hasattr(user, "created_at") and user.created_at is not None:
            created_at_value = user.created_at.isoformat()

        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_verified": getattr(user, "is_verified", True),
            "created_at": created_at_value,
        }
    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user profile. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user profile. Please try again later.",
        )


# Telegram connection endpoints
@router.get("/telegram/connect")
async def get_telegram_connect_link(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Telegram bot connection link"""
    try:
        bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "finance_monitor_bot")
        import base64
        import hashlib
        import secrets

        from app.models import User

        token = secrets.token_urlsafe(32)

        user_token = base64.urlsafe_b64encode(
            f"{current_user['user_id']}:{token}".encode()
        ).decode()

        # Store a hash of the token so it can be validated on /start
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user = db.query(User).filter(User.id == current_user["user_id"]).first()
        if user:
            user.telegram_connect_token_hash = token_hash
            db.commit()
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        connect_link = f"https://t.me/{bot_username}?start={user_token}"

        return {
            "connect_link": connect_link,
            "bot_username": bot_username,
            "instructions": "Нажмите на ссылку и отправьте команду /start в Telegram боте",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating Telegram connect link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating connection link. Please try again later.",
        )


@router.get("/telegram/status")
async def get_telegram_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Telegram connection status for current user"""
    try:
        from app.models import TelegramConnection

        connection = (
            db.query(TelegramConnection)
            .filter(
                TelegramConnection.user_id == current_user["user_id"],
                TelegramConnection.is_active,
            )
            .first()
        )

        if connection:
            return {
                "connected": True,
                "telegram_id": connection.telegram_id,
                "telegram_username": connection.telegram_username,
                "connected_at": connection.connected_at.isoformat(),
                "last_notification_at": (
                    connection.last_notification_at.isoformat()
                    if connection.last_notification_at
                    else None
                ),
            }
        else:
            return {
                "connected": False,
                "message": "Telegram not connected",
            }
    except Exception as e:
        logger.error(f"Error getting Telegram status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving Telegram status. Please try again later.",
        )


@router.post("/telegram/disconnect")
async def disconnect_telegram(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect Telegram from user account"""
    try:
        from app.models import TelegramConnection

        connection = (
            db.query(TelegramConnection)
            .filter(TelegramConnection.user_id == current_user["user_id"])
            .first()
        )

        if connection:
            connection.is_active = False
            db.commit()
            logger.info(f"Telegram disconnected for user {current_user['user_id']}")
            return {"message": "Telegram disconnected successfully"}
        else:
            return {"message": "Telegram was not connected"}
    except Exception as e:
        logger.error(f"Error disconnecting Telegram: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error disconnecting Telegram. Please try again later.",
        )


@router.post("/telegram/test")
async def send_test_telegram_notification(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send test Telegram notification"""
    try:
        from app.models import TelegramConnection
        from app.services.telegram_service import get_telegram_service

        connection = (
            db.query(TelegramConnection)
            .filter(
                TelegramConnection.user_id == current_user["user_id"],
                TelegramConnection.is_active,
            )
            .first()
        )

        if not connection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram not connected. Please connect first.",
            )

        telegram_service = get_telegram_service()
        success = await telegram_service.send_message(
            connection.telegram_id,
            "✅ <b>Тестовое уведомление</b>\n\n"
            "Telegram уведомления работают корректно!\n\n"
            "<i>FastAPI Finance Monitor</i>",
        )

        if success:
            return {"message": "Test notification sent successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test notification",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test Telegram notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending test notification. Please try again later.",
        )


# Get market data endpoint
@router.get("/market-data/{symbol}")
async def get_market_data(symbol: str, period: str = "1d", interval: str = "5m"):
    """Get market data for a specific symbol"""
    try:
        data_fetcher = get_data_fetcher()

        # Determine asset type based on symbol
        if symbol.lower() in ["bitcoin", "ethereum", "solana", "litecoin", "cardano"]:
            data = await data_fetcher.get_crypto_data(symbol)
        else:
            data = await data_fetcher.get_stock_data(symbol, period, interval)

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"No data found for symbol: {symbol}"
            )

        return data
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    except TimeoutError as e:
        logger.error(f"Timeout error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout fetching data for {symbol}. Try again later.",
        )
    except NetworkError as e:
        logger.error(f"Network error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network error fetching data for {symbol}. Try again later.",
        )
    except DataFetchError as e:
        logger.error(f"Data fetch error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching data for {symbol}. Try again later.",
        )
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving data for {symbol}. Please try again later.",
        )


# Get multiple market data endpoint
@router.post("/market-data/batch")
async def get_batch_market_data(symbols: list[str]):
    """Get market data for multiple symbols"""
    try:
        data_fetcher = get_data_fetcher()

        # Prepare assets list
        assets = []
        for symbol in symbols:
            asset_type = (
                "crypto"
                if symbol.lower() in ["bitcoin", "ethereum", "solana", "litecoin", "cardano"]
                else "stock"
            )
            assets.append({"symbol": symbol, "name": symbol, "type": asset_type})

        # Fetch data for all assets concurrently
        data = await data_fetcher.get_multiple_assets(assets)

        return {"data": data, "count": len(data)}
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
    except TimeoutError as e:
        logger.error(f"Timeout error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Timeout fetching batch data. Try again later.",
        )
    except NetworkError as e:
        logger.error(f"Network error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Network error fetching batch data. Try again later.",
        )
    except DataFetchError as e:
        logger.error(f"Data fetch error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error fetching batch data. Try again later.",
        )
    except Exception as e:
        logger.error(f"Error getting batch market data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving batch data. Please try again later.",
        )


# Forecasting endpoints
@router.post("/forecast", response_model=dict)
async def forecast_price(request: dict, db: Session = Depends(get_db)):
    """
    Get price forecast for an asset using ML models

    Supports: ARIMA, Exponential Smoothing, Linear Regression
    """
    try:
        from app.models import ForecastRequest
        from app.services.forecasting_service import get_forecasting_service

        # Parse request
        req = ForecastRequest(**request)

        # Get forecasting service
        forecasting_service = get_forecasting_service()

        # Convert order list to tuple
        order = tuple(req.order) if req.order else (1, 1, 1)

        # Get forecast
        result = await asyncio.to_thread(
            forecasting_service.get_forecast,
            symbol=req.symbol,
            days_ahead=req.days_ahead,
            model_type=req.model_type,
            order=order,
        )

        return result

    except ValueError as e:
        logger.warning(f"Validation error for forecast: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating forecast. Please try again later.",
        )


@router.post("/forecast/retrain")
async def retrain_forecast_model(request: dict, db: Session = Depends(get_db)):
    """Force retrain forecast model for a symbol"""
    try:
        from app.services.forecasting_service import get_forecasting_service

        symbol = request.get("symbol")
        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol is required"
            )

        forecasting_service = get_forecasting_service()
        success = await asyncio.to_thread(forecasting_service.retrain_model, symbol)

        if success:
            return {"message": f"Model retrained successfully for {symbol}", "symbol": symbol}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrain model"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retraining forecast model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retraining model. Please try again later.",
        )


@router.get("/forecast/accuracy/{symbol}")
async def get_forecast_accuracy(symbol: str, db: Session = Depends(get_db)):
    """Get model accuracy metrics for a symbol"""
    try:
        from app.services.forecasting_service import get_forecasting_service

        forecasting_service = get_forecasting_service()
        accuracy = await asyncio.to_thread(forecasting_service.get_model_accuracy, symbol)
        return accuracy

    except Exception as e:
        logger.error(f"Error getting forecast accuracy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting accuracy. Please try again later.",
        )


# Backtesting endpoints
@router.post("/backtest")
async def run_backtest_endpoint(request: dict, db: Session = Depends(get_db)):
    """
    Run backtest on historical data to evaluate model accuracy
    """
    try:
        from app.services.backtesting_service import get_backtesting_service

        symbol = request.get("symbol")
        model_type = request.get("model_type", "arima")
        forecast_horizon = request.get("forecast_horizon", 30)
        train_ratio = request.get("train_ratio", 0.8)

        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol is required"
            )

        backtesting_service = get_backtesting_service()
        result = await asyncio.to_thread(
            backtesting_service.run_backtest,
            symbol=symbol,
            model_type=model_type,
            forecast_horizon=forecast_horizon,
            train_ratio=train_ratio,
        )

        return result

    except ValueError as e:
        logger.warning(f"Validation error for backtest: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error running backtest. Please try again later.",
        )


@router.get("/backtest/compare/{symbol}")
async def compare_models_endpoint(
    symbol: str, forecast_horizon: int = 30, db: Session = Depends(get_db)
):
    """Compare different forecasting models"""
    try:
        from app.services.backtesting_service import get_backtesting_service

        backtesting_service = get_backtesting_service()
        result = await asyncio.to_thread(
            backtesting_service.compare_models, symbol=symbol, forecast_horizon=forecast_horizon
        )

        return result

    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error comparing models. Please try again later.",
        )


# Advanced forecasting endpoints
@router.post("/forecast/grid-search")
async def grid_search_arima_endpoint(request: dict):
    """
    Grid search for best ARIMA parameters (p, d, q).
    Tries all combinations and returns the best by RMSE.
    """
    try:
        from app.models import GridSearchRequest
        from app.services.forecasting_service import get_forecasting_service

        req = GridSearchRequest(**request)
        forecasting_service = get_forecasting_service()

        # Load historical data
        from app.database import SessionLocal
        from app.services.database_service import DatabaseService

        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            history = db_service.get_historical_data(req.symbol, days=365)
        finally:
            db.close()

        if history.empty or len(history) < 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient data for {req.symbol}",
            )

        result = await asyncio.to_thread(
            forecasting_service.grid_search_arima,
            history["Close"],
            range(0, req.p_max),
            range(0, req.d_max),
            range(0, req.q_max),
        )

        return {"symbol": req.symbol, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in grid search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error in grid search. Please try again later.",
        )


@router.post("/forecast/cross-validate")
async def cross_validate_endpoint(request: dict):
    """
    Time series cross-validation using TimeSeriesSplit.
    Evaluates model stability across multiple folds.
    """
    try:
        from app.models import CrossValidationRequest
        from app.services.forecasting_service import get_forecasting_service

        req = CrossValidationRequest(**request)
        forecasting_service = get_forecasting_service()

        # Load historical data
        from app.database import SessionLocal
        from app.services.database_service import DatabaseService

        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            history = db_service.get_historical_data(req.symbol, days=365)
        finally:
            db.close()

        if history.empty or len(history) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient data for {req.symbol}",
            )

        result = await asyncio.to_thread(
            forecasting_service.timeseries_cross_validate,
            history["Close"],
            n_splits=req.n_splits,
            model_type=req.model_type,
        )

        return {"symbol": req.symbol, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cross-validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error in cross-validation. Please try again later.",
        )


@router.post("/forecast/compare-baselines")
async def compare_baselines_endpoint(request: dict):
    """
    Compare all baseline forecasting methods:
    naive, rolling mean, weighted MA, Holt-Winters, ARIMA.
    """
    try:
        from app.models import BaselineComparisonRequest
        from app.services.forecasting_service import get_forecasting_service

        req = BaselineComparisonRequest(**request)
        forecasting_service = get_forecasting_service()

        # Load historical data
        from app.database import SessionLocal
        from app.services.database_service import DatabaseService

        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            history = db_service.get_historical_data(req.symbol, days=365)
        finally:
            db.close()

        if history.empty or len(history) < 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient data for {req.symbol}",
            )

        result = await asyncio.to_thread(
            forecasting_service.compare_all_baselines,
            history["Close"],
            forecast_horizon=req.forecast_horizon,
        )

        return {"symbol": req.symbol, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing baselines: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error comparing baselines. Please try again later.",
        )


@router.get("/forecast/stationarity/{symbol}")
async def check_stationarity_endpoint(symbol: str):
    """
    Check time series stationarity using Augmented Dickey-Fuller test.
    Returns test statistics and recommendations.
    """
    try:
        from app.services.forecasting_service import get_forecasting_service

        forecasting_service = get_forecasting_service()

        # Load historical data
        from app.database import SessionLocal
        from app.services.database_service import DatabaseService

        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            history = db_service.get_historical_data(symbol, days=365)
        finally:
            db.close()

        if history.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data for {symbol}",
            )

        result = await asyncio.to_thread(
            forecasting_service.check_stationarity, history["Close"]
        )

        return {
            "symbol": symbol,
            "stationarity": result,
            "recommendation": (
                "Series is stationary. ARIMA(0,d,q) with d=0 may work."
                if result["is_stationary"]
                else "Series is non-stationary. Consider differencing (d>=1) or log transform."
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking stationarity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error checking stationarity. Please try again later.",
        )


# Clustering endpoints
@router.post("/forecast/clusters")
async def get_market_regimes_endpoint(request: dict):
    """
    Detect market regimes using K-means clustering on price windows.
    Includes silhouette analysis and PCA/t-SNE dimensionality reduction.
    """
    try:
        from app.models import ClusteringRequest
        from app.services.clustering_service import get_clustering_service

        req = ClusteringRequest(**request)

        # Load historical data
        from app.database import SessionLocal
        from app.services.database_service import DatabaseService

        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            history = db_service.get_historical_data(req.symbol, days=365)
        finally:
            db.close()

        if history.empty or len(history) < req.window_size * 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient data for clustering {req.symbol}. "
                f"Need at least {req.window_size * 3} data points.",
            )

        clustering_service = get_clustering_service()
        result = await asyncio.to_thread(
            clustering_service.get_market_regimes,
            history["Close"],
            window_size=req.window_size,
            k_range=range(req.k_min, req.k_max),
        )

        return {"symbol": req.symbol, **result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in market regime clustering: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error in clustering. Please try again later.",
        )


# Import portfolio service
from app.services.portfolio_service import PortfolioService, get_portfolio_service


# Portfolio endpoints
@router.post("/portfolios", status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_data: PortfolioCreateRequest,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Create a new portfolio for the current user"""
    try:
        result = await portfolio_service.create_portfolio(
            current_user["user_id"], portfolio_data.name
        )

        if "error" in result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating portfolio. Please try again later.",
        )


@router.get("/portfolios")
async def get_user_portfolios(
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get all portfolios for the current user"""
    try:
        portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])

        return {"portfolios": portfolios, "count": len(portfolios)}
    except Exception as e:
        logger.error(f"Error getting user portfolios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving portfolios. Please try again later.",
        )


@router.get("/portfolios/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get a specific portfolio with its items"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this portfolio",
            )

        portfolio = await portfolio_service.get_portfolio(portfolio_id)

        if not portfolio:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

        return portfolio
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving portfolio. Please try again later.",
        )


@router.post("/portfolios/{portfolio_id}/items")
async def add_to_portfolio(
    portfolio_id: int,
    item_data: AssetAddRequest,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Add an asset to a portfolio"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this portfolio",
            )

        # Add current date as purchase date
        from datetime import datetime

        purchase_date = datetime.now(UTC).isoformat()

        # If no purchase price provided, use the current market price
        purchase_price = item_data.purchase_price
        if purchase_price is None:
            try:
                data_fetcher = get_data_fetcher()
                market_data = await data_fetcher.get_stock_data(item_data.symbol)
                if market_data and market_data.get("current_price"):
                    purchase_price = float(market_data["current_price"])
            except Exception as e:
                logger.warning(f"Could not fetch market price for {item_data.symbol}: {e}")

        if purchase_price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="purchase_price is required (could not fetch current market price)",
            )

        result = await portfolio_service.add_to_portfolio(
            portfolio_id,
            item_data.symbol,
            item_data.name,
            item_data.quantity,
            purchase_price,
            purchase_date,
            item_data.asset_type,
        )

        if "error" in result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding asset to portfolio. Please try again later.",
        )


@router.delete("/portfolios/{portfolio_id}/items/{symbol}")
async def remove_from_portfolio(
    portfolio_id: int,
    symbol: str,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Remove an asset from a portfolio"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to modify this portfolio",
            )

        success = await portfolio_service.remove_from_portfolio(portfolio_id, symbol)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found in portfolio"
            )

        return {"message": f"Asset {symbol} removed from portfolio successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removing asset from portfolio. Please try again later.",
        )


@router.get("/portfolios/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get portfolio performance metrics"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this portfolio",
            )

        performance = await portfolio_service.calculate_portfolio_performance(portfolio_id)

        if "error" in performance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=performance["error"]
            )

        return performance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving portfolio performance. Please try again later.",
        )


@router.get("/portfolios/{portfolio_id}/holdings")
async def get_portfolio_holdings(
    portfolio_id: int,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get detailed portfolio holdings"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this portfolio",
            )

        holdings = await portfolio_service.get_portfolio_holdings(portfolio_id)

        return {"holdings": holdings, "count": len(holdings)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio holdings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving portfolio holdings. Please try again later.",
        )


@router.get("/portfolios/{portfolio_id}/analytics/advanced")
async def get_advanced_portfolio_analytics(
    portfolio_id: int,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get advanced portfolio analytics including VaR, beta, and Sortino ratio"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this portfolio",
            )

        analytics = await portfolio_service.get_advanced_portfolio_analytics(portfolio_id)

        if "error" in analytics:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=analytics["error"])

        return analytics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting advanced portfolio analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving advanced portfolio analytics. Please try again later.",
        )


@router.get("/portfolios/{portfolio_id}/risk/var")
async def get_portfolio_value_at_risk(
    portfolio_id: int,
    confidence_level: float = 0.95,
    time_horizon: int = 1,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get portfolio Value at Risk (VaR)"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this portfolio",
            )

        var_metrics = await portfolio_service.calculate_value_at_risk(
            portfolio_id, confidence_level=confidence_level, time_horizon=time_horizon
        )

        if "error" in var_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=var_metrics["error"]
            )

        return var_metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio VaR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving portfolio Value at Risk. Please try again later.",
        )


@router.get("/portfolios/{portfolio_id}/risk/beta")
async def get_portfolio_beta(
    portfolio_id: int,
    benchmark_symbol: str = "SPY",
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get portfolio beta relative to a benchmark"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this portfolio",
            )

        beta_metrics = await portfolio_service.calculate_portfolio_beta(
            portfolio_id, benchmark_symbol=benchmark_symbol
        )

        if "error" in beta_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=beta_metrics["error"]
            )

        return beta_metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio beta: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving portfolio beta. Please try again later.",
        )


@router.get("/portfolios/{portfolio_id}/risk/sortino")
async def get_portfolio_sortino_ratio(
    portfolio_id: int,
    risk_free_rate: float = 0.02,
    current_user: dict = Depends(get_current_user),
    portfolio_service: PortfolioService = Depends(get_portfolio_service),
):
    """Get portfolio Sortino ratio"""
    try:
        # Verify that the portfolio belongs to the current user
        user_portfolios = await portfolio_service.get_user_portfolios(current_user["user_id"])
        portfolio_ids = [p["id"] for p in user_portfolios]

        if portfolio_id not in portfolio_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this portfolio",
            )

        sortino_metrics = await portfolio_service.calculate_sortino_ratio(
            portfolio_id, risk_free_rate=risk_free_rate
        )

        if "error" in sortino_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=sortino_metrics["error"]
            )

        return sortino_metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio Sortino ratio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving portfolio Sortino ratio. Please try again later.",
        )


# Export data endpoint
@router.get("/asset/{symbol}/export")
async def export_data(
    symbol: str,
    format: str = "csv",
    period: str = "1mo",
    interval: str = "5m",
):
    """Export asset data as CSV or Excel"""
    try:
        try:
            symbol = _validate_symbol(symbol)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        data_fetcher = get_data_fetcher()

        # Determine asset type based on symbol
        if symbol.lower() in ["bitcoin", "ethereum", "solana", "cardano", "polkadot"]:
            data = await data_fetcher.get_crypto_data(symbol.lower())
        else:
            data = await data_fetcher.get_stock_data(symbol, period, interval)

        if not data or not data.get("chart_data"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}",
            )

        # Validate format
        if format.lower() not in ["csv", "xlsx"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {format}. Supported formats: csv, xlsx",
            )

        chart_data = data.get("chart_data", [])

        if format.lower() == "csv":
            # Create CSV content
            output = io.StringIO()
            if chart_data and len(chart_data) > 0:
                # Determine columns from first row
                first_row = chart_data[0]
                fieldnames = list(first_row.keys())

                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(chart_data)

            csv_content = output.getvalue()

            return Response(
                content=csv_content,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename={_sanitize_filename(symbol)}_data.csv"
                    )
                },
            )
        else:  # xlsx
            # Create real Excel file using openpyxl
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            assert ws is not None
            ws.title = symbol.upper()[:31]

            if chart_data and len(chart_data) > 0:
                # Write header row
                fieldnames = list(chart_data[0].keys())
                ws.append(fieldnames)

                # Write data rows
                for row in chart_data:
                    ws.append([row.get(col) for col in fieldnames])

            xlsx_buffer = io.BytesIO()
            wb.save(xlsx_buffer)
            xlsx_content = xlsx_buffer.getvalue()

            return Response(
                content=xlsx_content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": (
                        f"attachment; filename={_sanitize_filename(symbol)}_data.xlsx"
                    )
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error exporting data. Please try again later.",
        )


# Historical data endpoint
@router.get("/asset/{symbol}/historical")
async def get_historical_data(
    symbol: str,
    period: int = Query(default=30, ge=1, le=365, description="Number of days"),
    interval: str = Query(default="daily", pattern="^(hourly|daily|weekly)$"),
):
    """Get historical data for an asset"""
    try:
        data_fetcher = get_data_fetcher()

        # Determine asset type and fetch historical data
        if symbol.lower() in [
            "bitcoin",
            "ethereum",
            "solana",
            "cardano",
            "polkadot",
            "ripple",
            "dogecoin",
        ]:
            data = await data_fetcher.get_crypto_historical_data(symbol.lower(), period)
        else:
            # For stocks, use get_stock_data with converted period/interval
            yf_period = _convert_days_to_yf_period(period)
            yf_interval = _convert_interval_to_yf(interval)
            data = await data_fetcher.get_stock_data(symbol, period=yf_period, interval=yf_interval)

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No historical data found for symbol: {symbol}",
            )

        return {
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data": data.get("chart_data", []),
            "current_price": data.get("current_price"),
            "timestamp": data.get("timestamp"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting historical data for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving historical data. Please try again later.",
        )


# Email notification endpoints
@router.post("/email/test")
async def test_email_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send a test email to verify SMTP configuration"""
    try:
        from app.services.email_service import EmailService

        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        email_service = await EmailService.get_instance()
        success = await email_service.send_test_email(user.email)

        if success:
            return {
                "message": "Test email sent successfully",
                "to": user.email,
                "enabled": email_service.enabled,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test email. Check SMTP configuration.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending test email. Please try again later.",
        )


@router.post("/email/price-alert")
async def send_price_alert_email(
    request: Request,
    symbol: str = Query(..., description="Asset symbol"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Send a price alert email notification"""
    try:
        from app.services.email_service import EmailService

        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        data_fetcher = get_data_fetcher()
        data = await data_fetcher.get_stock_data(symbol)

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}",
            )

        email_service = await EmailService.get_instance()
        success = await email_service.send_price_alert(user.email, dict(data))

        if success:
            return {"message": f"Price alert email sent for {symbol}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send price alert email.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending price alert email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending price alert email. Please try again later.",
        )


# Compare assets endpoint
@router.get("/assets/compare")
async def compare_assets(
    symbols: str = Query(
        ..., description="Comma-separated list of symbols to compare (e.g., AAPL,GOOGL,MSFT)"
    ),
    period: int = Query(default=30, ge=1, le=365, description="Number of days for comparison"),
):
    """Compare multiple assets performance"""
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]

        if len(symbol_list) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 symbols are required for comparison",
            )

        if len(symbol_list) > 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 10 symbols allowed for comparison",
            )

        data_fetcher = get_data_fetcher()
        comparison_data = []

        for symbol in symbol_list:
            try:
                # Determine asset type and fetch data
                if symbol.lower() in [
                    "bitcoin",
                    "ethereum",
                    "solana",
                    "cardano",
                    "polkadot",
                    "ripple",
                    "dogecoin",
                ]:
                    data = await data_fetcher.get_crypto_data(symbol.lower())
                else:
                    data = await data_fetcher.get_stock_data(symbol)

                if data:
                    comparison_data.append(
                        {
                            "symbol": symbol,
                            "current_price": data.get("current_price"),
                            "change_percent": data.get("change_percent"),
                            "volume": data.get("volume"),
                            "market_cap": data.get("market_cap"),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch data for {symbol}: {e}")
                comparison_data.append(
                    {
                        "symbol": symbol,
                        "error": "Failed to fetch data",
                    }
                )

        if not comparison_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for any of the requested symbols",
            )

        # Calculate performance metrics
        performance_data = []
        base_prices = {}

        for item in comparison_data:
            if "error" not in item and item.get("current_price"):
                base_prices[item["symbol"]] = item["current_price"]
                performance_data.append(
                    {
                        "symbol": item["symbol"],
                        "current_price": item["current_price"],
                        "change_percent": item["change_percent"],
                        "performance_1d": item.get("change_percent", 0),
                    }
                )

        # Sort by performance
        performance_data.sort(key=lambda x: x.get("performance_1d", 0), reverse=True)

        return {
            "symbols": symbol_list,
            "period": period,
            "comparison": comparison_data,
            "performance_ranking": performance_data,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing assets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error comparing assets. Please try again later.",
        )
