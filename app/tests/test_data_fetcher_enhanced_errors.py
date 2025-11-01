"""Enhanced tests for the data fetcher with focus on error conditions and edge cases"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock
from app.services.data_fetcher import DataFetcher
from app.exceptions.custom_exceptions import DataFetchError, RateLimitError, DataValidationError, NetworkError, TimeoutError


class TestDataFetcherEnhancedErrors:
    """Enhanced test suite for DataFetcher error handling"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.data_fetcher = DataFetcher()
    
    @pytest.mark.asyncio
    async def test_get_stock_data_with_validation_error(self):
        """Test stock data fetching with validation error"""
        # Mock the internal method to raise a validation error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance', 
                         AsyncMock(side_effect=DataValidationError("Invalid data"))):
            result = await self.data_fetcher.get_stock_data("INVALID")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "INVALID"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_get_stock_data_with_rate_limit_error(self):
        """Test stock data fetching with rate limit error"""
        # Mock the internal method to raise a rate limit error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance', 
                         AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))):
            result = await self.data_fetcher.get_stock_data("AAPL")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "AAPL"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_get_stock_data_with_network_error(self):
        """Test stock data fetching with network error"""
        # Mock the internal method to raise a network error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance', 
                         AsyncMock(side_effect=NetworkError("Network error"))):
            result = await self.data_fetcher.get_stock_data("AAPL")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "AAPL"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_get_stock_data_with_timeout_error(self):
        """Test stock data fetching with timeout error"""
        # Mock the internal method to raise a timeout error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance', 
                         AsyncMock(side_effect=TimeoutError("Timeout error"))):
            result = await self.data_fetcher.get_stock_data("AAPL")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "AAPL"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_get_crypto_data_with_validation_error(self):
        """Test crypto data fetching with validation error"""
        # Mock the internal method to raise a validation error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_coingecko', 
                         AsyncMock(side_effect=DataValidationError("Invalid data"))):
            result = await self.data_fetcher.get_crypto_data("invalidcoin")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "invalidcoin"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_get_crypto_data_with_rate_limit_error(self):
        """Test crypto data fetching with rate limit error"""
        # Mock the internal method to raise a rate limit error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_coingecko', 
                         AsyncMock(side_effect=RateLimitError("Rate limit exceeded"))):
            result = await self.data_fetcher.get_crypto_data("bitcoin")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "bitcoin"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_get_crypto_data_with_network_error(self):
        """Test crypto data fetching with network error"""
        # Mock the internal method to raise a network error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_coingecko', 
                         AsyncMock(side_effect=NetworkError("Network error"))):
            result = await self.data_fetcher.get_crypto_data("bitcoin")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "bitcoin"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_get_crypto_data_with_timeout_error(self):
        """Test crypto data fetching with timeout error"""
        # Mock the internal method to raise a timeout error
        with patch('app.services.data_fetcher.DataFetcher._fetch_from_coingecko', 
                         AsyncMock(side_effect=TimeoutError("Timeout error"))):
            result = await self.data_fetcher.get_crypto_data("bitcoin")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "bitcoin"
            assert "current_price" in result
    
    @pytest.mark.asyncio
    async def test_fetch_from_yahoo_finance_empty_data(self):
        """Test _fetch_from_yahoo_finance with empty data"""
        # Mock empty DataFrame
        mock_df = Mock()
        mock_df.empty = True
        
        with patch('app.services.data_fetcher.yf.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history = Mock(return_value=mock_df)
            mock_ticker_class.return_value = mock_ticker
            
            result = await self.data_fetcher._fetch_from_yahoo_finance("INVALID")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_from_yahoo_finance_missing_columns(self):
        """Test _fetch_from_yahoo_finance with missing required columns"""
        # Mock DataFrame with missing columns
        mock_df = Mock()
        mock_df.empty = False
        mock_df.columns = ['Volume', 'Adj Close']  # Missing 'Close' and 'Open'
        
        with patch('app.services.data_fetcher.yf.Ticker') as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history = Mock(return_value=mock_df)
            mock_ticker_class.return_value = mock_ticker
            
            with pytest.raises(DataValidationError):
                await self.data_fetcher._fetch_from_yahoo_finance("AAPL")
    
    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_empty_data(self):
        """Test _fetch_from_coingecko with empty data"""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={})
        
        with patch('app.services.data_fetcher.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get = Mock(return_value=mock_response)
            mock_session_class.return_value = mock_session
            
            result = await self.data_fetcher._fetch_from_coingecko("invalidcoin")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_missing_price_data(self):
        """Test _fetch_from_coingecko with missing price data"""
        # Mock response with missing USD price
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"bitcoin": {"eur": 40000}})  # Missing "usd" key
        
        with patch('app.services.data_fetcher.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get = Mock(return_value=mock_response)
            mock_session_class.return_value = mock_session
            
            with pytest.raises(DataValidationError):
                await self.data_fetcher._fetch_from_coingecko("bitcoin")
    
    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_http_error_fallback(self):
        """Test _fetch_from_coingecko HTTP error with fallback"""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        # Mock alternative endpoint success
        mock_alt_response = Mock()
        mock_alt_response.status_code = 200
        mock_alt_response.json = Mock(return_value={
            "market_data": {
                "current_price": {"usd": 45000},
                "price_change_percentage_24h": 2.5,
                "total_volume": {"usd": 1000000},
                "market_cap": {"usd": 800000000}
            }
        })
        
        with patch('app.services.data_fetcher.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get = Mock(side_effect=[mock_response, mock_alt_response])
            mock_session_class.return_value = mock_session
            
            result = await self.data_fetcher._fetch_from_coingecko("bitcoin")
            assert result is not None
            assert result["symbol"] == "BITCOIN"
            assert result["current_price"] == 45000
    
    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_http_error_no_fallback(self):
        """Test _fetch_from_coingecko HTTP error with no fallback success"""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        # Mock alternative endpoint also failing
        mock_alt_response = Mock()
        mock_alt_response.status_code = 500
        mock_alt_response.text = "Internal Server Error"
        
        with patch('app.services.data_fetcher.requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.get = Mock(side_effect=[mock_response, mock_alt_response])
            mock_session_class.return_value = mock_session
            
            with pytest.raises(DataFetchError):
                await self.data_fetcher._fetch_from_coingecko("bitcoin")
    
    @pytest.mark.asyncio
    async def test_get_multiple_assets_with_mixed_errors(self):
        """Test get_multiple_assets with mixed success and error conditions"""
        assets = [
            {"symbol": "AAPL", "name": "Apple", "type": "stock"},
            {"symbol": "INVALID", "name": "Invalid Stock", "type": "stock"},
            {"symbol": "bitcoin", "name": "Bitcoin", "type": "crypto"},
            {"symbol": "invalidcoin", "name": "Invalid Coin", "type": "crypto"}
        ]
        
        # Mock mixed results - some succeed, some fail
        async def mock_get_stock_data(symbol):
            if symbol == "AAPL":
                return {
                    "symbol": "AAPL",
                    "current_price": 150.0,
                    "change_percent": 2.5,
                    "chart_data": []
                }
            else:
                raise DataFetchError("Failed to fetch")
        
        async def mock_get_crypto_data(symbol):
            if symbol == "bitcoin":
                return {
                    "symbol": "bitcoin",
                    "current_price": 45000.0,
                    "change_percent": 5.0,
                    "chart_data": []
                }
            else:
                raise DataFetchError("Failed to fetch")
        
        with patch('app.services.data_fetcher.DataFetcher.get_stock_data', side_effect=mock_get_stock_data), \
             patch('app.services.data_fetcher.DataFetcher.get_crypto_data', side_effect=mock_get_crypto_data):
            result = await self.data_fetcher.get_multiple_assets(assets)
            # Should have 2 successful results (AAPL and bitcoin)
            assert len(result) == 2
            symbols = [item["symbol"] for item in result]
            assert "AAPL" in symbols
            assert "bitcoin" in symbols
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_decorator(self):
        """Test the retry_on_failure decorator"""
        call_count = 0
        
        # Create a mock function to test the decorator
        @self.data_fetcher.retry_on_failure(max_retries=3, delay=0.1, backoff_factor=1, exceptions=(DataFetchError,))
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DataFetchError("Temporary failure")
            return "Success"
        
        result = await failing_function()
        assert result == "Success"
        assert call_count == 3  # Should have retried twice before succeeding
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_decorator_max_retries(self):
        """Test the retry_on_failure decorator reaches max retries"""
        call_count = 0
        
        # Create a mock function to test the decorator
        @self.data_fetcher.retry_on_failure(max_retries=3, delay=0.1, backoff_factor=1, exceptions=(DataFetchError,))
        async def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise DataFetchError("Permanent failure")
        
        with pytest.raises(DataFetchError):
            await always_failing_function()
        
        assert call_count == 3  # Should have tried 3 times (max_retries)
    
    @pytest.mark.asyncio
    async def test_initialize_cache_warming_with_errors(self):
        """Test initialize_cache_warming with some assets failing"""
        # Mock some assets succeeding and some failing
        async def mock_get_stock_data(symbol):
            if symbol == "AAPL":
                return {"symbol": "AAPL", "current_price": 150.0}
            else:
                raise Exception("Failed")
        
        async def mock_get_crypto_data(coin_id):
            if coin_id == "bitcoin":
                return {"symbol": "bitcoin", "current_price": 45000.0}
            else:
                raise Exception("Failed")
        
        with patch('app.services.data_fetcher.DataFetcher.get_stock_data', side_effect=mock_get_stock_data), \
             patch('app.services.data_fetcher.DataFetcher.get_crypto_data', side_effect=mock_get_crypto_data), \
             patch.object(self.data_fetcher.cache_service, 'warm_cache', AsyncMock(return_value=2)):
            await self.data_fetcher.initialize_cache_warming()
            # Should complete without crashing even with some failures


if __name__ == "__main__":
    pytest.main([__file__])