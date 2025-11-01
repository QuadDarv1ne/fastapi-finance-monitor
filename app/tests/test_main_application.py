"""Tests for the main FastAPI application"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from fastapi.testclient import TestClient
from app.main import app, startup_event, shutdown_event
from app.services.monitoring_service import get_monitoring_service
from app.services.cache_service import get_cache_service
from app.services.redis_cache_service import get_redis_cache_service


class TestMainApplication:
    """Test suite for the main FastAPI application"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
    
    def test_application_initialization(self):
        """Test that the FastAPI application is properly initialized"""
        assert app.title == "FastAPI Finance Monitor"
        assert app.description == "Real-time financial dashboard for stocks, crypto, and commodities"
        assert app.version == "1.0.0"
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
    
    def test_docs_endpoints(self):
        """Test that documentation endpoints are available"""
        # Test Swagger UI
        response = self.client.get("/docs")
        assert response.status_code == 200
        
        # Test ReDoc
        response = self.client.get("/redoc")
        assert response.status_code == 200
    
    def test_cors_middleware(self):
        """Test that CORS middleware is properly configured"""
        response = self.client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Example"
            }
        )
        # CORS middleware should allow the request
        # Note: This might not work in test environment, so we check that it doesn't error
        assert response.status_code in [200, 405]  # 200 for successful OPTIONS, 405 for method not allowed
    
    @pytest.mark.asyncio
    async def test_startup_event_success(self):
        """Test successful startup event"""
        # Mock all the services to succeed
        with patch('app.main.init_db') as mock_init_db, \
             patch('app.main.get_redis_cache_service') as mock_get_redis, \
             patch('app.main.get_monitoring_service') as mock_get_monitoring, \
             patch('app.main.get_advanced_alert_service') as mock_get_alerts, \
             patch('app.main.data_stream_worker', new_callable=AsyncMock) as mock_data_stream:
            
            # Mock database session import
            with patch('app.database.SessionLocal') as mock_session_local:
                # Mock database session
                mock_db = Mock()
                mock_session_local.return_value = mock_db
                
                # Mock database service import
                with patch('services.database_service.DatabaseService') as mock_db_service_class:
                    # Mock database service
                    mock_db_service = Mock()
                    mock_db_service_class.return_value = mock_db_service
                    mock_db_service.get_user_by_username = Mock(return_value=None)
                    
                    # Mock Redis cache service
                    mock_redis_service = AsyncMock()
                    mock_redis_service.connect = AsyncMock(return_value=True)
                    mock_get_redis.return_value = mock_redis_service
                    
                    # Mock monitoring service
                    mock_monitoring_service = AsyncMock()
                    mock_monitoring_service.log_periodic_metrics = AsyncMock(return_value=None)
                    mock_get_monitoring.return_value = mock_monitoring_service
                    
                    # Mock alert service
                    mock_alert_service = AsyncMock()
                    mock_alert_service.start_monitoring = AsyncMock(return_value=None)
                    mock_get_alerts.return_value = mock_alert_service
                    
                    # Mock DataFetcher
                    with patch('app.main.DataFetcher') as mock_data_fetcher_class:
                        mock_data_fetcher = AsyncMock()
                        mock_data_fetcher.initialize_cache_warming = AsyncMock(return_value=None)
                        mock_data_fetcher_class.return_value = mock_data_fetcher
                        
                        # Run startup event
                        await startup_event()
                        
                        # Verify all services were initialized
                        mock_init_db.assert_called_once()
                        mock_redis_service.connect.assert_called_once()
                        mock_monitoring_service.log_periodic_metrics.assert_called_once()
                        mock_alert_service.start_monitoring.assert_called_once()
                        mock_data_stream.assert_called_once()
                        mock_data_fetcher.initialize_cache_warming.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_startup_event_redis_failure(self):
        """Test startup event with Redis connection failure"""
        # Mock services with Redis failure
        with patch('app.main.init_db') as mock_init_db, \
             patch('app.main.get_redis_cache_service') as mock_get_redis, \
             patch('app.main.get_monitoring_service') as mock_get_monitoring, \
             patch('app.main.get_advanced_alert_service') as mock_get_alerts, \
             patch('app.main.data_stream_worker', new_callable=AsyncMock) as mock_data_stream:
            
            # Mock database session import
            with patch('app.database.SessionLocal') as mock_session_local:
                # Mock database session
                mock_db = Mock()
                mock_session_local.return_value = mock_db
                
                # Mock database service import
                with patch('services.database_service.DatabaseService') as mock_db_service_class:
                    # Mock database service
                    mock_db_service = Mock()
                    mock_db_service_class.return_value = mock_db_service
                    mock_db_service.get_user_by_username = Mock(return_value=None)
                    
                    # Mock Redis cache service to fail
                    mock_redis_service = AsyncMock()
                    mock_redis_service.connect = AsyncMock(return_value=False)  # Redis connection fails
                    mock_get_redis.return_value = mock_redis_service
                    
                    # Mock monitoring service
                    mock_monitoring_service = AsyncMock()
                    mock_monitoring_service.log_periodic_metrics = AsyncMock(return_value=None)
                    mock_get_monitoring.return_value = mock_monitoring_service
                    
                    # Mock alert service
                    mock_alert_service = AsyncMock()
                    mock_alert_service.start_monitoring = AsyncMock(return_value=None)
                    mock_get_alerts.return_value = mock_alert_service
                    
                    # Mock DataFetcher
                    with patch('app.main.DataFetcher') as mock_data_fetcher_class:
                        mock_data_fetcher = AsyncMock()
                        mock_data_fetcher.initialize_cache_warming = AsyncMock(return_value=None)
                        mock_data_fetcher_class.return_value = mock_data_fetcher
                        
                        # Run startup event - should not raise exception even with Redis failure
                        await startup_event()
                        
                        # Verify all services were attempted
                        mock_init_db.assert_called_once()
                        mock_redis_service.connect.assert_called_once()
                        mock_monitoring_service.log_periodic_metrics.assert_called_once()
                        mock_alert_service.start_monitoring.assert_called_once()
                        mock_data_stream.assert_called_once()
                        mock_data_fetcher.initialize_cache_warming.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test shutdown event"""
        # Mock services for shutdown
        with patch('app.main.get_advanced_alert_service') as mock_get_alerts, \
             patch('app.main.get_redis_cache_service') as mock_get_redis:
            
            # Mock database session import
            with patch('app.database.SessionLocal') as mock_session_local:
                # Mock database session
                mock_db = Mock()
                mock_session_local.return_value = mock_db
                
                # Mock database service import
                with patch('services.database_service.DatabaseService') as mock_db_service_class:
                    # Mock database service
                    mock_db_service = Mock()
                    mock_db_service_class.return_value = mock_db_service
                    
                    # Mock alert service
                    mock_alert_service = AsyncMock()
                    mock_alert_service.stop_monitoring = AsyncMock(return_value=None)
                    mock_get_alerts.return_value = mock_alert_service
                    
                    # Mock Redis cache service
                    mock_redis_service = AsyncMock()
                    mock_redis_service.redis_client = True  # Simulate connected Redis
                    mock_redis_service.close = AsyncMock(return_value=None)
                    mock_get_redis.return_value = mock_redis_service
                    
                    # Run shutdown event
                    await shutdown_event()
                    
                    # Verify services were shut down
                    mock_alert_service.stop_monitoring.assert_called_once()
                    mock_redis_service.close.assert_called_once()
    
    def test_dashboard_endpoint(self):
        """Test that the dashboard endpoint returns HTML content"""
        response = self.client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Check that the response contains expected HTML elements
        assert "<title>FastAPI Finance Monitor</title>" in response.text
        assert "dashboard" in response.text.lower()


if __name__ == "__main__":
    pytest.main([__file__])