"""Tests for the enhanced portfolio service"""

import pytest
from unittest.mock import Mock, patch
from app.services.portfolio_service import PortfolioService


def test_portfolio_service_initialization():
    """Test portfolio service initialization"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Check that the service is initialized correctly
    assert portfolio_service.db_service == mock_db_service
    assert portfolio_service.data_fetcher is not None


@patch('app.services.portfolio_service.PortfolioService._get_current_price')
def test_calculate_portfolio_performance_enhanced(mock_get_price):
    """Test enhanced portfolio performance calculation"""
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
    
    # Test the enhanced performance calculation
    import asyncio
    
    async def test_async():
        result = await portfolio_service.calculate_portfolio_performance(1)
        return result
    
    result = asyncio.run(test_async())
    
    # Check that the result contains enhanced metrics
    assert isinstance(result, dict)
    assert "total_value" in result
    assert "total_cost" in result
    assert "total_gain" in result
    assert "total_gain_percent" in result
    assert "sharpe_ratio" in result
    assert "max_drawdown" in result
    assert "volatility" in result


@patch('app.services.portfolio_service.PortfolioService._get_current_price')
def test_get_portfolio_history(mock_get_price):
    """Test portfolio history fetching"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Mock portfolio items
    mock_item1 = Mock()
    mock_item1.symbol = "AAPL"
    mock_item1.asset_type = "stock"
    mock_item1.quantity = 10
    mock_item1.purchase_price = 100.0
    
    mock_db_service.get_portfolio_items.return_value = [mock_item1]
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test the history fetching
    import asyncio
    
    async def test_async():
        result = await portfolio_service.get_portfolio_history(1, 30)
        return result
    
    result = asyncio.run(test_async())
    
    # Check that the result contains expected fields
    assert isinstance(result, dict)
    assert "portfolio_id" in result
    assert "days" in result
    assert "history" in result
    assert result["portfolio_id"] == 1
    assert result["days"] == 30


def test_calculate_sharpe_ratio():
    """Test Sharpe ratio calculation"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test data
    holdings_data = [
        {"cost": 1000, "current_value": 1100},
        {"cost": 2000, "current_value": 2200}
    ]
    
    # Test the Sharpe ratio calculation
    import asyncio
    
    async def test_async():
        result = await portfolio_service._calculate_sharpe_ratio(holdings_data)
        return result
    
    result = asyncio.run(test_async())
    
    # Result should be a float or None
    assert isinstance(result, (int, float, type(None)))


def test_calculate_max_drawdown():
    """Test maximum drawdown calculation"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test data
    holdings_data = [
        {"cost": 1000, "current_value": 1100},
        {"cost": 2000, "current_value": 2200}
    ]
    
    # Test the max drawdown calculation
    import asyncio
    
    async def test_async():
        result = await portfolio_service._calculate_max_drawdown(holdings_data)
        return result
    
    result = asyncio.run(test_async())
    
    # Result should be a float or None
    assert isinstance(result, (int, float, type(None)))


def test_calculate_volatility():
    """Test volatility calculation"""
    # Create a mock database service
    mock_db_service = Mock()
    
    # Create portfolio service
    portfolio_service = PortfolioService(mock_db_service)
    
    # Test data
    holdings_data = [
        {"symbol": "AAPL", "current_value": 1100},
        {"symbol": "GOOGL", "current_value": 2200},
        {"symbol": "bitcoin", "current_value": 50000}
    ]
    
    # Test the volatility calculation
    import asyncio
    
    async def test_async():
        result = await portfolio_service._calculate_volatility(holdings_data)
        return result
    
    result = asyncio.run(test_async())
    
    # Result should be a float or None
    assert isinstance(result, (int, float, type(None)))


if __name__ == "__main__":
    test_portfolio_service_initialization()
    print("Enhanced portfolio service tests completed!")