"""Tests for the metrics collector service"""

import pytest
import time
from app.services.metrics_collector import MetricsCollector


class TestMetricsCollector:
    """Test suite for MetricsCollector"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a new instance for each test to avoid interference
        self.metrics_collector = MetricsCollector()
        # Reset the global instance
        global metrics_collector
        metrics_collector = None
    
    def test_metrics_collector_initialization(self):
        """Test MetricsCollector initialization"""
        assert isinstance(self.metrics_collector.metrics, dict)
        assert self.metrics_collector.metrics["total_connections"] == 0
        assert self.metrics_collector.metrics["active_connections"] == 0
        assert self.metrics_collector.metrics["messages_sent"] == 0
        assert self.metrics_collector.metrics["messages_received"] == 0
        assert self.metrics_collector.metrics["errors"] == 0
        assert self.metrics_collector.metrics["cache_hits"] == 0
        assert self.metrics_collector.metrics["cache_misses"] == 0
        assert "start_time" in dir(self.metrics_collector)
    
    def test_get_instance(self):
        """Test getting singleton instance"""
        # Reset global instance
        global metrics_collector
        metrics_collector = None
        
        # Get instance
        instance1 = MetricsCollector.get_instance()
        instance2 = MetricsCollector.get_instance()
        
        # Should be the same instance
        assert instance1 is instance2
        assert isinstance(instance1, MetricsCollector)
    
    def test_record_metric(self):
        """Test recording a metric"""
        initial_messages_sent = self.metrics_collector.metrics["messages_sent"]
        
        # Record a metric
        self.metrics_collector.record_metric("messages_sent", 5)
        
        # Check that metric was recorded
        assert self.metrics_collector.metrics["messages_sent"] == initial_messages_sent + 5
        
        # Record another metric
        self.metrics_collector.record_metric("errors", 2)
        assert self.metrics_collector.metrics["errors"] == 2
    
    def test_record_metric_invalid_name(self):
        """Test recording an invalid metric name"""
        initial_metrics = self.metrics_collector.metrics.copy()
        
        # Try to record an invalid metric
        self.metrics_collector.record_metric("invalid_metric", 5)
        
        # Metrics should be unchanged
        assert self.metrics_collector.metrics == initial_metrics
    
    def test_get_stats(self):
        """Test getting statistics"""
        # Record some metrics
        self.metrics_collector.record_metric("messages_sent", 10)
        self.metrics_collector.record_metric("messages_received", 8)
        self.metrics_collector.record_metric("errors", 1)
        
        # Get stats
        stats = self.metrics_collector.get_stats()
        
        # Check that stats contain expected fields
        assert "total_connections" in stats
        assert "active_connections" in stats
        assert "messages_sent" in stats
        assert "messages_received" in stats
        assert "errors" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "uptime_seconds" in stats
        
        # Check specific values
        assert stats["messages_sent"] == 10
        assert stats["messages_received"] == 8
        assert stats["errors"] == 1
        assert stats["uptime_seconds"] >= 0
    
    def test_increment_connections(self):
        """Test incrementing connections"""
        initial_total = self.metrics_collector.metrics["total_connections"]
        initial_active = self.metrics_collector.metrics["active_connections"]
        
        # Increment connections
        self.metrics_collector.increment_connections()
        
        # Check that both counters were incremented
        assert self.metrics_collector.metrics["total_connections"] == initial_total + 1
        assert self.metrics_collector.metrics["active_connections"] == initial_active + 1
    
    def test_decrement_connections(self):
        """Test decrementing connections"""
        # First increment to have something to decrement
        self.metrics_collector.increment_connections()
        self.metrics_collector.increment_connections()
        
        initial_active = self.metrics_collector.metrics["active_connections"]
        
        # Decrement connections
        self.metrics_collector.decrement_connections()
        
        # Check that active connections were decremented
        assert self.metrics_collector.metrics["active_connections"] == initial_active - 1
    
    def test_decrement_connections_below_zero(self):
        """Test that active connections can't go below zero"""
        # Decrement connections when already at zero
        self.metrics_collector.decrement_connections()
        
        # Active connections should stay at zero
        assert self.metrics_collector.metrics["active_connections"] == 0
    
    def test_record_message_sent(self):
        """Test recording a message sent"""
        initial_count = self.metrics_collector.metrics["messages_sent"]
        
        # Record a message sent
        self.metrics_collector.record_message_sent()
        
        # Check that counter was incremented
        assert self.metrics_collector.metrics["messages_sent"] == initial_count + 1
    
    def test_record_message_received(self):
        """Test recording a message received"""
        initial_count = self.metrics_collector.metrics["messages_received"]
        
        # Record a message received
        self.metrics_collector.record_message_received()
        
        # Check that counter was incremented
        assert self.metrics_collector.metrics["messages_received"] == initial_count + 1
    
    def test_record_error(self):
        """Test recording an error"""
        initial_count = self.metrics_collector.metrics["errors"]
        
        # Record an error
        self.metrics_collector.record_error()
        
        # Check that counter was incremented
        assert self.metrics_collector.metrics["errors"] == initial_count + 1
    
    def test_record_cache_hit(self):
        """Test recording a cache hit"""
        initial_count = self.metrics_collector.metrics["cache_hits"]
        
        # Record a cache hit
        self.metrics_collector.record_cache_hit()
        
        # Check that counter was incremented
        assert self.metrics_collector.metrics["cache_hits"] == initial_count + 1
    
    def test_record_cache_miss(self):
        """Test recording a cache miss"""
        initial_count = self.metrics_collector.metrics["cache_misses"]
        
        # Record a cache miss
        self.metrics_collector.record_cache_miss()
        
        # Check that counter was incremented
        assert self.metrics_collector.metrics["cache_misses"] == initial_count + 1


if __name__ == "__main__":
    pytest.main([__file__])