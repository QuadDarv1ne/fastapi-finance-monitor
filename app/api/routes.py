"""API routes for the finance monitor application"""

from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
import logging
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator

from app.models import User
from app.services.auth_service import AuthService, get_current_user
from app.services.database_service import DatabaseService
from app.database import get_db
from app.services.cache_service import get_cache_service
from app.services.redis_cache_service import get_redis_cache_service
from app.services.monitoring_service import get_monitoring_service
from app.services.portfolio_service import get_portfolio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Pydantic models for request validation
class UserRegistrationRequest(BaseModel):
    username: str
    email: str
    password: str
    
    @validator('username')
    def validate_username(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if not v or len(v) > 255:
            raise ValueError('Email must be less than 255 characters')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        is_valid, message = AuthService.validate_password(v)
        if not is_valid:
            raise ValueError(message)
        return v

class EmailVerificationRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: str

class UserProfileUpdateRequest(BaseModel):
    email: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

# Portfolio Pydantic models
class PortfolioCreateRequest(BaseModel):
    name: str

class PortfolioAddItemRequest(BaseModel):
    portfolio_id: int
    symbol: str
    name: str
    quantity: float
    purchase_price: float
    purchase_date: str
    asset_type: str

class PortfolioRemoveItemRequest(BaseModel):
    portfolio_id: int
    symbol: str

# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Finance monitor is running",
        "timestamp": datetime.now().isoformat()
    }

# Enhanced health check with detailed status
@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check endpoint"""
    try:
        # Check database connection
        db_service = DatabaseService(db)
        db_status = "healthy"
        try:
            # Try to perform a simple database operation
            db_service.get_user_by_username("admin")  # This will return None but test the connection
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check cache service
        cache_service = get_cache_service()
        cache_stats = await cache_service.get_stats()
        cache_status = "healthy" if cache_stats else "unhealthy"
        
        # Check Redis connection
        redis_service = get_redis_cache_service()
        redis_stats = await redis_service.get_stats()
        redis_status = "healthy" if redis_stats else "unhealthy"
        
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
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

# User registration endpoint
@router.post("/users/register", status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistrationRequest, request: Request, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        username = user_data.username
        email = user_data.email
        password = user_data.password
        
        # Rate limiting check for registration
        client_ip = request.client.host if hasattr(request, 'client') and request.client else "unknown"
        if not AuthService.is_registration_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many registration attempts. Please try again later."
            )
        
        # Validate username format
        if not AuthService.validate_username(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid username format. Username must be 3-50 characters and contain only letters, numbers, and underscores."
            )
        
        # Validate email format
        if not AuthService.validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format."
            )
        
        # Validate password strength
        is_valid, message = AuthService.validate_password(password)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
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
        new_user = db_service.create_user(username, email, password)
        
        return {
            "message": "User registered successfully",
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user. Please try again later."
        )

# User login endpoint
@router.post("/users/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and return access token"""
    try:
        # Rate limiting check could be implemented here
        
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
        if not getattr(user, 'is_verified', True):  # Default to True for backward compatibility
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
    except Exception as e:
        db.rollback()
        logger.error(f"Error verifying email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying email. Please try again later."
        )

# Resend email verification endpoint
@router.post("/users/resend-verification")
async def resend_verification_email(verification_data: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Resend email verification to user"""
    try:
        # Find user by email
        db_service = DatabaseService(db)
        user = db_service.get_user_by_email(verification_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is already verified
        if getattr(user, 'is_verified', True):  # Default to True for backward compatibility
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )
        
        # Send verification email
        db_service.send_verification_email(user)
        
        logger.info(f"Resent verification email to user {user.username} (ID: {user.id})")
        
        return {
            "message": "Verification email sent successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resending verification email. Please try again later."
        )

# Get current user profile
@router.get("/users/me")
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
        
        # Get created_at as string if it exists
        created_at_str = None
        user_created_at = getattr(user, 'created_at', None)
        if user_created_at:
            created_at_str = user_created_at.isoformat()
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": created_at_str
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user profile. Please try again later."
        )

# Update user profile
@router.put("/users/me")
async def update_user_profile(
    user_data: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update email if provided
        email = user_data.email
        if email:
            # Validate email format
            if not AuthService.validate_email(email):
                raise ValueError("Invalid email format")
            
            # Check if email is already taken
            existing_email = db_service.get_user_by_email(email)
            existing_email_id = getattr(existing_email, 'id', None) if existing_email else None
            user_id = getattr(user, 'id')
            if existing_email and existing_email_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already registered"
                )
            setattr(user, 'email', email)
        
        db.commit()
        db.refresh(user)
        
        # Log the update
        logger.info(f"User {user.username} (ID: {user.id}) updated their profile")
        
        return {
            "message": "User profile updated successfully",
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        }
    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user profile. Please try again later."
        )

# Change password
@router.put("/users/me/password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        db_service = DatabaseService(db)
        user = db_service.get_user(current_user["user_id"])
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        current_password = password_data.current_password
        new_password = password_data.new_password
        
        # Validate new password strength
        is_valid, message = AuthService.validate_password(new_password)
        if not is_valid:
            raise ValueError(message)
        
        # Verify current password (get the actual value from the column)
        current_hashed_password = getattr(user, 'hashed_password')
        if not AuthService.verify_password(current_password, current_hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Hash and update new password
        setattr(user, 'hashed_password', AuthService.get_password_hash(new_password))
        db.commit()
        
        # Log the password change
        logger.info(f"User {user.username} (ID: {user.id}) changed their password")
        
        return {
            "message": "Password updated successfully"
        }
    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing password. Please try again later."
        )

# Portfolio endpoints
@router.post("/portfolio/create")
async def create_portfolio(
    portfolio_data: PortfolioCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new portfolio for the current user"""
    try:
        db_service = DatabaseService(db)
        portfolio_service = get_portfolio_service(db_service)
        
        result = await portfolio_service.create_portfolio(
            current_user["user_id"], 
            portfolio_data.name
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating portfolio"
        )

@router.get("/portfolio/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific portfolio with its items"""
    try:
        db_service = DatabaseService(db)
        portfolio_service = get_portfolio_service(db_service)
        
        # Check if portfolio belongs to user
        user_portfolios = db_service.get_user_portfolios(current_user["user_id"])
        if not any(p.id == portfolio_id for p in user_portfolios):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portfolio does not belong to user"
            )
        
        result = await portfolio_service.get_portfolio(portfolio_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio not found"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting portfolio"
        )

@router.get("/portfolio")
async def get_user_portfolios(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all portfolios for the current user"""
    try:
        db_service = DatabaseService(db)
        portfolio_service = get_portfolio_service(db_service)
        
        result = await portfolio_service.get_user_portfolios(current_user["user_id"])
        return result
    except Exception as e:
        logger.error(f"Error getting user portfolios: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting user portfolios"
        )

@router.post("/portfolio/add_item")
async def add_to_portfolio(
    item_data: PortfolioAddItemRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add an asset to a portfolio"""
    try:
        db_service = DatabaseService(db)
        portfolio_service = get_portfolio_service(db_service)
        
        # Check if portfolio belongs to user
        user_portfolios = db_service.get_user_portfolios(current_user["user_id"])
        if not any(p.id == item_data.portfolio_id for p in user_portfolios):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portfolio does not belong to user"
            )
        
        result = await portfolio_service.add_to_portfolio(
            item_data.portfolio_id,
            item_data.symbol,
            item_data.name,
            item_data.quantity,
            item_data.purchase_price,
            item_data.purchase_date,
            item_data.asset_type
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding to portfolio"
        )

@router.post("/portfolio/remove_item")
async def remove_from_portfolio(
    item_data: PortfolioRemoveItemRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove an asset from a portfolio"""
    try:
        db_service = DatabaseService(db)
        portfolio_service = get_portfolio_service(db_service)
        
        # Check if portfolio belongs to user
        user_portfolios = db_service.get_user_portfolios(current_user["user_id"])
        if not any(p.id == item_data.portfolio_id for p in user_portfolios):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portfolio does not belong to user"
            )
        
        result = await portfolio_service.remove_from_portfolio(
            item_data.portfolio_id,
            item_data.symbol
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found in portfolio"
            )
        
        return {"message": "Asset removed from portfolio successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removing from portfolio"
        )

@router.get("/portfolio/{portfolio_id}/performance")
async def get_portfolio_performance(
    portfolio_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get portfolio performance metrics"""
    try:
        db_service = DatabaseService(db)
        portfolio_service = get_portfolio_service(db_service)
        
        # Check if portfolio belongs to user
        user_portfolios = db_service.get_user_portfolios(current_user["user_id"])
        if not any(p.id == portfolio_id for p in user_portfolios):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portfolio does not belong to user"
            )
        
        result = await portfolio_service.calculate_portfolio_performance(portfolio_id)
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"]
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio performance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting portfolio performance"
        )

@router.get("/portfolio/{portfolio_id}/holdings")
async def get_portfolio_holdings(
    portfolio_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed portfolio holdings"""
    try:
        db_service = DatabaseService(db)
        portfolio_service = get_portfolio_service(db_service)
        
        # Check if portfolio belongs to user
        user_portfolios = db_service.get_user_portfolios(current_user["user_id"])
        if not any(p.id == portfolio_id for p in user_portfolios):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Portfolio does not belong to user"
            )
        
        result = await portfolio_service.get_portfolio_holdings(portfolio_id)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio holdings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error getting portfolio holdings"
        )