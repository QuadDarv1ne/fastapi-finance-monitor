"""Authentication manager for WebSocket connections"""

from typing import Optional
import logging
from jose import JWTError, jwt
import os
import secrets

logger = logging.getLogger(__name__)

class AuthManager:
    """Управление аутентификацией"""
    
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    ALGORITHM = "HS256"
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[str]:
        """
        Verify JWT token and return client ID if valid
        
        Args:
            token: JWT token to verify
            
        Returns:
            Client ID if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            client_id = payload.get("sub")
            if isinstance(client_id, str):
                return client_id
            return None
        except JWTError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None