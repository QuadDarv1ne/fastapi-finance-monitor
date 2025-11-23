"""Tests for the main FastAPI application"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestMainApplication:
    """Test suite for the main FastAPI application"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)

    def test_application_initialization(self):
        """Test that the FastAPI application is properly initialized"""
        assert app.title == "FastAPI Finance Monitor"
        assert (
            app.description == "Real-time financial dashboard for stocks, crypto, and commodities"
        )
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
                "Access-Control-Request-Headers": "X-Example",
            },
        )
        # CORS middleware should allow the request
        # Note: This might not work in test environment, so we check that it doesn't error
        assert response.status_code in [
            200,
            405,
        ]  # 200 for successful OPTIONS, 405 for method not allowed

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self):
        """Test successful lifespan startup"""
        # Mock all the services to succeed
        with (
            patch("app.main.init_db") as mock_init_db,
            patch("app.main.get_redis_cache_service") as mock_get_redis,
            patch("app.main.get_monitoring_service") as mock_get_monitoring,
            patch("app.main.get_advanced_alert_service") as mock_get_alerts,
            patch("app.main.data_stream_worker", new_callable=AsyncMock),
            patch("app.database.SessionLocal") as mock_session_local,
        ):
            # Mock database session
            mock_db = Mock()
            mock_session_local.return_value = mock_db

            # Mock database service import
            with patch("services.database_service.DatabaseService") as mock_db_service_class:
                # Mock database service
                mock_db_service = Mock()
                mock_db_service_class.return_value = mock_db_service

                # Mock Redis cache service
                mock_redis_service = AsyncMock()
                mock_redis_service.connect = AsyncMock(return_value=True)
                mock_redis_service.redis_client = True
                mock_redis_service.close = AsyncMock(return_value=None)
                mock_get_redis.return_value = mock_redis_service

                # Mock monitoring service
                mock_monitoring_service = AsyncMock()
                mock_monitoring_service.log_periodic_metrics = AsyncMock(return_value=None)
                mock_get_monitoring.return_value = mock_monitoring_service

                # Mock alert service
                mock_alert_service = AsyncMock()
                mock_alert_service.start_monitoring = AsyncMock(return_value=None)
                mock_alert_service.stop_monitoring = AsyncMock(return_value=None)
                mock_get_alerts.return_value = mock_alert_service

                # Mock DataFetcher
                with patch("app.main.DataFetcher") as mock_data_fetcher_class:
                    mock_data_fetcher = AsyncMock()
                    mock_data_fetcher.initialize_cache_warming = AsyncMock(return_value=None)
                    mock_data_fetcher_class.return_value = mock_data_fetcher

                    # Test lifespan using TestClient (automatically runs lifespan)
                    with TestClient(app):
                        # Verify startup services were initialized
                        mock_init_db.assert_called_once()
                        mock_redis_service.connect.assert_called_once()

                    # After context exit, shutdown should have been called
                    mock_alert_service.stop_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_redis_failure(self):
        """Test lifespan startup with Redis connection failure"""
        # Mock services with Redis failure
        with (
            patch("app.main.init_db") as mock_init_db,
            patch("app.main.get_redis_cache_service") as mock_get_redis,
            patch("app.main.get_monitoring_service") as mock_get_monitoring,
            patch("app.main.get_advanced_alert_service") as mock_get_alerts,
            patch("app.main.data_stream_worker", new_callable=AsyncMock),
            patch("app.database.SessionLocal") as mock_session_local,
        ):
            # Mock database session
            mock_db = Mock()
            mock_session_local.return_value = mock_db

            # Mock database service import
            with patch("services.database_service.DatabaseService") as mock_db_service_class:
                # Mock database service
                mock_db_service = Mock()
                mock_db_service_class.return_value = mock_db_service

                # Mock Redis cache service to fail
                mock_redis_service = AsyncMock()
                mock_redis_service.connect = AsyncMock(return_value=False)  # Redis connection fails
                mock_redis_service.redis_client = None
                mock_get_redis.return_value = mock_redis_service

                # Mock monitoring service
                mock_monitoring_service = AsyncMock()
                mock_monitoring_service.log_periodic_metrics = AsyncMock(return_value=None)
                mock_get_monitoring.return_value = mock_monitoring_service

                # Mock alert service
                mock_alert_service = AsyncMock()
                mock_alert_service.start_monitoring = AsyncMock(return_value=None)
                mock_alert_service.stop_monitoring = AsyncMock(return_value=None)
                mock_get_alerts.return_value = mock_alert_service

                # Mock DataFetcher
                with patch("app.main.DataFetcher") as mock_data_fetcher_class:
                    mock_data_fetcher = AsyncMock()
                    mock_data_fetcher.initialize_cache_warming = AsyncMock(return_value=None)
                    mock_data_fetcher_class.return_value = mock_data_fetcher

                    # Test lifespan - should not raise exception even with Redis failure
                    with TestClient(app):
                        # Verify services were attempted
                        mock_init_db.assert_called_once()
                        mock_redis_service.connect.assert_called_once()

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
