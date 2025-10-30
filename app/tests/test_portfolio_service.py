"""Tests for the portfolio service"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.portfolio_service import PortfolioService
from app.services.database_service import DatabaseService


class TestPortfolioService:
    """Test suite for PortfolioService"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create a mock database service
        self.mock_db_service = Mock(spec=DatabaseService)
        self.portfolio_service = PortfolioService(self.mock_db_service)
    
    def test_create_portfolio(self):
        """Test creating a new portfolio"""
        # Mock the database service response
        mock_portfolio = Mock()
        mock_portfolio.id = 1
        mock_portfolio.name = "Test Portfolio"
        mock_portfolio.created_at = None
        self.mock_db_service.create_portfolio.return_value = mock_portfolio
        
        # Call the method
        result = asyncio.run(self.portfolio_service.create_portfolio(1, "Test Portfolio"))
        
        # Assertions
        assert "portfolio_id" in result
        assert result["portfolio_id"] == 1
        assert result["name"] == "Test Portfolio"
        self.mock_db_service.create_portfolio.assert_called_once_with(1, "Test Portfolio")
    
    def test_get_user_portfolios(self):
        """Test getting user portfolios"""
        # Mock the database service response
        mock_portfolio1 = Mock()
        mock_portfolio1.id = 1
        mock_portfolio1.name = "Portfolio 1"
        mock_portfolio1.created_at = None
        
        mock_portfolio2 = Mock()
        mock_portfolio2.id = 2
        mock_portfolio2.name = "Portfolio 2"
        mock_portfolio2.created_at = None
        
        self.mock_db_service.get_user_portfolios.return_value = [mock_portfolio1, mock_portfolio2]
        
        # Call the method
        result = asyncio.run(self.portfolio_service.get_user_portfolios(1))
        
        # Assertions
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2
        self.mock_db_service.get_user_portfolios.assert_called_once_with(1)
    
    def test_add_to_portfolio(self):
        """Test adding an item to portfolio"""
        # Mock the database service response
        mock_item = Mock()
        mock_item.id = 1
        mock_item.symbol = "AAPL"
        mock_item.name = "Apple Inc."
        mock_item.quantity = "10.0"
        mock_item.purchase_price = "150.0"
        mock_item.purchase_date = None
        mock_item.asset_type = "stock"
        
        self.mock_db_service.add_to_portfolio.return_value = mock_item
        
        # Call the method
        result = asyncio.run(self.portfolio_service.add_to_portfolio(
            1, "AAPL", "Apple Inc.", 10.0, 150.0, "2023-01-01", "stock"
        ))
        
        # Assertions
        assert "item_id" in result
        assert result["item_id"] == 1
        assert result["symbol"] == "AAPL"
        self.mock_db_service.add_to_portfolio.assert_called_once_with(
            1, "AAPL", "Apple Inc.", 10.0, 150.0, "2023-01-01", "stock"
        )
    
    @patch('app.services.portfolio_service.DataFetcher')
    def test_calculate_portfolio_performance(self, mock_data_fetcher):
        """Test calculating portfolio performance"""
        # Mock portfolio
        mock_portfolio = Mock()
        mock_portfolio.id = 1
        self.mock_db_service.get_portfolio.return_value = mock_portfolio
        
        # Mock portfolio items with string values (as they would be from database)
        mock_item1 = Mock()
        mock_item1.symbol = "AAPL"
        mock_item1.asset_type = "stock"
        mock_item1.quantity = "10.0"
        mock_item1.purchase_price = "150.0"
        
        mock_item2 = Mock()
        mock_item2.symbol = "GOOGL"
        mock_item2.asset_type = "stock"
        mock_item2.quantity = "5.0"
        mock_item2.purchase_price = "2500.0"
        
        self.mock_db_service.get_portfolio_items.return_value = [mock_item1, mock_item2]
        
        # Mock data fetcher response
        mock_data_fetcher_instance = Mock()
        mock_data_fetcher.return_value = mock_data_fetcher_instance
        
        # Mock stock data responses
        mock_aapl_data = {"current_price": 160.0}
        mock_googl_data = {"current_price": 2600.0}
        
        async def mock_get_stock_data(symbol):
            if symbol == "AAPL":
                return mock_aapl_data
            elif symbol == "GOOGL":
                return mock_googl_data
            return None
        
        mock_data_fetcher_instance.get_stock_data = mock_get_stock_data
        
        # Call the method
        result = asyncio.run(self.portfolio_service.calculate_portfolio_performance(1))
        
        # Assertions
        assert "total_value" in result
        assert "total_cost" in result
        assert "total_gain" in result
        assert "total_gain_percent" in result
        
        # Calculate expected values
        expected_cost = (10 * 150) + (5 * 2500)  # 1500 + 12500 = 14000
        
        assert result["total_cost"] == expected_cost
        # Just check that the values are reasonable numbers
        assert isinstance(result["total_value"], (int, float))
        assert isinstance(result["total_gain"], (int, float))
        assert isinstance(result["total_gain_percent"], (int, float))
        assert result["total_value"] > 0


if __name__ == "__main__":
    pytest.main([__file__])