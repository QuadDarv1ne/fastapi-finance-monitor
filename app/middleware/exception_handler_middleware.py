"""Centralized exception handling middleware for the FastAPI Finance Monitor application"""

import logging
import traceback
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.exceptions.custom_exceptions import (
    FinanceMonitorError, DataFetchError, RateLimitError, DataValidationError,
    CacheError, DatabaseError, AuthenticationError, AuthorizationError,
    ValidationError, WebSocketError, ConfigurationError, ServiceUnavailableError,
    NetworkError, TimeoutError
)

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized exception handling"""
    
    async def dispatch(self, request: Request, call_next):
        """Process each request with centralized exception handling"""
        try:
            # Process the request
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            # Handle FastAPI HTTP exceptions (pass through)
            logger.info(f"HTTP exception: {e.status_code} - {e.detail}")
            raise
            
        except RateLimitError as e:
            # Handle rate limit errors
            logger.warning(f"Rate limit exceeded for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": str(e),
                    "type": "RateLimitError"
                }
            )
            
        except TimeoutError as e:
            # Handle timeout errors
            logger.error(f"Timeout error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "Request timeout",
                    "message": str(e),
                    "type": "TimeoutError"
                }
            )
            
        except NetworkError as e:
            # Handle network errors
            logger.error(f"Network error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Network error",
                    "message": str(e),
                    "type": "NetworkError"
                }
            )
            
        except DataFetchError as e:
            # Handle data fetching errors
            logger.error(f"Data fetch error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={
                    "error": "Data fetch error",
                    "message": str(e),
                    "type": "DataFetchError"
                }
            )
            
        except DataValidationError as e:
            # Handle data validation errors
            logger.warning(f"Data validation error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Data validation error",
                    "message": str(e),
                    "type": "DataValidationError"
                }
            )
            
        except ValidationError as e:
            # Handle general validation errors
            logger.warning(f"Validation error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation error",
                    "message": str(e),
                    "type": "ValidationError"
                }
            )
            
        except AuthenticationError as e:
            # Handle authentication errors
            logger.warning(f"Authentication error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Authentication failed",
                    "message": str(e),
                    "type": "AuthenticationError"
                }
            )
            
        except AuthorizationError as e:
            # Handle authorization errors
            logger.warning(f"Authorization error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Access forbidden",
                    "message": str(e),
                    "type": "AuthorizationError"
                }
            )
            
        except DatabaseError as e:
            # Handle database errors
            logger.error(f"Database error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Database error",
                    "message": "An error occurred while accessing the database",
                    "type": "DatabaseError"
                }
            )
            
        except CacheError as e:
            # Handle cache errors
            logger.error(f"Cache error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Cache error",
                    "message": "An error occurred while accessing the cache",
                    "type": "CacheError"
                }
            )
            
        except WebSocketError as e:
            # Handle WebSocket errors
            logger.error(f"WebSocket error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "WebSocket error",
                    "message": str(e),
                    "type": "WebSocketError"
                }
            )
            
        except ConfigurationError as e:
            # Handle configuration errors
            logger.critical(f"Configuration error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Configuration error",
                    "message": "Application is misconfigured",
                    "type": "ConfigurationError"
                }
            )
            
        except ServiceUnavailableError as e:
            # Handle service unavailable errors
            logger.error(f"Service unavailable for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "error": "Service unavailable",
                    "message": str(e),
                    "type": "ServiceUnavailableError"
                }
            )
            
        except FinanceMonitorError as e:
            # Handle other FinanceMonitor errors
            logger.error(f"FinanceMonitor error for {request.method} {request.url}: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Application error",
                    "message": str(e),
                    "type": type(e).__name__
                }
            )
            
        except Exception as e:
            # Handle all other unexpected errors
            logger.critical(f"Unhandled exception for {request.method} {request.url}: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "type": "InternalServerError"
                }
            )