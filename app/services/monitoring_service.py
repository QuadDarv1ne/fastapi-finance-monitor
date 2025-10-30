"""Monitoring service for tracking application performance and health"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psutil
import json
import os

# Configure logging
logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring application performance and health"""
    
    def __init__(self):
        self.metrics = {
            "request_count": 0,
            "error_count": 0,
            "response_times": [],
            "active_connections": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.start_time = datetime.now()
    
    def increment_request_count(self):
        """Increment the request counter"""
        self.metrics["request_count"] += 1
    
    def increment_error_count(self):
        """Increment the error counter"""
        self.metrics["error_count"] += 1
    
    def record_response_time(self, response_time: float):
        """Record a response time"""
        self.metrics["response_times"].append(response_time)
        # Keep only the last 1000 response times to prevent memory issues
        if len(self.metrics["response_times"]) > 1000:
            self.metrics["response_times"] = self.metrics["response_times"][-1000:]
    
    def increment_active_connections(self):
        """Increment active connections counter"""
        self.metrics["active_connections"] += 1
    
    def decrement_active_connections(self):
        """Decrement active connections counter"""
        self.metrics["active_connections"] = max(0, self.metrics["active_connections"] - 1)
    
    def increment_cache_hit(self):
        """Increment cache hit counter"""
        self.metrics["cache_hits"] += 1
    
    def increment_cache_miss(self):
        """Increment cache miss counter"""
        self.metrics["cache_misses"] += 1
    
    def get_system_metrics(self) -> Dict:
        """Get system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_percent": memory.percent,
                "disk_total": disk.total,
                "disk_free": disk.free,
                "disk_percent": (disk.total - disk.free) / disk.total * 100
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    def get_application_metrics(self) -> Dict:
        """Get application-level metrics"""
        # Calculate average response time
        avg_response_time = 0
        if self.metrics["response_times"]:
            avg_response_time = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        
        # Calculate cache hit ratio
        cache_hit_ratio = 0
        total_cache_requests = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        if total_cache_requests > 0:
            cache_hit_ratio = self.metrics["cache_hits"] / total_cache_requests
        
        uptime = datetime.now() - self.start_time
        
        return {
            "request_count": self.metrics["request_count"],
            "error_count": self.metrics["error_count"],
            "average_response_time": round(avg_response_time, 4),
            "active_connections": self.metrics["active_connections"],
            "cache_hits": self.metrics["cache_hits"],
            "cache_misses": self.metrics["cache_misses"],
            "cache_hit_ratio": round(cache_hit_ratio, 4),
            "uptime_seconds": uptime.total_seconds()
        }
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics combined"""
        return {
            "timestamp": datetime.now().isoformat(),
            "system": self.get_system_metrics(),
            "application": self.get_application_metrics()
        }
    
    async def log_periodic_metrics(self):
        """Log metrics periodically"""
        while True:
            try:
                metrics = self.get_all_metrics()
                logger.info(f"Periodic metrics: {json.dumps(metrics)}")
                await asyncio.sleep(60)  # Log every minute
            except Exception as e:
                logger.error(f"Error logging periodic metrics: {e}")
                await asyncio.sleep(60)
    
    def log_request(self, method: str, path: str, status_code: int, response_time: float):
        """Log a request with its details"""
        logger.info(f"Request: {method} {path} - Status: {status_code} - Time: {response_time:.4f}s")
    
    def log_error(self, error_type: str, message: str, traceback: Optional[str] = None):
        """Log an error with details"""
        error_info = {
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if traceback:
            error_info["traceback"] = traceback
        
        logger.error(f"Application error: {json.dumps(error_info)}")


# Global monitoring service instance
monitoring_service = MonitoringService()


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance"""
    return monitoring_service