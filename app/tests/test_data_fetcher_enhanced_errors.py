"""Enhanced tests for the data fetcher with focus on error conditions and edge cases

Note: Tests marked with @pytest.mark.isolated require isolated execution due to
mock conflicts with other tests. Run them separately with:
    pytest -m isolated
or exclude them from full test runs with:
    pytest -m "not isolated"
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.exceptions.custom_exceptions import (
    DataFetchError,
    DataValidationError,
    NetworkError,
    RateLimitError,
    TimeoutError,
)
from app.services.data_fetcher import DataFetcher, retry_on_failure


class TestDataFetcherEnhancedErrors:
    """Enhanced test suite for DataFetcher error handling"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create fresh DataFetcher instance for each test
        self.data_fetcher = DataFetcher()

    def teardown_method(self):
        """Tear down test fixtures after each test method."""
        # Clean up any mocks to prevent leakage between tests
        if hasattr(self.data_fetcher, 'session'):
            self.data_fetcher.session = None
        # Force garbage collection of mock objects
        self.data_fetcher = None

    @pytest.mark.asyncio
    async def test_get_stock_data_with_validation_error(self):
        """Test stock data fetching with validation error"""
        # Mock the internal method to raise a validation error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance",
            AsyncMock(side_effect=DataValidationError("Invalid data")),
        ):
            result = await self.data_fetcher.get_stock_data("INVALID")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "INVALID"
            assert "current_price" in result

    @pytest.mark.asyncio
    async def test_get_stock_data_with_rate_limit_error(self):
        """Test stock data fetching with rate limit error"""
        # Mock the internal method to raise a rate limit error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance",
            AsyncMock(side_effect=RateLimitError("Rate limit exceeded")),
        ):
            result = await self.data_fetcher.get_stock_data("AAPL")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "AAPL"
            assert "current_price" in result

    @pytest.mark.asyncio
    async def test_get_stock_data_with_network_error(self):
        """Test stock data fetching with network error"""
        # Mock the internal method to raise a network error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance",
            AsyncMock(side_effect=NetworkError("Network error")),
        ):
            result = await self.data_fetcher.get_stock_data("AAPL")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "AAPL"
            assert "current_price" in result

    @pytest.mark.asyncio
    async def test_get_stock_data_with_timeout_error(self):
        """Test stock data fetching with timeout error"""
        # Mock the internal method to raise a timeout error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_yahoo_finance",
            AsyncMock(side_effect=TimeoutError("Timeout error")),
        ):
            result = await self.data_fetcher.get_stock_data("AAPL")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "AAPL"
            assert "current_price" in result

    @pytest.mark.asyncio
    async def test_get_crypto_data_with_validation_error(self):
        """Test crypto data fetching with validation error"""
        # Mock the internal method to raise a validation error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_coingecko",
            AsyncMock(side_effect=DataValidationError("Invalid data")),
        ):
            result = await self.data_fetcher.get_crypto_data("invalidcoin")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "invalidcoin"
            assert "current_price" in result

    @pytest.mark.asyncio
    async def test_get_crypto_data_with_rate_limit_error(self):
        """Test crypto data fetching with rate limit error"""
        # Mock the internal method to raise a rate limit error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_coingecko",
            AsyncMock(side_effect=RateLimitError("Rate limit exceeded")),
        ):
            result = await self.data_fetcher.get_crypto_data("bitcoin")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "bitcoin"
            assert "current_price" in result

    @pytest.mark.asyncio
    async def test_get_crypto_data_with_network_error(self):
        """Test crypto data fetching with network error"""
        # Mock the internal method to raise a network error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_coingecko",
            AsyncMock(side_effect=NetworkError("Network error")),
        ):
            result = await self.data_fetcher.get_crypto_data("bitcoin")
            # Should fall back to mock data
            assert result is not None
            assert result["symbol"] == "bitcoin"
            assert "current_price" in result

    @pytest.mark.asyncio
    async def test_get_crypto_data_with_timeout_error(self):
        """Test crypto data fetching with timeout error"""
        # Mock the internal method to raise a timeout error
        with patch(
            "app.services.data_fetcher.DataFetcher._fetch_from_coingecko",
            AsyncMock(side_effect=TimeoutError("Timeout error")),
        ):
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

        with patch("app.services.data_fetcher.yf.Ticker") as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history = Mock(return_value=mock_df)
            mock_ticker_class.return_value = mock_ticker

            result = await self.data_fetcher._fetch_from_yahoo_finance("INVALID")
            assert result is None

    @pytest.mark.isolated
    @pytest.mark.asyncio
    async def test_fetch_from_yahoo_finance_missing_columns(self):
        """Test _fetch_from_yahoo_finance with missing required columns"""
        # Mock DataFrame with missing columns
        mock_df = Mock()
        mock_df.empty = False
        mock_df.columns = ["Volume", "Adj Close"]  # Missing 'Close' and 'Open'

        with patch("app.services.data_fetcher.yf.Ticker") as mock_ticker_class:
            mock_ticker = Mock()
            mock_ticker.history = Mock(return_value=mock_df)
            mock_ticker_class.return_value = mock_ticker

            # The code should raise DataValidationError for missing columns
            # before falling back to mock data
            with pytest.raises(DataValidationError):
                await self.data_fetcher._fetch_from_yahoo_finance("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_empty_data(self):
        """Test _fetch_from_coingecko with empty data"""
        # Mock empty response for aiohttp
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Mock the session
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.closed = False

        with patch.object(self.data_fetcher, '_get_http_session', return_value=mock_session):
            result = await self.data_fetcher._fetch_from_coingecko("invalidcoin")
            assert result is None

    @pytest.mark.isolated
    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_missing_price_data(self):
        """Test _fetch_from_coingecko with missing price data"""
        # Mock response with missing USD price (using aiohttp style)
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"bitcoin": {"eur": 40000}})  # Missing "usd" key
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Mock alternative endpoint also failing (returns empty market_data)
        mock_alt_response = Mock()
        mock_alt_response.status = 200
        mock_alt_response.json = AsyncMock(return_value={"market_data": {}})  # No current_price
        mock_alt_response.__aenter__ = AsyncMock(return_value=mock_alt_response)
        mock_alt_response.__aexit__ = AsyncMock(return_value=None)

        # Mock historical endpoint
        mock_hist_response = Mock()
        mock_hist_response.status = 200
        mock_hist_response.json = AsyncMock(return_value={"prices": []})
        mock_hist_response.__aenter__ = AsyncMock(return_value=mock_hist_response)
        mock_hist_response.__aexit__ = AsyncMock(return_value=None)

        # Mock session with async context manager
        mock_session = Mock()
        mock_session.get = Mock(side_effect=[mock_response, mock_alt_response, mock_hist_response])
        mock_session.closed = False

        with patch.object(self.data_fetcher, '_get_http_session', return_value=mock_session):
            with pytest.raises(DataValidationError):
                await self.data_fetcher._fetch_from_coingecko("bitcoin")

    @pytest.mark.isolated
    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_http_error_fallback(self):
        """Test _fetch_from_coingecko HTTP error with fallback

        Note: This test mocks both the main endpoint (which fails) and the
        alternative endpoint (which succeeds). The fallback returns data from
        the alternative endpoint.
        """
        # Mock HTTP error response for main endpoint (aiohttp style)
        mock_response = Mock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Mock alternative endpoint success
        mock_alt_response = Mock()
        mock_alt_response.status = 200
        mock_alt_response.json = AsyncMock(
            return_value={
                "market_data": {
                    "current_price": {"usd": 45000},
                    "price_change_percentage_24h": 2.5,
                    "total_volume": {"usd": 1000000},
                    "market_cap": {"usd": 800000000},
                }
            }
        )
        mock_alt_response.__aenter__ = AsyncMock(return_value=mock_alt_response)
        mock_alt_response.__aexit__ = AsyncMock(return_value=None)

        # Mock historical endpoint (empty data is OK)
        mock_hist_response = Mock()
        mock_hist_response.status = 200
        mock_hist_response.json = AsyncMock(return_value={"prices": []})
        mock_hist_response.__aenter__ = AsyncMock(return_value=mock_hist_response)
        mock_hist_response.__aexit__ = AsyncMock(return_value=None)

        # Mock session with async context manager
        mock_session = Mock()
        mock_session.get = Mock(side_effect=[mock_response, mock_alt_response, mock_hist_response])
        mock_session.closed = False

        with patch.object(self.data_fetcher, '_get_http_session', return_value=mock_session):
            result = await self.data_fetcher._fetch_from_coingecko("bitcoin")
            assert result is not None
            assert result["symbol"] == "BITCOIN"
            # Price from alternative endpoint fallback
            assert result["current_price"] == 45000

    @pytest.mark.isolated
    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_http_error_no_fallback(self):
        """Test _fetch_from_coingecko HTTP error with no fallback success

        Note: This test verifies that DataFetchError is raised when both
        the main endpoint and fallback endpoint fail.
        """
        # Mock HTTP error response for main endpoint (aiohttp style)
        mock_response = Mock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Mock alternative endpoint also failing
        mock_alt_response = Mock()
        mock_alt_response.status = 500
        mock_alt_response.text = AsyncMock(return_value="Internal Server Error")
        mock_alt_response.__aenter__ = AsyncMock(return_value=mock_alt_response)
        mock_alt_response.__aexit__ = AsyncMock(return_value=None)

        # Mock historical endpoint also failing
        mock_hist_response = Mock()
        mock_hist_response.status = 500
        mock_hist_response.text = AsyncMock(return_value="Internal Server Error")
        mock_hist_response.__aenter__ = AsyncMock(return_value=mock_hist_response)
        mock_hist_response.__aexit__ = AsyncMock(return_value=None)

        # Create fresh DataFetcher instance for this test
        fresh_fetcher = DataFetcher()

        # Mock cache to return None (no cached data)
        with (
            patch.object(fresh_fetcher.cache_service, 'get', AsyncMock(return_value=None)),
            patch.object(fresh_fetcher, '_get_http_session', return_value=Mock(
                get=Mock(side_effect=[mock_response, mock_alt_response, mock_hist_response]),
                closed=False
            ))
        ):
            # All calls fail (main, fallback, and historical)
            with pytest.raises(DataFetchError):
                await fresh_fetcher._fetch_from_coingecko("bitcoin")

    @pytest.mark.asyncio
    async def test_get_multiple_assets_with_mixed_errors(self):
        """Test get_multiple_assets with mixed success and error conditions"""
        assets = [
            {"symbol": "AAPL", "name": "Apple", "type": "stock"},
            {"symbol": "INVALID", "name": "Invalid Stock", "type": "stock"},
            {"symbol": "bitcoin", "name": "Bitcoin", "type": "crypto"},
            {"symbol": "invalidcoin", "name": "Invalid Coin", "type": "crypto"},
        ]

        # Mock mixed results - some succeed, some fail
        async def mock_get_stock_data(symbol):
            if symbol == "AAPL":
                return {
                    "symbol": "AAPL",
                    "current_price": 150.0,
                    "change_percent": 2.5,
                    "chart_data": [],
                }
            else:
                raise DataFetchError("Failed to fetch")

        async def mock_get_crypto_data(symbol):
            if symbol == "bitcoin":
                return {
                    "symbol": "bitcoin",
                    "current_price": 45000.0,
                    "change_percent": 5.0,
                    "chart_data": [],
                }
            else:
                raise DataFetchError("Failed to fetch")

        with (
            patch(
                "app.services.data_fetcher.DataFetcher.get_stock_data",
                side_effect=mock_get_stock_data,
            ),
            patch(
                "app.services.data_fetcher.DataFetcher.get_crypto_data",
                side_effect=mock_get_crypto_data,
            ),
        ):
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
        @retry_on_failure(
            max_retries=3, delay=0.1, backoff_factor=1, exceptions=(DataFetchError,)
        )
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
        @retry_on_failure(
            max_retries=3, delay=0.1, backoff_factor=1, exceptions=(DataFetchError,)
        )
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

        with (
            patch(
                "app.services.data_fetcher.DataFetcher.get_stock_data",
                side_effect=mock_get_stock_data,
            ),
            patch(
                "app.services.data_fetcher.DataFetcher.get_crypto_data",
                side_effect=mock_get_crypto_data,
            ),
            patch.object(self.data_fetcher.cache_service, "warm_cache", AsyncMock(return_value=2)),
        ):
            await self.data_fetcher.initialize_cache_warming()
            # Should complete without crashing even with some failures


if __name__ == "__main__":
    pytest.main([__file__])
