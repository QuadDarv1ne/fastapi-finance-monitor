"""API routes for the finance monitor application"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import User
from app.services.auth_service import AuthService, get_current_user
from app.services.database_service import DatabaseService
from app.database import get_db
from app.services.cache_service import get_cache_service
from app.services.redis_cache_service import get_redis_cache_service
from app.services.monitoring_service import get_monitoring_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

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
async def register_user(username: str, email: str, password: str, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Validate input
        if not username or not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username, email, and password are required"
            )
        
        # Check if user already exists
        db_service = DatabaseService(db)
        existing_user = db_service.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        existing_email = db_service.get_user_by_email(email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
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
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error registering user"
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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=AuthService.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"user_id": user.id, "username": user.username}, 
            expires_delta=access_token_expires
        )
        
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
            detail="Error logging in user"
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
        
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user profile"
        )

# Update user profile
@router.put("/users/me")
async def update_user_profile(
    email: Optional[str] = None,
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
        if email:
            # Check if email is already taken
            existing_email = db_service.get_user_by_email(email)
            if existing_email and existing_email.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            user.email = email
        
        db.commit()
        db.refresh(user)
        
        return {
            "message": "User profile updated successfully",
            "user_id": user.id,
            "username": user.username,
            "email": user.email
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user profile"
        )

# Change password
@router.put("/users/me/password")
async def change_password(
    current_password: str,
    new_password: str,
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
        
        # Verify current password
        if not AuthService.verify_password(current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Hash and update new password
        user.hashed_password = AuthService.get_password_hash(new_password)
        db.commit()
        
        return {
            "message": "Password updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing password"
        )