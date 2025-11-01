"""Metrics collection service for WebSocket system monitoring"""

from typing import Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Global metrics collector instance
metrics_collector = None

class MetricsCollector:
    """Сбор метрик системы"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.start_time = datetime.now()
    
    @classmethod
    def get_instance(cls):
        """Get global metrics collector instance"""
        global metrics_collector
        if metrics_collector is None:
            metrics_collector = cls()
        return metrics_collector
    
    def record_metric(self, metric_name: str, value: int = 1) -> None:
        """
        Record a metric value
        
        Args:
            metric_name: Name of the metric to record
            value: Value to add to the metric (default: 1)
        """
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get all metrics statistics
        
        Returns:
            Dictionary with all metrics
        """
        # Add uptime information
        uptime = datetime.now() - self.start_time
        self.metrics["uptime_seconds"] = int(uptime.total_seconds())
        
        return self.metrics.copy()
    
    def increment_connections(self) -> None:
        """Increment total and active connection counts"""
        self.metrics["total_connections"] += 1
        self.metrics["active_connections"] += 1
    
    def decrement_connections(self) -> None:
        """Decrement active connection count"""
        self.metrics["active_connections"] -= 1
        if self.metrics["active_connections"] < 0:
            self.metrics["active_connections"] = 0
    
    def record_message_sent(self) -> None:
        """Record a message sent"""
        self.metrics["messages_sent"] += 1
    
    def record_message_received(self) -> None:
        """Record a message received"""
        self.metrics["messages_received"] += 1
    
    def record_error(self) -> None:
        """Record an error"""
        self.metrics["errors"] += 1
    
    def record_cache_hit(self) -> None:
        """Record a cache hit"""
        self.metrics["cache_hits"] += 1
    
    def record_cache_miss(self) -> None:
        """Record a cache miss"""
        self.metrics["cache_misses"] += 1