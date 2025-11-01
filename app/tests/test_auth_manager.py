"""Tests for the auth manager service"""

import pytest
from unittest.mock import patch
from app.services.auth_manager import AuthManager
from app.services.auth_service import AuthService
from jose import JWTError


class TestAuthManager:
    """Test suite for AuthManager"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Store original secret key
        self.original_secret_key = AuthManager.SECRET_KEY
    
    def teardown_method(self):
        """Tear down test fixtures after each test method."""
        # Restore original secret key
        AuthManager.SECRET_KEY = self.original_secret_key
    
    def test_auth_manager_initialization(self):
        """Test AuthManager initialization"""
        assert hasattr(AuthManager, 'SECRET_KEY')
        assert hasattr(AuthManager, 'ALGORITHM')
        assert AuthManager.ALGORITHM == "HS256"
    
    def test_verify_token_valid_token(self):
        """Test verifying a valid token"""
        # Create a valid token using jose.jwt directly to match AuthManager expectations
        from jose import jwt
        from datetime import datetime, timedelta
        
        client_id = "test_client_123"
        payload = {
            "sub": client_id,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, AuthManager.SECRET_KEY, algorithm=AuthManager.ALGORITHM)
        
        # Verify the token
        result = AuthManager.verify_token(token)
        assert result == client_id
    
    def test_verify_token_invalid_token(self):
        """Test verifying an invalid token"""
        invalid_token = "invalid.token.here"
        
        # Verify the invalid token
        result = AuthManager.verify_token(invalid_token)
        assert result is None
    
    def test_verify_token_malformed_token(self):
        """Test verifying a malformed token"""
        malformed_token = "malformed.token"
        
        # Verify the malformed token
        result = AuthManager.verify_token(malformed_token)
        assert result is None
    
    def test_verify_token_none_input(self):
        """Test verifying a None token"""
        result = AuthManager.verify_token(None)  # type: ignore
        assert result is None
    
    def test_verify_token_empty_string(self):
        """Test verifying an empty string token"""
        result = AuthManager.verify_token("")
        assert result is None
    
    def test_verify_token_expired_token(self):
        """Test verifying an expired token"""
        from jose import jwt
        import time
        from datetime import datetime, timedelta
        
        # Create an expired token
        client_id = "test_client_123"
        expired_payload = {
            "sub": client_id,
            "exp": datetime.utcnow() - timedelta(hours=1)  # 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, AuthManager.SECRET_KEY, algorithm=AuthManager.ALGORITHM)
        
        # Verify the expired token
        result = AuthManager.verify_token(expired_token)
        assert result is None
    
    def test_verify_token_invalid_client_id(self):
        """Test verifying a token with invalid client ID"""
        from jose import jwt
        from datetime import datetime, timedelta
        
        # Create a token with invalid client ID
        invalid_payload = {
            "sub": 12345,  # Not a string
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(invalid_payload, AuthManager.SECRET_KEY, algorithm=AuthManager.ALGORITHM)
        
        # Verify the token
        result = AuthManager.verify_token(token)
        assert result is None
    
    @patch('app.services.auth_manager.jwt.decode')
    def test_verify_token_jwt_error(self, mock_decode):
        """Test verifying a token that raises JWTError"""
        # Mock jwt.decode to raise JWTError
        mock_decode.side_effect = JWTError("Token invalid")
        
        token = "some.token.here"
        result = AuthManager.verify_token(token)
        assert result is None
    
    @patch('app.services.auth_manager.jwt.decode')
    def test_verify_token_general_exception(self, mock_decode):
        """Test verifying a token that raises a general exception"""
        # Mock jwt.decode to raise a general exception
        mock_decode.side_effect = Exception("Something went wrong")
        
        token = "some.token.here"
        result = AuthManager.verify_token(token)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])