"""Authentication manager for WebSocket connections"""

import logging

from jose import JWTError, jwt

# Import security configuration
from app.config import SecurityConfig

logger = logging.getLogger(__name__)


class AuthManager:
    """Управление аутентификацией"""

    # Use centralized security configuration
    SECRET_KEY = SecurityConfig.SECRET_KEY
    ALGORITHM = SecurityConfig.ALGORITHM

    @classmethod
    def verify_token(cls, token: str) -> str | None:
        """
        Verify JWT token and return client ID if valid

        Args:
            token: JWT token to verify

        Returns:
            Client ID if token is valid, None otherwise
        """
        try:
            # Verify with audience and issuer validation
            payload = jwt.decode(
                token,
                cls.SECRET_KEY,
                algorithms=[cls.ALGORITHM],
                audience=SecurityConfig.JWT_AUDIENCE,
                issuer=SecurityConfig.JWT_ISSUER,
            )
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
