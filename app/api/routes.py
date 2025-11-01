"""API routes for the FastAPI Finance Monitor application"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
from datetime import datetime, timedelta

from app.database import get_db
from app.services.database_service import DatabaseService
from app.services.auth_service import AuthService, get_current_user
from app.services.data_fetcher import DataFetcher
from app.services.cache_service import get_cache_service
from app.services.redis_cache_service import get_redis_cache_service
from app.services.monitoring_service import get_monitoring_service

# Import custom exceptions
from app.exceptions.custom_exceptions import (
    FinanceMonitorError, DataFetchError, RateLimitError, DataValidationError,
    CacheError, DatabaseError, AuthenticationError, AuthorizationError,
    ValidationError, WebSocketError, ConfigurationError, ServiceUnavailableError,
    NetworkError, TimeoutError
)

# Import request/response models
from app.models import (
    UserRegistrationRequest, EmailVerificationRequest, 
    AlertCreateRequest, PortfolioCreateRequest, WatchlistCreateRequest,
    AssetAddRequest, AssetRemoveRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

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
            "services": {
                "database": "healthy",
                "cache": cache_status,
                "redis": redis_status
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
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
            db_service.get_user_by_username("admin")  # This will return None but test the connection
            db_status = "healthy"
        except DatabaseError as e:
            db_status = f"unhealthy: {str(e)}"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check cache service
        cache_service = get_cache_service()
        try:
            cache_stats = await cache_service.get_stats()
            cache_status = "healthy" if cache_stats else "unhealthy"
        except CacheError as e:
            cache_status = f"unhealthy: {str(e)}"
        except Exception as e:
            cache_status = f"unhealthy: {str(e)}"
        
        # Check Redis connection
        redis_service = get_redis_cache_service()
        try:
            redis_stats = await redis_service.get_stats()
            redis_status = "healthy" if redis_stats else "unhealthy"
        except CacheError as e:
            redis_status = f"unhealthy: {str(e)}"
        except Exception as e:
            redis_status = f"unhealthy: {str(e)}"
        
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
                "monitoring": "healthy"
            },
            "stats": {
                "cache": cache_stats,
                "redis": redis_stats,
                "monitoring": monitoring_stats
            }
        }
    except FinanceMonitorError as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )

# User registration endpoint
@router.post("/users/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistrationRequest, request: Request, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        username = user_data.username
        email = user_data.email
        password = user_data.password
        
        logger.info(f"Attempting to register user: {username}, email: {email}")
        
        # Rate limiting check for registration
        client_ip = request.client.host if hasattr(request, 'client') and request.client else "unknown"
        if not AuthService.is_registration_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later."
            )
        
        # Check if user already exists
        db_service = DatabaseService(db)
        existing_user = db_service.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered"
            )
        
        existing_email = db_service.get_user_by_email(email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
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
            "email": new_user.email
        }
    except HTTPException:
        raise
    except ValidationError as e:
        # Handle validation errors
        logger.error(f"Validation error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(f"Database error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user. Please try again later."
        )
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user. Please try again later."
        )

# User login endpoint
@router.post("/users/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
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
        
        # Check if user has verified their email (if required)
        # For development/testing, we can skip email verification
        is_development = os.getenv("APP_ENV", "development") == "development"
        if not is_development and not getattr(user, 'is_verified', True):  # Default to True for backward compatibility
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please verify your email address before logging in",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=30)  # Use hardcoded value instead of class attribute
        access_token = AuthService.create_access_token(
            data={"user_id": user.id, "username": user.username}, 
            expires_delta=access_token_expires
        )
        
        # Log successful login
        logger.info(f"User {user.username} (ID: {user.id}) logged in successfully")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
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
            detail="Error logging in user. Please try again later."
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
                detail="Invalid or expired verification token"
            )
        
        # Find user by email
        db_service = DatabaseService(db)
        user = db_service.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user verification status
        setattr(user, 'is_verified', True)
        db.commit()
        db.refresh(user)
        
        logger.info(f"User {user.username} (ID: {user.id}) verified their email address")
        
        return {
            "message": "Email verified successfully",
            "user_id": user.id,
            "username": user.username
        }
    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying email. Please try again later."
        )
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying email. Please try again later."
        )

# Get user profile endpoint
@router.get("/users/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user profile"""
    try:
        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Handle the created_at field properly
        created_at_value = None
        if hasattr(user, 'created_at') and user.created_at is not None:
            created_at_value = user.created_at.isoformat()
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_verified": getattr(user, 'is_verified', True),
            "created_at": created_at_value
        }
    except HTTPException:
        raise
    except DatabaseError as e:
        logger.error(f"Database error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user profile. Please try again later."
        )
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving user profile. Please try again later."
        )

# Get market data endpoint
@router.get("/market-data/{symbol}")
async def get_market_data(symbol: str, period: str = "1d", interval: str = "5m"):
    """Get market data for a specific symbol"""
    try:
        data_fetcher = DataFetcher()
        
        # Determine asset type based on symbol
        if symbol.lower() in ['bitcoin', 'ethereum', 'solana', 'litecoin', 'cardano']:
            data = await data_fetcher.get_crypto_data(symbol)
        else:
            data = await data_fetcher.get_stock_data(symbol, period, interval)
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}"
            )
        
        return data
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {str(e)}"
        )
    except TimeoutError as e:
        logger.error(f"Timeout error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout fetching data for {symbol}: {str(e)}"
        )
    except NetworkError as e:
        logger.error(f"Network error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network error fetching data for {symbol}: {str(e)}"
        )
    except DataFetchError as e:
        logger.error(f"Data fetch error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching data for {symbol}: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving data for {symbol}. Please try again later."
        )

# Get multiple market data endpoint
@router.post("/market-data/batch")
async def get_batch_market_data(symbols: List[str]):
    """Get market data for multiple symbols"""
    try:
        data_fetcher = DataFetcher()
        
        # Prepare assets list
        assets = []
        for symbol in symbols:
            asset_type = "crypto" if symbol.lower() in ['bitcoin', 'ethereum', 'solana', 'litecoin', 'cardano'] else "stock"
            assets.append({
                "symbol": symbol,
                "name": symbol,
                "type": asset_type
            })
        
        # Fetch data for all assets
        data = await data_fetcher.get_multiple_assets(assets)
        
        return {
            "data": data,
            "count": len(data)
        }
    except RateLimitError as e:
        logger.warning(f"Rate limit exceeded for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {str(e)}"
        )
    except TimeoutError as e:
        logger.error(f"Timeout error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout fetching batch data: {str(e)}"
        )
    except NetworkError as e:
        logger.error(f"Network error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network error fetching batch data: {str(e)}"
        )
    except DataFetchError as e:
        logger.error(f"Data fetch error for batch request: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error fetching batch data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error getting batch market data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving batch data. Please try again later."
        )
