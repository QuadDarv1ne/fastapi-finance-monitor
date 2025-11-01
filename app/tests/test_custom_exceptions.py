"""Tests for custom exceptions"""

import pytest
from app.exceptions.custom_exceptions import (
    FinanceMonitorError, DataFetchError, RateLimitError, DataValidationError,
    CacheError, DatabaseError, AuthenticationError, AuthorizationError,
    ValidationError, WebSocketError, ConfigurationError, ServiceUnavailableError,
    NetworkError, TimeoutError
)


class TestCustomExceptions:
    """Test suite for custom exceptions"""
    
    def test_finance_monitor_error(self):
        """Test FinanceMonitorError base exception"""
        exception = FinanceMonitorError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, Exception)
    
    def test_data_fetch_error(self):
        """Test DataFetchError exception"""
        exception = DataFetchError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_rate_limit_error(self):
        """Test RateLimitError exception"""
        exception = RateLimitError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, DataFetchError)
    
    def test_data_validation_error(self):
        """Test DataValidationError exception"""
        exception = DataValidationError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, DataFetchError)
    
    def test_cache_error(self):
        """Test CacheError exception"""
        exception = CacheError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_database_error(self):
        """Test DatabaseError exception"""
        exception = DatabaseError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_authentication_error(self):
        """Test AuthenticationError exception"""
        exception = AuthenticationError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_authorization_error(self):
        """Test AuthorizationError exception"""
        exception = AuthorizationError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_validation_error(self):
        """Test ValidationError exception"""
        exception = ValidationError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_websocket_error(self):
        """Test WebSocketError exception"""
        exception = WebSocketError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_configuration_error(self):
        """Test ConfigurationError exception"""
        exception = ConfigurationError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError exception"""
        exception = ServiceUnavailableError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, FinanceMonitorError)
    
    def test_network_error(self):
        """Test NetworkError exception"""
        exception = NetworkError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, DataFetchError)
    
    def test_timeout_error(self):
        """Test TimeoutError exception"""
        exception = TimeoutError("Test error")
        assert str(exception) == "Test error"
        assert isinstance(exception, NetworkError)


if __name__ == "__main__":
    pytest.main([__file__])