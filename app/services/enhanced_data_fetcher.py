"""Enhanced data fetcher with multi-source support and intelligent fallback

This module extends the base DataFetcher with support for multiple data sources,
intelligent fallback strategies, and advanced classification.

Key Features:
- Automatic source selection based on asset type
- Intelligent fallback to alternative sources
- Source health monitoring and auto-disable
- Parallel requests to multiple sources
- Data aggregation and validation
- Advanced classification and enrichment

Classes:
    EnhancedDataFetcher: Extended data fetcher with multi-source support
"""

import logging
from datetime import datetime

import aiohttp

from app.services.data_fetcher import DataFetcher
from app.services.data_sources_registry import (
    AssetClass,
    get_data_source_registry,
)
from app.utils.types import AssetData

logger = logging.getLogger(__name__)


class EnhancedDataFetcher(DataFetcher):
    """Enhanced data fetcher with multi-source support"""

    def __init__(self):
        super().__init__()
        self.registry = get_data_source_registry()
        self.enable_fallback = True
        self.enable_parallel_fetch = False  # Experimental
        self.max_fallback_attempts = 3
        # Reusable sessions for external APIs
        self._binance_session = None
        self._alpha_vantage_session = None
        self._session_lock = asyncio.Lock()

    async def _get_binance_session(self):
        """Get or create Binance aiohttp session"""
        if self._binance_session is None or self._binance_session.closed:
            async with self._session_lock:
                if self._binance_session is None or self._binance_session.closed:
                    timeout = aiohttp.ClientTimeout(total=10)
                    self._binance_session = aiohttp.ClientSession(timeout=timeout)
        return self._binance_session

    async def _get_alpha_vantage_session(self):
        """Get or create Alpha Vantage aiohttp session"""
        if self._alpha_vantage_session is None or self._alpha_vantage_session.closed:
            async with self._session_lock:
                if self._alpha_vantage_session is None or self._alpha_vantage_session.closed:
                    timeout = aiohttp.ClientTimeout(total=10)
                    self._alpha_vantage_session = aiohttp.ClientSession(timeout=timeout)
        return self._alpha_vantage_session

    async def close(self):
        """Close all aiohttp sessions"""
        await super().close()
        if self._binance_session and not self._binance_session.closed:
            await self._binance_session.close()
        if self._alpha_vantage_session and not self._alpha_vantage_session.closed:
            await self._alpha_vantage_session.close()

    def _classify_asset(self, symbol: str) -> AssetClass:
        """Classify asset type based on symbol"""
        symbol_upper = symbol.upper()

        # Crypto detection
        crypto_symbols = {
            "BITCOIN",
            "BTC",
            "ETHEREUM",
            "ETH",
            "SOLANA",
            "SOL",
            "CARDANO",
            "ADA",
            "RIPPLE",
            "XRP",
            "POLKADOT",
            "DOT",
            "DOGECOIN",
            "DOGE",
            "SHIBA",
            "SHIB",
            "AVALANCHE",
            "AVAX",
            "POLYGON",
            "MATIC",
            "CHAINLINK",
            "LINK",
            "UNI",
            "UNISWAP",
        }

        # Check if symbol is in known crypto list
        for crypto in crypto_symbols:
            if crypto in symbol_upper:
                return AssetClass.CRYPTOCURRENCY

        # Commodity detection (futures)
        if symbol_upper.endswith("=F"):
            return AssetClass.COMMODITY

        # Forex detection (currency pairs)
        forex_indicators = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"]
        if any(fx in symbol_upper for fx in forex_indicators) and len(symbol) == 6:
            return AssetClass.FOREX

        # Index detection
        if symbol_upper.startswith("^") or symbol_upper in ["SPX", "DJI", "IXIC", "NDX"]:
            return AssetClass.INDEX

        # Default to equity
        return AssetClass.EQUITY

    async def fetch_with_fallback(
        self,
        symbol: str,
        asset_class: AssetClass | None = None,
        require_features: set[str] | None = None,
    ) -> AssetData | None:
        """
        Fetch data with automatic fallback to alternative sources

        Args:
            symbol: Asset symbol
            asset_class: Asset classification (auto-detected if None)
            require_features: Required features (e.g., {"historical", "real_time"})

        Returns:
            Asset data or None if all sources fail
        """
        # Auto-classify if not provided
        if asset_class is None:
            asset_class = self._classify_asset(symbol)

        logger.info(f"Fetching {symbol} as {asset_class.value}")

        # Get available sources
        sources = self.registry.get_sources_for_asset(asset_class, require_features)

        if not sources:
            logger.warning(f"No sources available for {asset_class.value}")
            # Fall back to original fetch method
            return await self._fallback_to_original(symbol, asset_class)

        # Try each source in priority order
        for i, source in enumerate(sources[: self.max_fallback_attempts]):
            try:
                logger.info(
                    f"Attempting source {i+1}/{len(sources)}: {source.name} (priority: {source.priority})"
                )

                # Fetch from source
                data = await self._fetch_from_source(source.name, symbol, asset_class)

                if data:
                    # Enrich data with source information
                    data["source"] = source.name
                    data["data_quality"] = source.quality.name

                    # Record success
                    source.record_success()

                    logger.info(f"Successfully fetched {symbol} from {source.name}")
                    return data
                else:
                    logger.warning(f"No data returned from {source.name} for {symbol}")
                    source.record_failure("No data returned")

            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                source.record_failure(str(e))

                # Disable source if reliability drops too low
                if source.reliability_score < 20:
                    logger.warning(
                        f"Disabling {source.name} due to low reliability: {source.reliability_score:.1f}%"
                    )
                    source.enabled = False

        # All sources failed - try original method as last resort
        logger.warning(f"All sources failed for {symbol}, falling back to original method")
        return await self._fallback_to_original(symbol, asset_class)

    async def _fetch_from_source(
        self, source_name: str, symbol: str, asset_class: AssetClass
    ) -> AssetData | None:
        """Fetch data from a specific source"""

        # Map to existing methods
        if source_name == "yahoo_finance":
            if asset_class == AssetClass.EQUITY:
                return await self.get_stock_data(symbol)
            elif asset_class == AssetClass.COMMODITY:
                return await self.get_commodity_data(symbol)
            elif asset_class == AssetClass.FOREX:
                return await self.get_forex_data(symbol)

        elif source_name == "coingecko":
            return await self._fetch_from_coingecko(symbol.lower())

        elif source_name == "binance":
            return await self._fetch_from_binance(symbol)

        elif source_name == "alpha_vantage":
            return await self._fetch_from_alpha_vantage(symbol, asset_class)

        # Add more source handlers here

        logger.warning(f"Source {source_name} not implemented yet")
        return None

    async def _fallback_to_original(self, symbol: str, asset_class: AssetClass) -> AssetData | None:
        """Fallback to original DataFetcher methods"""
        try:
            if asset_class == AssetClass.CRYPTOCURRENCY:
                return await self.get_crypto_data(symbol.lower())
            elif asset_class == AssetClass.EQUITY:
                return await self.get_stock_data(symbol)
            elif asset_class == AssetClass.COMMODITY:
                return await self.get_commodity_data(symbol)
            elif asset_class == AssetClass.FOREX:
                return await self.get_forex_data(symbol)
            else:
                return await self.get_stock_data(symbol)
        except Exception as e:
            logger.error(f"Original method also failed: {e}")
            return None

    async def _fetch_from_binance(self, symbol: str) -> AssetData | None:
        """Fetch cryptocurrency data from Binance"""
        try:
            # Convert symbol to Binance format (e.g., bitcoin -> BTCUSDT)
            symbol_map = {
                "bitcoin": "BTCUSDT",
                "ethereum": "ETHUSDT",
                "solana": "SOLUSDT",
                "cardano": "ADAUSDT",
                "ripple": "XRPUSDT",
                "polkadot": "DOTUSDT",
                "dogecoin": "DOGEUSDT",
            }

            binance_symbol = symbol_map.get(symbol.lower())
            if not binance_symbol:
                return None

            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
            session = await self._get_binance_session()

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    return {
                        "symbol": symbol,
                        "name": symbol.capitalize(),
                        "price": float(data["lastPrice"]),
                        "change": float(data["priceChange"]),
                        "change_percent": float(data["priceChangePercent"]),
                        "volume": float(data["volume"]),
                        "high": float(data["highPrice"]),
                        "low": float(data["lowPrice"]),
                        "open": float(data["openPrice"]),
                        "close": float(data["lastPrice"]),
                        "timestamp": datetime.now().isoformat(),
                        "asset_type": "crypto",
                        "source": "binance",
                        "market_cap": None,
                        "bid": float(data.get("bidPrice", 0)),
                        "ask": float(data.get("askPrice", 0)),
                    }
        except Exception as e:
            logger.error(f"Error fetching from Binance: {e}")
            return None

    async def _fetch_from_alpha_vantage(
        self, symbol: str, asset_class: AssetClass
    ) -> AssetData | None:
        """Fetch data from Alpha Vantage (requires API key)"""
        import os

        api_key = os.getenv("ALPHA_VANTAGE_KEY")

        if not api_key:
            logger.warning("Alpha Vantage API key not configured")
            return None

        try:
            function_map = {
                AssetClass.EQUITY: "GLOBAL_QUOTE",
                AssetClass.FOREX: "CURRENCY_EXCHANGE_RATE",
                AssetClass.CRYPTOCURRENCY: "CURRENCY_EXCHANGE_RATE",
            }

            function = function_map.get(asset_class, "GLOBAL_QUOTE")
            url = f"https://www.alphavantage.co/query?function={function}&symbol={symbol}&apikey={api_key}"
            session = await self._get_alpha_vantage_session()

            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Parse based on function type
                    if function == "GLOBAL_QUOTE":
                        quote = data.get("Global Quote", {})
                        if quote:
                            return {
                                "symbol": symbol,
                                "name": symbol,
                                "price": float(quote.get("05. price", 0)),
                                "change": float(quote.get("09. change", 0)),
                                "change_percent": float(
                                    quote.get("10. change percent", "0").rstrip("%")
                                ),
                                "volume": float(quote.get("06. volume", 0)),
                                "high": float(quote.get("03. high", 0)),
                                "low": float(quote.get("04. low", 0)),
                                "open": float(quote.get("02. open", 0)),
                                "close": float(quote.get("08. previous close", 0)),
                                "timestamp": quote.get(
                                    "07. latest trading day", datetime.now().isoformat()
                                ),
                                "asset_type": "stock",
                                "source": "alpha_vantage",
                            }
        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage: {e}")
            return None

    def get_source_health(self) -> dict[str, dict]:
        """Get health report for all data sources"""
        return self.registry.get_health_report()


# Global instance
_enhanced_fetcher: EnhancedDataFetcher | None = None


def get_enhanced_data_fetcher() -> EnhancedDataFetcher:
    """Get the global enhanced data fetcher instance"""
    global _enhanced_fetcher
    if _enhanced_fetcher is None:
        _enhanced_fetcher = EnhancedDataFetcher()
    return _enhanced_fetcher
