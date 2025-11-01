"""Tests for the advanced portfolio analytics functionality"""

import pytest
from unittest.mock import Mock, patch
from app.services.portfolio_service import PortfolioService


def test_calculate_value_at_risk():
    """Test Value at Risk calculation"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Mock portfolio items
    mock_item1 = Mock()
    mock_item1.symbol = "AAPL"
    mock_item1.asset_type = "stock"
    mock_item1.quantity = 10
    mock_item1.purchase_price = 100.0
    
    mock_item2 = Mock()
    mock_item2.symbol = "GOOGL"
    mock_item2.asset_type = "stock"
    mock_item2.quantity = 5
    mock_item2.purchase_price = 2000.0
    
    mock_db_service.get_portfolio_items.return_value = [mock_item1, mock_item2]
    
    # Mock portfolio
    mock_portfolio = Mock()
    mock_db_service.get_portfolio.return_value = mock_portfolio
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test the VaR calculation
    import asyncio
    
    async def test_async():
        result = await portfolio_service.calculate_value_at_risk(1, confidence_level=0.95, time_horizon=1)
        return result
    
    result = asyncio.run(test_async())
    
    # Check that the result contains expected fields
    assert isinstance(result, dict)
    assert "value_at_risk" in result
    assert "confidence_level" in result
    assert "time_horizon" in result
    assert "portfolio_value" in result
    assert result["confidence_level"] == 0.95
    assert result["time_horizon"] == 1


@patch('app.services.portfolio_service.PortfolioService._get_current_price')
def test_calculate_portfolio_beta(mock_get_price):
    """Test portfolio beta calculation"""
    # Mock the current price fetching
    mock_get_price.return_value = 110.0
    
    # Create a mock database service
    mock_db_service = Mock()
    
    # Mock portfolio items
    mock_item1 = Mock()
    mock_item1.symbol = "AAPL"
    mock_item1.asset_type = "stock"
    mock_item1.quantity = 10
    mock_item1.purchase_price = 100.0
    
    mock_item2 = Mock()
    mock_item2.symbol = "GOOGL"
    mock_item2.asset_type = "stock"
    mock_item2.quantity = 5
    mock_item2.purchase_price = 2000.0
    
    mock_db_service.get_portfolio_items.return_value = [mock_item1, mock_item2]
    
    # Mock portfolio
    mock_portfolio = Mock()
    mock_db_service.get_portfolio.return_value = mock_portfolio
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test the beta calculation
    import asyncio
    
    async def test_async():
        result = await portfolio_service.calculate_portfolio_beta(1, "SPY")
        return result
    
    result = asyncio.run(test_async())
    
    # Check that the result contains expected fields
    assert isinstance(result, dict)
    assert "beta" in result
    assert "benchmark" in result
    assert result["benchmark"] == "SPY"


@patch('app.services.portfolio_service.PortfolioService._get_current_price')
def test_calculate_sortino_ratio(mock_get_price):
    """Test Sortino ratio calculation"""
    # Mock the current price fetching
    mock_get_price.return_value = 110.0
    
    # Create a mock database service
    mock_db_service = Mock()
    
    # Mock portfolio items
    mock_item1 = Mock()
    mock_item1.symbol = "AAPL"
    mock_item1.asset_type = "stock"
    mock_item1.quantity = 10
    mock_item1.purchase_price = 100.0
    
    mock_item2 = Mock()
    mock_item2.symbol = "GOOGL"
    mock_item2.asset_type = "stock"
    mock_item2.quantity = 5
    mock_item2.purchase_price = 2000.0
    
    mock_db_service.get_portfolio_items.return_value = [mock_item1, mock_item2]
    
    # Mock portfolio
    mock_portfolio = Mock()
    mock_db_service.get_portfolio.return_value = mock_portfolio
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test the Sortino ratio calculation
    import asyncio
    
    async def test_async():
        result = await portfolio_service.calculate_sortino_ratio(1, risk_free_rate=0.02)
        return result
    
    result = asyncio.run(test_async())
    
    # Check that the result contains expected fields
    assert isinstance(result, dict)
    assert "sortino_ratio" in result
    assert "risk_free_rate" in result
    assert "average_return" in result
    assert "downside_deviation" in result


@patch('app.services.portfolio_service.PortfolioService._get_current_price')
def test_get_advanced_portfolio_analytics(mock_get_price):
    """Test advanced portfolio analytics"""
    # Mock the current price fetching
    mock_get_price.return_value = 110.0
    
    # Create a mock database service
    mock_db_service = Mock()
    
    # Mock portfolio items
    mock_item1 = Mock()
    mock_item1.symbol = "AAPL"
    mock_item1.asset_type = "stock"
    mock_item1.quantity = 10
    mock_item1.purchase_price = 100.0
    
    mock_item2 = Mock()
    mock_item2.symbol = "GOOGL"
    mock_item2.asset_type = "stock"
    mock_item2.quantity = 5
    mock_item2.purchase_price = 2000.0
    
    mock_db_service.get_portfolio_items.return_value = [mock_item1, mock_item2]
    
    # Mock portfolio
    mock_portfolio = Mock()
    mock_db_service.get_portfolio.return_value = mock_portfolio
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test the advanced analytics
    import asyncio
    
    async def test_async():
        result = await portfolio_service.get_advanced_portfolio_analytics(1)
        return result
    
    result = asyncio.run(test_async())
    
    # Check that the result contains expected sections
    assert isinstance(result, dict)
    assert "basic_performance" in result
    assert "value_at_risk" in result
    assert "portfolio_beta" in result
    assert "sortino_ratio" in result


def test_value_at_risk_edge_cases():
    """Test VaR calculation with edge cases"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Mock empty portfolio
    mock_db_service.get_portfolio_items.return_value = []
    
    # Mock portfolio
    mock_portfolio = Mock()
    mock_db_service.get_portfolio.return_value = mock_portfolio
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test VaR with empty portfolio
    import asyncio
    
    async def test_async():
        result = await portfolio_service.calculate_value_at_risk(1)
        return result
    
    result = asyncio.run(test_async())
    
    # Should return 0 VaR for empty portfolio
    assert isinstance(result, dict)
    assert "value_at_risk" in result
    assert result["value_at_risk"] == 0


def test_portfolio_beta_edge_cases():
    """Test portfolio beta with edge cases"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Mock empty portfolio
    mock_db_service.get_portfolio_items.return_value = []
    
    # Mock portfolio
    mock_portfolio = Mock()
    mock_db_service.get_portfolio.return_value = mock_portfolio
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test beta with empty portfolio
    import asyncio
    
    async def test_async():
        result = await portfolio_service.calculate_portfolio_beta(1)
        return result
    
    result = asyncio.run(test_async())
    
    # Should return default beta of 1.0 for empty portfolio
    assert isinstance(result, dict)
    assert "beta" in result
    assert result["beta"] == 1.0


if __name__ == "__main__":
    test_calculate_value_at_risk()
    test_calculate_portfolio_beta()
    test_calculate_sortino_ratio()
    test_get_advanced_portfolio_analytics()
    test_value_at_risk_edge_cases()
    test_portfolio_beta_edge_cases()
    print("All advanced portfolio analytics tests passed!")