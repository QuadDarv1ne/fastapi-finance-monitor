"""Tests for the monitoring service"""

import pytest
import time
from app.services.monitoring_service import MonitoringService


def test_monitoring_service_initialization():
    """Test monitoring service initialization"""
    monitoring_service = MonitoringService()
    
    # Check that metrics are initialized correctly
    assert monitoring_service.metrics["request_count"] == 0
    assert monitoring_service.metrics["error_count"] == 0
    assert monitoring_service.metrics["response_times"] == []
    assert monitoring_service.metrics["active_connections"] == 0
    assert monitoring_service.metrics["cache_hits"] == 0
    assert monitoring_service.metrics["cache_misses"] == 0


def test_increment_request_count():
    """Test incrementing request count"""
    monitoring_service = MonitoringService()
    
    # Initial count should be 0
    assert monitoring_service.metrics["request_count"] == 0
    
    # Increment request count
    monitoring_service.increment_request_count()
    assert monitoring_service.metrics["request_count"] == 1
    
    # Increment again
    monitoring_service.increment_request_count()
    assert monitoring_service.metrics["request_count"] == 2


def test_increment_error_count():
    """Test incrementing error count"""
    monitoring_service = MonitoringService()
    
    # Initial count should be 0
    assert monitoring_service.metrics["error_count"] == 0
    
    # Increment error count
    monitoring_service.increment_error_count()
    assert monitoring_service.metrics["error_count"] == 1
    
    # Increment again
    monitoring_service.increment_error_count()
    assert monitoring_service.metrics["error_count"] == 2


def test_record_response_time():
    """Test recording response times"""
    monitoring_service = MonitoringService()
    
    # Initially should be empty
    assert monitoring_service.metrics["response_times"] == []
    
    # Record some response times
    monitoring_service.record_response_time(0.1)
    monitoring_service.record_response_time(0.2)
    monitoring_service.record_response_time(0.15)
    
    assert len(monitoring_service.metrics["response_times"]) == 3
    assert monitoring_service.metrics["response_times"][0] == 0.1
    assert monitoring_service.metrics["response_times"][1] == 0.2
    assert monitoring_service.metrics["response_times"][2] == 0.15


def test_response_time_limit():
    """Test that response times are limited to prevent memory issues"""
    monitoring_service = MonitoringService()
    
    # Add more than 1000 response times
    for i in range(1010):
        monitoring_service.record_response_time(float(i) / 1000)
    
    # Should only keep the last 1000
    assert len(monitoring_service.metrics["response_times"]) == 1000
    assert monitoring_service.metrics["response_times"][0] == 1.0 / 1000
    assert monitoring_service.metrics["response_times"][-1] == 1009.0 / 1000


def test_active_connections():
    """Test active connections tracking"""
    monitoring_service = MonitoringService()
    
    # Initial count should be 0
    assert monitoring_service.metrics["active_connections"] == 0
    
    # Increment connections
    monitoring_service.increment_active_connections()
    assert monitoring_service.metrics["active_connections"] == 1
    
    monitoring_service.increment_active_connections()
    assert monitoring_service.metrics["active_connections"] == 2
    
    # Decrement connections
    monitoring_service.decrement_active_connections()
    assert monitoring_service.metrics["active_connections"] == 1
    
    # Decrement below zero should stay at zero
    monitoring_service.decrement_active_connections()
    assert monitoring_service.metrics["active_connections"] == 0
    
    monitoring_service.decrement_active_connections()
    assert monitoring_service.metrics["active_connections"] == 0


def test_cache_metrics():
    """Test cache hit/miss tracking"""
    monitoring_service = MonitoringService()
    
    # Initial counts should be 0
    assert monitoring_service.metrics["cache_hits"] == 0
    assert monitoring_service.metrics["cache_misses"] == 0
    
    # Increment cache hits
    monitoring_service.increment_cache_hit()
    monitoring_service.increment_cache_hit()
    assert monitoring_service.metrics["cache_hits"] == 2
    assert monitoring_service.metrics["cache_misses"] == 0
    
    # Increment cache misses
    monitoring_service.increment_cache_miss()
    monitoring_service.increment_cache_miss()
    monitoring_service.increment_cache_miss()
    assert monitoring_service.metrics["cache_hits"] == 2
    assert monitoring_service.metrics["cache_misses"] == 3


def test_cache_hit_ratio():
    """Test cache hit ratio calculation"""
    monitoring_service = MonitoringService()
    
    # With no cache requests, ratio should be 0
    metrics = monitoring_service.get_application_metrics()
    assert metrics["cache_hit_ratio"] == 0
    
    # Add some hits and misses
    monitoring_service.increment_cache_hit()
    monitoring_service.increment_cache_hit()
    monitoring_service.increment_cache_miss()
    
    metrics = monitoring_service.get_application_metrics()
    assert metrics["cache_hit_ratio"] == 0.6667  # 2 hits / 3 total


def test_average_response_time():
    """Test average response time calculation"""
    monitoring_service = MonitoringService()
    
    # With no response times, average should be 0
    metrics = monitoring_service.get_application_metrics()
    assert metrics["average_response_time"] == 0
    
    # Add some response times
    monitoring_service.record_response_time(0.1)
    monitoring_service.record_response_time(0.2)
    monitoring_service.record_response_time(0.3)
    
    metrics = monitoring_service.get_application_metrics()
    assert metrics["average_response_time"] == 0.2  # (0.1 + 0.2 + 0.3) / 3


def test_application_metrics():
    """Test application metrics calculation"""
    monitoring_service = MonitoringService()
    
    # Test initial metrics
    metrics = monitoring_service.get_application_metrics()
    assert "request_count" in metrics
    assert "error_count" in metrics
    assert "average_response_time" in metrics
    assert "active_connections" in metrics
    assert "cache_hits" in metrics
    assert "cache_misses" in metrics
    assert "cache_hit_ratio" in metrics
    assert "uptime_seconds" in metrics


def test_get_all_metrics():
    """Test getting all metrics"""
    monitoring_service = MonitoringService()
    
    all_metrics = monitoring_service.get_all_metrics()
    
    assert "timestamp" in all_metrics
    assert "system" in all_metrics
    assert "application" in all_metrics
    
    # Check that system metrics are present
    assert isinstance(all_metrics["system"], dict)
    
    # Check that application metrics are present
    assert isinstance(all_metrics["application"], dict)
    assert "request_count" in all_metrics["application"]
    assert "error_count" in all_metrics["application"]


if __name__ == "__main__":
    test_monitoring_service_initialization()
    test_increment_request_count()
    test_increment_error_count()
    test_record_response_time()
    test_response_time_limit()
    test_active_connections()
    test_cache_metrics()
    test_cache_hit_ratio()
    test_average_response_time()
    test_application_metrics()
    test_get_all_metrics()
    print("All monitoring service tests passed!")