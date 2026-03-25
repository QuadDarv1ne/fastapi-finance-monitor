"""2FA TOTP Authentication Service

This module provides Two-Factor Authentication using Time-based One-Time Passwords (TOTP).
Compatible with Google Authenticator, Authy, Microsoft Authenticator, and other TOTP apps.

Key Features:
- TOTP secret generation
- QR code generation for easy setup
- OTP verification
- Backup codes generation and verification
- Rate limiting for OTP attempts

Dependencies:
- pyotp: TOTP library
- qrcode: QR code generation (optional, for setup)
"""

import base64
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import pyotp

from app.config import SecurityConfig

logger = logging.getLogger(__name__)


class TwoFactorAuthService:
    """Service for 2FA TOTP operations"""

    # TOTP configuration
    ISSUER_NAME = "FastAPI Finance Monitor"
    DIGITS = 6  # Standard TOTP digits
    INTERVAL = 30  # TOTP validity period in seconds (pyotp uses 'interval' not 'period')

    @classmethod
    def generate_secret(cls) -> str:
        """Generate a new TOTP secret key
        
        Returns:
            str: Base32-encoded secret key (32 characters)
        """
        secret = pyotp.random_base32()
        logger.info("Generated new TOTP secret")
        return secret

    @classmethod
    def get_provisioning_uri(cls, username: str, email: str, secret: str) -> str:
        """Generate provisioning URI for QR code
        
        Args:
            username: User's username
            email: User's email address
            secret: TOTP secret key
            
        Returns:
            str: otpauth:// URI for QR code generation
        """
        totp = pyotp.TOTP(secret, digits=cls.DIGITS, interval=cls.INTERVAL)
        uri = totp.provisioning_uri(
            name=email,
            issuer_name=cls.ISSUER_NAME
        )
        logger.info(f"Generated provisioning URI for user {username}")
        return uri

    @classmethod
    def generate_qr_code_data(cls, username: str, email: str, secret: str) -> str:
        """Generate QR code data as base64 image
        
        Args:
            username: User's username
            email: User's email address  
            secret: TOTP secret key
            
        Returns:
            str: Base64-encoded PNG image data URI
        """
        try:
            import qrcode
            from io import BytesIO
            
            uri = cls.get_provisioning_uri(username, email, secret)
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except ImportError:
            # qrcode not installed, return URI instead
            logger.warning("qrcode library not installed, returning URI instead of QR code")
            return cls.get_provisioning_uri(username, email, secret)

    @classmethod
    def verify_otp(cls, secret: str, otp: str, window: int = 1) -> bool:
        """Verify a TOTP code
        
        Args:
            secret: User's TOTP secret key
            otp: OTP code to verify (6 digits)
            window: Number of intervals to check before/after current (default: 1)
                   This allows for clock skew between server and client
            
        Returns:
            bool: True if OTP is valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret, digits=cls.DIGITS, interval=cls.INTERVAL)
            is_valid = totp.verify(otp, valid_window=window)
            
            if is_valid:
                logger.info("OTP verified successfully")
            else:
                logger.warning("OTP verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return False

    @classmethod
    def generate_backup_codes(cls, count: int = 10) -> list[str]:
        """Generate backup codes for account recovery
        
        Args:
            count: Number of backup codes to generate (default: 10)
            
        Returns:
            list[str]: List of backup codes (8 characters each)
        """
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_urlsafe(6).upper()
            codes.append(code)
        
        logger.info(f"Generated {count} backup codes")
        return codes

    @classmethod
    def verify_backup_code(cls, backup_codes: list[str], code: str) -> bool:
        """Verify a backup code
        
        Args:
            backup_codes: List of valid backup codes (hashed)
            code: Backup code to verify
            
        Returns:
            bool: True if code is valid, False otherwise
        """
        try:
            # Simple comparison (in production, should hash codes)
            if code.upper() in [c.upper() for c in backup_codes]:
                logger.info("Backup code verified successfully")
                return True
            logger.warning("Backup code verification failed")
            return False
        except Exception as e:
            logger.error(f"Error verifying backup code: {e}")
            return False

    @classmethod
    def get_current_otp(cls, secret: str) -> str:
        """Get current TOTP code (for testing/debugging only)
        
        WARNING: Only use for testing or debugging. Never expose in production.
        
        Args:
            secret: TOTP secret key
            
        Returns:
            str: Current 6-digit OTP code
        """
        totp = pyotp.TOTP(secret, digits=cls.DIGITS, interval=cls.INTERVAL)
        return totp.now()

    @classmethod
    def is_2fa_setup_required(cls, is_2fa_enabled: bool, totp_secret: Optional[str]) -> bool:
        """Check if 2FA setup is required for user
        
        Args:
            is_2fa_enabled: Whether 2FA is enabled for user
            totp_secret: User's stored TOTP secret
            
        Returns:
            bool: True if 2FA setup is required
        """
        # 2FA setup required if enabled but no secret exists
        return is_2fa_enabled and not totp_secret


# Rate limiting for 2FA attempts
_2fa_attempts: dict[str, list[float]] = {}


def is_2fa_attempt_allowed(user_id: int) -> bool:
    """Check if 2FA attempt is allowed (rate limiting)
    
    Args:
        user_id: User ID to check
        
    Returns:
        bool: True if attempt is allowed
    """
    now = datetime.now(timezone.utc).timestamp()
    window = 300  # 5 minutes
    
    # Clean old attempts
    if str(user_id) in _2fa_attempts:
        _2fa_attempts[str(user_id)] = [
            attempt for attempt in _2fa_attempts[str(user_id)]
            if now - attempt < window
        ]
    
    # Check if max attempts exceeded
    max_attempts = 5
    return len(_2fa_attempts.get(str(user_id), [])) < max_attempts


def record_2fa_attempt(user_id: int):
    """Record a 2FA attempt
    
    Args:
        user_id: User ID
    """
    now = datetime.now(timezone.utc).timestamp()
    if str(user_id) not in _2fa_attempts:
        _2fa_attempts[str(user_id)] = []
    _2fa_attempts[str(user_id)].append(now)


def get_2fa_attempts(user_id: int) -> int:
    """Get number of recent 2FA attempts
    
    Args:
        user_id: User ID
        
    Returns:
        int: Number of attempts in last 5 minutes
    """
    now = datetime.now(timezone.utc).timestamp()
    window = 300
    
    if str(user_id) not in _2fa_attempts:
        return 0
    
    return len([
        attempt for attempt in _2fa_attempts[str(user_id)]
        if now - attempt < window
    ])
