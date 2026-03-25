"""API routes for the FastAPI Finance Monitor application"""

import csv
import io
import logging
import os
from datetime import datetime, timedelta

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
    UserRegistrationRequest,
)
from app.services.auth_service import AuthService, get_current_user
from app.services.cache_service import get_cache_service
from app.services.data_fetcher import DataFetcher
from app.services.database_service import DatabaseService
from app.services.monitoring_service import get_monitoring_service
from app.services.redis_cache_service import get_redis_cache_service

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
            "timestamp": datetime.now().isoformat(),
            "services": {"database": "healthy", "cache": cache_status, "redis": redis_status},
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Service unhealthy: {e!s}"
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
            "timestamp": datetime.now().isoformat(),
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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Service unhealthy: {e!s}"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Service unhealthy: {e!s}"
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
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """Login user and return access token"""
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

        # Create access token
        access_token_expires = timedelta(
            minutes=30
        )  # Use hardcoded value instead of class attribute
        access_token = AuthService.create_access_token(
            data={"user_id": user.id, "username": user.username}, expires_delta=access_token_expires
        )

        # Log successful login
        logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username,
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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required"
            )

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
):
    """Get Telegram bot connection link"""
    try:
        bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "finance_monitor_bot")
        import secrets
        token = secrets.token_urlsafe(32)
        
        import base64
        user_token = base64.urlsafe_b64encode(
            f"{current_user['user_id']}:{token}".encode()
        ).decode()
        
        connect_link = f"https://t.me/{bot_username}?start={user_token}"
        
        return {
            "connect_link": connect_link,
            "bot_username": bot_username,
            "instructions": "Нажмите на ссылку и отправьте команду /start в Telegram боте",
        }
    except Exception as e:
        logger.error(f"Error generating Telegram connect link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating connection link: {e!s}",
        )


@router.get("/telegram/status")
async def get_telegram_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Telegram connection status for current user"""
    try:
        from app.models import TelegramConnection
        
        connection = db.query(TelegramConnection).filter(
            TelegramConnection.user_id == current_user["user_id"],
            TelegramConnection.is_active == True
        ).first()
        
        if connection:
            return {
                "connected": True,
                "telegram_id": connection.telegram_id,
                "telegram_username": connection.telegram_username,
                "connected_at": connection.connected_at.isoformat(),
                "last_notification_at": connection.last_notification_at.isoformat() if connection.last_notification_at else None,
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
            detail=f"Error retrieving Telegram status: {e!s}",
        )


@router.post("/telegram/disconnect")
async def disconnect_telegram(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect Telegram from user account"""
    try:
        from app.models import TelegramConnection
        
        connection = db.query(TelegramConnection).filter(
            TelegramConnection.user_id == current_user["user_id"]
        ).first()
        
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
            detail=f"Error disconnecting Telegram: {e!s}",
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
        
        connection = db.query(TelegramConnection).filter(
            TelegramConnection.user_id == current_user["user_id"],
            TelegramConnection.is_active == True
        ).first()
        
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
            "<i>FastAPI Finance Monitor</i>"
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
            detail=f"Error sending test notification: {e!s}",
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
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Rate limit exceeded: {e!s}"
        )
    except TimeoutError as e:
        logger.error(f"Timeout error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout fetching data for {symbol}: {e!s}",
        )
    except NetworkError as e:
        logger.error(f"Network error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network error fetching data for {symbol}: {e!s}",
        )
    except DataFetchError as e:
        logger.error(f"Data fetch error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching data for {symbol}: {e!s}",
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
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Rate limit exceeded: {e!s}"
        )
    except TimeoutError as e:
        logger.error(f"Timeout error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout fetching batch data: {e!s}",
        )
    except NetworkError as e:
        logger.error(f"Network error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network error fetching batch data: {e!s}",
        )
    except DataFetchError as e:
        logger.error(f"Data fetch error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Error fetching batch data: {e!s}"
        )
    except Exception as e:
        logger.error(f"Error getting batch market data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving batch data. Please try again later.",
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

        purchase_date = datetime.now().isoformat()

        result = await portfolio_service.add_to_portfolio(
            portfolio_id,
            item_data.symbol,
            item_data.name,
            1.0,  # Default quantity, should be configurable
            0.0,  # Default purchase price, should be configurable
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

        chart_data = data["chart_data"]

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
                    "Content-Disposition": f"attachment; filename={symbol}_data.csv"
                },
            )
        else:  # xlsx
            # For Excel export, we need openpyxl or similar
            # For now, return CSV with xlsx content-type (simplified)
            # In production, use: import openpyxl or pandas
            output = io.StringIO()
            if chart_data and len(chart_data) > 0:
                first_row = chart_data[0]
                fieldnames = list(first_row.keys())

                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(chart_data)

            csv_content = output.getvalue()

            # Note: This is a simplified implementation
            # For real Excel export, install openpyxl and use:
            # from openpyxl import Workbook
            return Response(
                content=csv_content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename={symbol}_data.xlsx"
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting data: {e!s}",
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
        if symbol.lower() in ["bitcoin", "ethereum", "solana", "cardano", "polkadot", "ripple", "dogecoin"]:
            data = await data_fetcher.get_crypto_historical_data(symbol.lower(), period)
        else:
            # For stocks, use get_stock_data with extended period
            data = await data_fetcher.get_stock_data(symbol, period=period, interval=interval)

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
            detail=f"Error retrieving historical data: {e!s}",
        )


# Compare assets endpoint
@router.get("/assets/compare")
async def compare_assets(
    symbols: str = Query(..., description="Comma-separated list of symbols to compare (e.g., AAPL,GOOGL,MSFT)"),
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
                if symbol.lower() in ["bitcoin", "ethereum", "solana", "cardano", "polkadot", "ripple", "dogecoin"]:
                    data = await data_fetcher.get_crypto_data(symbol.lower())
                else:
                    data = await data_fetcher.get_stock_data(symbol)

                if data:
                    comparison_data.append({
                        "symbol": symbol,
                        "current_price": data.get("current_price"),
                        "change_percent": data.get("change_percent"),
                        "volume": data.get("volume"),
                        "market_cap": data.get("market_cap"),
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch data for {symbol}: {e}")
                comparison_data.append({
                    "symbol": symbol,
                    "error": f"Failed to fetch data: {e!s}",
                })

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
                performance_data.append({
                    "symbol": item["symbol"],
                    "current_price": item["current_price"],
                    "change_percent": item["change_percent"],
                    "performance_1d": item.get("change_percent", 0),
                })

        # Sort by performance
        performance_data.sort(key=lambda x: x.get("performance_1d", 0), reverse=True)

        return {
            "symbols": symbol_list,
            "period": period,
            "comparison": comparison_data,
            "performance_ranking": performance_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing assets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error comparing assets: {e!s}",
        )
