"""Tests for the portfolio API endpoints"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock
from app.main import app
from app.services.auth_service import AuthService


class TestPortfolioEndpoints:
    """Test suite for portfolio API endpoints"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
        # Create a valid test token
        self.test_token = AuthService.create_access_token(
            data={"user_id": 1, "username": "testuser"}
        )
    
    @patch('app.api.routes.get_current_user')
    @patch('app.api.routes.get_portfolio_service')
    def test_create_portfolio(self, mock_get_portfolio_service, mock_get_current_user):
        """Test creating a new portfolio"""
        # Mock current user
        mock_get_current_user.return_value = {"user_id": 1, "username": "testuser"}
        
        # Mock portfolio service
        mock_portfolio_service = AsyncMock()
        mock_portfolio_service.create_portfolio.return_value = {
            "portfolio_id": 1,
            "name": "My Portfolio",
            "created_at": "2023-01-01T00:00:00"
        }
        mock_get_portfolio_service.return_value = mock_portfolio_service
        
        # Test creating a portfolio
        response = self.client.post(
            "/api/portfolios",
            json={"name": "My Portfolio"},
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "portfolio_id" in data
        assert data["name"] == "My Portfolio"
    
    @patch('app.api.routes.get_current_user')
    @patch('app.api.routes.get_portfolio_service')
    def test_get_user_portfolios(self, mock_get_portfolio_service, mock_get_current_user):
        """Test getting user portfolios"""
        # Mock current user
        mock_get_current_user.return_value = {"user_id": 1, "username": "testuser"}
        
        # Mock portfolio service
        mock_portfolio_service = AsyncMock()
        mock_portfolio_service.get_user_portfolios.return_value = [
            {
                "id": 1,
                "name": "My Portfolio",
                "created_at": "2023-01-01T00:00:00"
            }
        ]
        mock_get_portfolio_service.return_value = mock_portfolio_service
        
        # Test getting portfolios
        response = self.client.get(
            "/api/portfolios",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "portfolios" in data
        assert data["count"] == 1
        assert data["portfolios"][0]["name"] == "My Portfolio"
    
    @patch('app.api.routes.get_current_user')
    @patch('app.api.routes.get_portfolio_service')
    def test_get_portfolio(self, mock_get_portfolio_service, mock_get_current_user):
        """Test getting a specific portfolio"""
        # Mock current user
        mock_get_current_user.return_value = {"user_id": 1, "username": "testuser"}
        
        # Mock portfolio service
        mock_portfolio_service = AsyncMock()
        mock_portfolio_service.get_user_portfolios.return_value = [{"id": 1}]
        mock_portfolio_service.get_portfolio.return_value = {
            "id": 1,
            "name": "My Portfolio",
            "created_at": "2023-01-01T00:00:00",
            "items": []
        }
        mock_get_portfolio_service.return_value = mock_portfolio_service
        
        # Test getting a specific portfolio
        response = self.client.get(
            "/api/portfolios/1",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Portfolio"
        assert "items" in data
    
    @patch('app.api.routes.get_current_user')
    @patch('app.api.routes.get_portfolio_service')
    def test_get_advanced_portfolio_analytics(self, mock_get_portfolio_service, mock_get_current_user):
        """Test getting advanced portfolio analytics"""
        # Mock current user
        mock_get_current_user.return_value = {"user_id": 1, "username": "testuser"}
        
        # Mock portfolio service
        mock_portfolio_service = AsyncMock()
        mock_portfolio_service.get_user_portfolios.return_value = [{"id": 1}]
        mock_portfolio_service.get_advanced_portfolio_analytics.return_value = {
            "basic_performance": {
                "total_value": 10000,
                "total_cost": 9000,
                "total_gain": 1000,
                "total_gain_percent": 11.11
            },
            "value_at_risk": {
                "value_at_risk": 500,
                "confidence_level": 0.95,
                "time_horizon": 1
            },
            "portfolio_beta": {
                "beta": 1.2,
                "benchmark": "SPY"
            },
            "sortino_ratio": {
                "sortino_ratio": 1.5,
                "risk_free_rate": 0.02
            }
        }
        mock_get_portfolio_service.return_value = mock_portfolio_service
        
        # Test getting advanced analytics
        response = self.client.get(
            "/api/portfolios/1/analytics/advanced",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "basic_performance" in data
        assert "value_at_risk" in data
        assert "portfolio_beta" in data
        assert "sortino_ratio" in data
    
    @patch('app.api.routes.get_current_user')
    @patch('app.api.routes.get_portfolio_service')
    def test_get_portfolio_value_at_risk(self, mock_get_portfolio_service, mock_get_current_user):
        """Test getting portfolio Value at Risk"""
        # Mock current user
        mock_get_current_user.return_value = {"user_id": 1, "username": "testuser"}
        
        # Mock portfolio service
        mock_portfolio_service = AsyncMock()
        mock_portfolio_service.get_user_portfolios.return_value = [{"id": 1}]
        mock_portfolio_service.calculate_value_at_risk.return_value = {
            "value_at_risk": 500,
            "confidence_level": 0.95,
            "time_horizon": 1,
            "portfolio_value": 10000
        }
        mock_get_portfolio_service.return_value = mock_portfolio_service
        
        # Test getting VaR
        response = self.client.get(
            "/api/portfolios/1/risk/var",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "value_at_risk" in data
        assert "confidence_level" in data
        assert "time_horizon" in data
        assert data["confidence_level"] == 0.95
    
    @patch('app.api.routes.get_current_user')
    @patch('app.api.routes.get_portfolio_service')
    def test_get_portfolio_beta(self, mock_get_portfolio_service, mock_get_current_user):
        """Test getting portfolio beta"""
        # Mock current user
        mock_get_current_user.return_value = {"user_id": 1, "username": "testuser"}
        
        # Mock portfolio service
        mock_portfolio_service = AsyncMock()
        mock_portfolio_service.get_user_portfolios.return_value = [{"id": 1}]
        mock_portfolio_service.calculate_portfolio_beta.return_value = {
            "beta": 1.2,
            "benchmark": "SPY"
        }
        mock_get_portfolio_service.return_value = mock_portfolio_service
        
        # Test getting beta
        response = self.client.get(
            "/api/portfolios/1/risk/beta",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "beta" in data
        assert "benchmark" in data
        assert data["benchmark"] == "SPY"
    
    @patch('app.api.routes.get_current_user')
    @patch('app.api.routes.get_portfolio_service')
    def test_get_portfolio_sortino_ratio(self, mock_get_portfolio_service, mock_get_current_user):
        """Test getting portfolio Sortino ratio"""
        # Mock current user
        mock_get_current_user.return_value = {"user_id": 1, "username": "testuser"}
        
        # Mock portfolio service
        mock_portfolio_service = AsyncMock()
        mock_portfolio_service.get_user_portfolios.return_value = [{"id": 1}]
        mock_portfolio_service.calculate_sortino_ratio.return_value = {
            "sortino_ratio": 1.5,
            "risk_free_rate": 0.02
        }
        mock_get_portfolio_service.return_value = mock_portfolio_service
        
        # Test getting Sortino ratio
        response = self.client.get(
            "/api/portfolios/1/risk/sortino",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sortino_ratio" in data
        assert "risk_free_rate" in data
        assert data["risk_free_rate"] == 0.02


if __name__ == "__main__":
    pytest.main([__file__])