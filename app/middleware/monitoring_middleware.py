"""Monitoring middleware for tracking requests and performance"""

import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.services.monitoring_service import get_monitoring_service

logger = logging.getLogger(__name__)
monitoring_service = get_monitoring_service()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring requests and performance"""
    
    async def dispatch(self, request: Request, call_next):
        """Process each request and track metrics"""
        # Record start time
        start_time = time.time()
        
        # Increment request counter
        monitoring_service.increment_request_count()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Record response time
            monitoring_service.record_response_time(response_time)
            
            # Log the request
            monitoring_service.log_request(
                method=request.method,
                path=str(request.url),
                status_code=response.status_code,
                response_time=response_time
            )
            
            return response
            
        except Exception as e:
            # Increment error counter
            monitoring_service.increment_error_count()
            
            # Log the error
            monitoring_service.log_error(
                error_type=type(e).__name__,
                message=str(e)
            )
            
            # Re-raise the exception
            raise