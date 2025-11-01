"""Custom exceptions for the FastAPI Finance Monitor application"""

class FinanceMonitorError(Exception):
    """Base exception for all Finance Monitor errors"""
    pass

class DataFetchError(FinanceMonitorError):
    """Exception raised when data fetching fails"""
    pass

class RateLimitError(DataFetchError):
    """Exception raised when rate limits are exceeded"""
    pass

class DataValidationError(DataFetchError):
    """Exception raised when data validation fails"""
    pass

class CacheError(FinanceMonitorError):
    """Exception raised when cache operations fail"""
    pass

class DatabaseError(FinanceMonitorError):
    """Exception raised when database operations fail"""
    pass

class AuthenticationError(FinanceMonitorError):
    """Exception raised when authentication fails"""
    pass

class AuthorizationError(FinanceMonitorError):
    """Exception raised when authorization fails"""
    pass

class ValidationError(FinanceMonitorError):
    """Exception raised when input validation fails"""
    pass

class WebSocketError(FinanceMonitorError):
    """Exception raised when WebSocket operations fail"""
    pass

class ConfigurationError(FinanceMonitorError):
    """Exception raised when configuration is invalid"""
    pass

class ServiceUnavailableError(FinanceMonitorError):
    """Exception raised when a required service is unavailable"""
    pass

class NetworkError(DataFetchError):
    """Exception raised when network operations fail"""
    pass

class TimeoutError(NetworkError):
    """Exception raised when operations timeout"""
    pass