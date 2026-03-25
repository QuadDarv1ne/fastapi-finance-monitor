"""Tests for the portfolio API endpoints"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth_service import AuthService, get_current_user
from app.services.portfolio_service import get_portfolio_service


class TestPortfolioEndpoints:
    """Test suite for portfolio API endpoints"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Clear any cached data from previous tests FIRST
        app.dependency_overrides.clear()
        self.client = TestClient(app)
        # Create a valid test token
        self.test_token = AuthService.create_access_token(
            data={"user_id": 999, "username": "testuser_unique"}
        )

    def teardown_method(self):
        """Tear down test fixtures after each test method."""
        # Clear dependency overrides
        app.dependency_overrides.clear()

    def test_get_user_portfolios(self):
        """Test getting user portfolios"""
        # Mock current user via dependency override
        async def mock_get_current_user():
            return {"user_id": 999, "username": "testuser_unique"}

        app.dependency_overrides[get_current_user] = mock_get_current_user

        # Mock portfolio service with async function
        async def mock_get_portfolios(user_id):
            return [
                {"id": 1, "name": "My Portfolio", "created_at": "2023-01-01T00:00:00"}
            ]

        mock_portfolio_service = Mock()
        mock_portfolio_service.get_user_portfolios = mock_get_portfolios

        # Override dependency (accept db_service parameter that route passes)
        app.dependency_overrides[get_portfolio_service] = lambda db_service=None: mock_portfolio_service

        # Test getting portfolios
        response = self.client.get(
            "/api/portfolios", headers={"Authorization": f"Bearer {self.test_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "portfolios" in data
        assert data["count"] == 1
        assert data["portfolios"][0]["name"] == "My Portfolio"

        # Clean up
        app.dependency_overrides.clear()

    def test_create_portfolio(self):
        """Test creating a new portfolio"""
        # Mock current user via dependency override
        async def mock_get_current_user():
            return {"user_id": 1, "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_get_current_user

        # Mock portfolio service with async functions
        async def mock_create_portfolio(*args, **kwargs):
            return {
                "portfolio_id": 1,
                "name": "My Portfolio",
                "created_at": "2023-01-01T00:00:00",
            }

        mock_portfolio_service = Mock()
        mock_portfolio_service.create_portfolio = mock_create_portfolio

        # Override dependency (accept db_service parameter that route passes)
        app.dependency_overrides[get_portfolio_service] = lambda db_service=None: mock_portfolio_service

        # Test creating a portfolio
        response = self.client.post(
            "/api/portfolios",
            json={"name": "My Portfolio"},
            headers={"Authorization": f"Bearer {self.test_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "portfolio_id" in data
        assert data["name"] == "My Portfolio"

        # Clean up
        app.dependency_overrides.clear()

    def test_get_portfolio(self):
        """Test getting a specific portfolio"""
        # Mock current user via dependency override
        async def mock_get_current_user():
            return {"user_id": 1, "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_get_current_user

        # Mock portfolio service
        async def mock_get_portfolios(user_id):
            return [{"id": 1}]

        async def mock_get_portfolio(portfolio_id):
            return {
                "id": 1,
                "name": "My Portfolio",
                "created_at": "2023-01-01T00:00:00",
                "items": [],
            }

        mock_portfolio_service = Mock()
        mock_portfolio_service.get_user_portfolios = mock_get_portfolios
        mock_portfolio_service.get_portfolio = mock_get_portfolio

        # Override dependency (accept db_service parameter that route passes)
        app.dependency_overrides[get_portfolio_service] = lambda db_service=None: mock_portfolio_service

        # Test getting a specific portfolio
        response = self.client.get(
            "/api/portfolios/1", headers={"Authorization": f"Bearer {self.test_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Portfolio"
        assert "items" in data

        # Clean up
        app.dependency_overrides.clear()

    def test_get_advanced_portfolio_analytics(self):
        """Test getting advanced portfolio analytics"""
        # Mock current user via dependency override
        async def mock_get_current_user():
            return {"user_id": 1, "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_get_current_user

        # Mock portfolio service
        async def mock_get_portfolios(user_id):
            return [{"id": 1}]

        async def mock_get_analytics(portfolio_id):
            return {
                "basic_performance": {
                    "total_value": 10000,
                    "total_cost": 9000,
                    "total_gain": 1000,
                    "total_gain_percent": 11.11,
                },
                "value_at_risk": {"value_at_risk": 500, "confidence_level": 0.95, "time_horizon": 1},
                "portfolio_beta": {"beta": 1.2, "benchmark": "SPY"},
                "sortino_ratio": {"sortino_ratio": 1.5, "risk_free_rate": 0.02},
            }

        mock_portfolio_service = Mock()
        mock_portfolio_service.get_user_portfolios = mock_get_portfolios
        mock_portfolio_service.get_advanced_portfolio_analytics = mock_get_analytics

        # Override dependency (accept db_service parameter that route passes)
        app.dependency_overrides[get_portfolio_service] = lambda db_service=None: mock_portfolio_service

        # Test getting advanced analytics
        response = self.client.get(
            "/api/portfolios/1/analytics/advanced",
            headers={"Authorization": f"Bearer {self.test_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "basic_performance" in data
        assert "value_at_risk" in data
        assert "portfolio_beta" in data
        assert "sortino_ratio" in data

        # Clean up
        app.dependency_overrides.clear()

    def test_get_portfolio_value_at_risk(self):
        """Test getting portfolio Value at Risk"""
        # Mock current user via dependency override
        async def mock_get_current_user():
            return {"user_id": 1, "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_get_current_user

        # Mock portfolio service
        async def mock_get_portfolios(user_id):
            return [{"id": 1}]

        async def mock_calculate_var(*args, **kwargs):
            return {
                "value_at_risk": 500,
                "confidence_level": 0.95,
                "time_horizon": 1,
                "portfolio_value": 10000,
            }

        mock_portfolio_service = Mock()
        mock_portfolio_service.get_user_portfolios = mock_get_portfolios
        mock_portfolio_service.calculate_value_at_risk = mock_calculate_var

        # Override dependency (accept db_service parameter that route passes)
        app.dependency_overrides[get_portfolio_service] = lambda db_service=None: mock_portfolio_service

        # Test getting VaR
        response = self.client.get(
            "/api/portfolios/1/risk/var", headers={"Authorization": f"Bearer {self.test_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "value_at_risk" in data
        assert "confidence_level" in data
        assert "time_horizon" in data
        assert data["confidence_level"] == 0.95

        # Clean up
        app.dependency_overrides.clear()

    def test_get_portfolio_beta(self):
        """Test getting portfolio beta"""
        # Mock current user via dependency override
        async def mock_get_current_user():
            return {"user_id": 1, "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_get_current_user

        # Mock portfolio service
        async def mock_get_portfolios(user_id):
            return [{"id": 1}]

        async def mock_calculate_beta(*args, **kwargs):
            return {
                "beta": 1.2,
                "benchmark": "SPY",
            }

        mock_portfolio_service = Mock()
        mock_portfolio_service.get_user_portfolios = mock_get_portfolios
        mock_portfolio_service.calculate_portfolio_beta = mock_calculate_beta

        # Override dependency (accept db_service parameter that route passes)
        app.dependency_overrides[get_portfolio_service] = lambda db_service=None: mock_portfolio_service

        # Test getting beta
        response = self.client.get(
            "/api/portfolios/1/risk/beta", headers={"Authorization": f"Bearer {self.test_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "beta" in data
        assert "benchmark" in data
        assert data["benchmark"] == "SPY"

        # Clean up
        app.dependency_overrides.clear()

    def test_get_portfolio_sortino_ratio(self):
        """Test getting portfolio Sortino ratio"""
        # Mock current user via dependency override
        async def mock_get_current_user():
            return {"user_id": 1, "username": "testuser"}

        app.dependency_overrides[get_current_user] = mock_get_current_user

        # Mock portfolio service
        async def mock_get_portfolios(user_id):
            return [{"id": 1}]

        async def mock_calculate_sortino(*args, **kwargs):
            return {
                "sortino_ratio": 1.5,
                "risk_free_rate": 0.02,
            }

        mock_portfolio_service = Mock()
        mock_portfolio_service.get_user_portfolios = mock_get_portfolios
        mock_portfolio_service.calculate_sortino_ratio = mock_calculate_sortino

        # Override dependency (accept db_service parameter that route passes)
        app.dependency_overrides[get_portfolio_service] = lambda db_service=None: mock_portfolio_service

        # Test getting Sortino ratio
        response = self.client.get(
            "/api/portfolios/1/risk/sortino", headers={"Authorization": f"Bearer {self.test_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "sortino_ratio" in data
        assert "risk_free_rate" in data
        assert data["risk_free_rate"] == 0.02

        # Clean up
        app.dependency_overrides.clear()


if __name__ == "__main__":
    pytest.main([__file__])
