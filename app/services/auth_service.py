"""Authentication service for user management

This module provides comprehensive authentication and authorization functionality
for the finance monitor application. It includes user registration, login,
password management, and JWT token handling with security best practices.

Key Features:
- Secure password hashing with bcrypt
- JWT token creation and validation
- Rate limiting for login, registration, and password reset
- Password strength validation
- Email and username validation
- OAuth2 integration with FastAPI

Classes:
    AuthService: Main class for authentication operations
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import os
import re
import secrets
import hashlib
import time
from collections import defaultdict
import logging

# Rate limiting for login attempts
login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW = 300  # 5 minutes

# Rate limiting for registration attempts
registration_attempts = defaultdict(list)
MAX_REGISTRATION_ATTEMPTS = 3
REGISTRATION_ATTEMPT_WINDOW = 3600  # 1 hour

# Rate limiting for password reset attempts
password_reset_attempts = defaultdict(list)
MAX_PASSWORD_RESET_ATTEMPTS = 3
PASSWORD_RESET_ATTEMPT_WINDOW = 3600  # 1 hour

def get_login_attempts():
    """Get login attempts dictionary"""
    return login_attempts

def get_registration_attempts():
    """Get registration attempts dictionary"""
    return registration_attempts



# JWT configuration
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/login")

# Logger
logger = logging.getLogger(__name__)

class AuthService:
    """Service for authentication operations"""
    
    @staticmethod
    def is_password_reset_allowed(email: str) -> bool:
        """Check if password reset is allowed for this email (rate limiting)"""
        now = time.time()
        # Remove attempts older than the window
        password_reset_attempts[email] = [
            attempt for attempt in password_reset_attempts[email] 
            if now - attempt < PASSWORD_RESET_ATTEMPT_WINDOW
        ]
        
        # Check if email has exceeded max attempts
        return len(password_reset_attempts[email]) < MAX_PASSWORD_RESET_ATTEMPTS

    @staticmethod
    def record_password_reset_attempt(email: str):
        """Record a password reset attempt"""
        password_reset_attempts[email].append(time.time())
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        # Truncate password to 72 bytes if needed (bcrypt limitation)
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password[:72]
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    @staticmethod
    def is_login_allowed(username: str) -> bool:
        """Check if user is allowed to login (rate limiting)"""
        now = time.time()
        # Remove attempts older than the window
        login_attempts[username] = [
            attempt for attempt in login_attempts[username] 
            if now - attempt < LOGIN_ATTEMPT_WINDOW
        ]
        
        # Check if user has exceeded max attempts
        return len(login_attempts[username]) < MAX_LOGIN_ATTEMPTS
    
    @staticmethod
    def is_registration_allowed(ip_address: str) -> bool:
        """Check if registration is allowed from this IP (rate limiting)"""
        now = time.time()
        # Remove attempts older than the window
        registration_attempts[ip_address] = [
            attempt for attempt in registration_attempts[ip_address] 
            if now - attempt < REGISTRATION_ATTEMPT_WINDOW
        ]
        
        # Check if IP has exceeded max attempts
        return len(registration_attempts[ip_address]) < MAX_REGISTRATION_ATTEMPTS
    
    @staticmethod
    def record_failed_login(username: str):
        """Record a failed login attempt"""
        login_attempts[username].append(time.time())
    
    @staticmethod
    def record_registration_attempt(ip_address: str):
        """Record a registration attempt"""
        registration_attempts[ip_address].append(time.time())
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password"""
        # Truncate password to 72 bytes if needed (bcrypt limitation)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """Validate password strength with detailed feedback"""
        # Truncate password to 72 bytes if needed (for bcrypt compatibility)
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters long"
        
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter (A-Z)"
        
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter (a-z)"
        
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit (0-9)"
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"
        
        # Check for common weak passwords
        common_passwords = [
            "password", "12345678", "qwerty", "abc123", "password123",
            "admin123", "welcome123", "letmein123"
        ]
        
        if password.lower() in common_passwords:
            return False, "Password is too common and weak. Please choose a stronger password."
        
        # Check for repetitive characters
        if re.search(r"(.)\1{2,}", password):
            return False, "Password contains too many repetitive characters (e.g., aaa, 111)"
        
        return True, "Password is valid"
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        if not username or len(username) < 3 or len(username) > 50:
            return False
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False
        return True
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token with enhanced security"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16),  # JWT ID for token revocation if needed
            "aud": "finance-monitor",  # Audience
            "iss": "finance-monitor-api"  # Issuer
        })
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        """Decode a JWT access token with enhanced security"""
        try:
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                audience="finance-monitor",
                issuer="finance-monitor-api"
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error decoding JWT: {e}")
            return None
    
    @staticmethod
    def generate_password_reset_token(email: str) -> str:
        """Generate a password reset token"""
        data = {
            "sub": email,
            "exp": datetime.utcnow() + timedelta(hours=1),  # Token expires in 1 hour
            "aud": "finance-monitor-password-reset",
            "iss": "finance-monitor-api"
        }
        return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_password_reset_token(token: str) -> Optional[str]:
        """Verify a password reset token and return the email"""
        try:
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                audience="finance-monitor-password-reset",
                issuer="finance-monitor-api"
            )
            email = payload.get("sub")
            if email:
                return email
            return None
        except JWTError:
            return None
        except Exception as e:
            logger.error(f"Error verifying password reset token: {e}")
            return None
    
    @staticmethod
    def generate_email_verification_token(email: str) -> str:
        """Generate an email verification token"""
        data = {
            "sub": email,
            "exp": datetime.utcnow() + timedelta(hours=24),  # Token expires in 24 hours
            "aud": "finance-monitor-email-verification",
            "iss": "finance-monitor-api"
        }
        return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_email_verification_token(token: str) -> Optional[str]:
        """Verify an email verification token and return the email"""
        try:
            payload = jwt.decode(
                token, 
                SECRET_KEY, 
                algorithms=[ALGORITHM],
                audience="finance-monitor-email-verification",
                issuer="finance-monitor-api"
            )
            email = payload.get("sub")
            if email:
                return email
            return None
        except JWTError:
            return None
        except Exception as e:
            logger.error(f"Error verifying email verification token: {e}")
            return None

# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = AuthService.decode_access_token(token)
        if payload is None:
            raise credentials_exception
        user_id = payload.get("user_id")
        username = payload.get("username")
        if user_id is None or username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Return user information
    return {"user_id": int(user_id), "username": username}

# Dependency to get optional current user (for endpoints that work with or without auth)
async def get_optional_user(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token if provided, otherwise return None"""
    try:
        payload = AuthService.decode_access_token(token)
        if payload is None:
            return None
        user_id = payload.get("user_id")
        username = payload.get("username")
        if user_id is None or username is None:
            return None
        return {"user_id": int(user_id), "username": username}
    except JWTError:
        return None
    except Exception as e:
        logger.error(f"Error getting optional user: {e}")
        return None