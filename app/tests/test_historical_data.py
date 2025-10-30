"""Tests for historical data functionality"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.data_fetcher import DataFetcher


class TestHistoricalData:
    """Test suite for historical data functionality"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.data_fetcher = DataFetcher()
    
    def test_convert_period_to_days(self):
        """Test converting period strings to days"""
        from app.api.routes import _convert_period_to_days
        
        # Test various period conversions
        assert _convert_period_to_days("1d") == 1
        assert _convert_period_to_days("5d") == 5
        assert _convert_period_to_days("1mo") == 30
        assert _convert_period_to_days("3mo") == 90
        assert _convert_period_to_days("6mo") == 180
        assert _convert_period_to_days("1y") == 365
        assert _convert_period_to_days("2y") == 730
        assert _convert_period_to_days("5y") == 1825
        assert _convert_period_to_days("10y") == 3650
        assert _convert_period_to_days("ytd") == 365
        assert _convert_period_to_days("max") == 3650
        
        # Test default fallback
        assert _convert_period_to_days("unknown") == 30
    
    @patch('app.services.data_fetcher.yf.Ticker')
    def test_get_stock_data_with_custom_period(self, mock_ticker):
        """Test getting stock data with custom period and interval"""
        async def test_async():
            # Mock Yahoo Finance response
            mock_history = Mock()
            mock_history.empty = False
            mock_history.__getitem__ = Mock(return_value=Mock(iloc=Mock(return_value=150.0)))
            mock_history.columns = ['Close', 'Open', 'High', 'Low', 'Volume']
            mock_history.iterrows = Mock(return_value=enumerate([
                (Mock(), {'Open': 149.0, 'High': 151.0, 'Low': 148.0, 'Close': 150.0, 'Volume': 1000000})
            ]))
            mock_history.max = Mock(return_value=151.0)
            mock_history.min = Mock(return_value=148.0)
            
            mock_ticker_instance = Mock()
            mock_ticker_instance.history = Mock(return_value=mock_history)
            mock_ticker.return_value = mock_ticker_instance
            
            # Test with custom period and interval
            result = await self.data_fetcher.get_stock_data("AAPL", period="1mo", interval="1d")
            
            # Assertions
            assert result is not None
            assert result["symbol"] == "AAPL"
            assert "chart_data" in result
            assert len(result["chart_data"]) > 0
            
            # Verify the ticker was called with correct parameters
            mock_ticker_instance.history.assert_called_once_with("1mo", "1d")
        
        asyncio.run(test_async())
    
    def test_get_crypto_historical_data(self):
        """Test getting crypto historical data"""
        async def test_async():
            # This is a placeholder test - in a real implementation,
            # we would mock the CoinGecko API response
            pass
        
        asyncio.run(test_async())


if __name__ == "__main__":
    pytest.main([__file__])