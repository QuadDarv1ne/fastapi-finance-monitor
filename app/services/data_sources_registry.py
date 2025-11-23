"""Registry of financial data sources with classification and priority

This module provides a centralized registry of all available data sources for different
asset types. It includes classification, reliability ratings, rate limits, and fallback
strategies.

Key Features:
- Multi-source data aggregation (10+ sources)
- Automatic source selection based on asset type
- Priority-based fallback mechanism
- Rate limit tracking
- Source health monitoring
- Classification by asset type and data quality

Classes:
    DataSourceType: Enum for source types
    AssetClass: Enum for asset classifications
    DataSource: Data source configuration
    DataSourceRegistry: Central registry for all sources
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Types of data sources"""

    FREE_API = "free_api"  # Free public APIs
    PREMIUM_API = "premium_api"  # Paid/subscription APIs
    WEB_SCRAPING = "web_scraping"  # Web scraping sources
    AGGREGATOR = "aggregator"  # Data aggregators
    OFFICIAL = "official"  # Official exchange APIs


class AssetClass(Enum):
    """Asset classification"""

    EQUITY = "equity"  # Stocks, ETFs
    CRYPTOCURRENCY = "cryptocurrency"  # Crypto coins/tokens
    FOREX = "forex"  # Currency pairs
    COMMODITY = "commodity"  # Commodities, futures
    FIXED_INCOME = "fixed_income"  # Bonds
    INDEX = "index"  # Market indices
    DERIVATIVE = "derivative"  # Options, futures


class DataQuality(Enum):
    """Data quality rating"""

    HIGH = 3  # Real-time, official exchange data
    MEDIUM = 2  # Delayed quotes, aggregated data
    LOW = 1  # Estimated/mock data


@dataclass
class DataSource:
    """Configuration for a data source"""

    name: str
    source_type: DataSourceType
    supported_assets: set[AssetClass]
    base_url: str
    requires_api_key: bool = False
    rate_limit: int = 60  # requests per minute
    quality: DataQuality = DataQuality.MEDIUM
    priority: int = 5  # 1 = highest priority, 10 = lowest
    enabled: bool = True
    features: set[str] = field(default_factory=set)

    # Health tracking
    success_count: int = 0
    failure_count: int = 0
    last_error: str | None = None

    @property
    def reliability_score(self) -> float:
        """Calculate reliability score (0-100)"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 100.0
        return (self.success_count / total) * 100

    def record_success(self):
        """Record successful API call"""
        self.success_count += 1
        self.last_error = None

    def record_failure(self, error: str):
        """Record failed API call"""
        self.failure_count += 1
        self.last_error = error


class DataSourceRegistry:
    """Central registry for all data sources"""

    def __init__(self):
        self.sources: dict[str, DataSource] = {}
        self._initialize_sources()

    def _initialize_sources(self):
        """Initialize all available data sources"""

        # 1. Yahoo Finance (Primary for stocks)
        self.register_source(
            DataSource(
                name="yahoo_finance",
                source_type=DataSourceType.FREE_API,
                supported_assets={
                    AssetClass.EQUITY,
                    AssetClass.COMMODITY,
                    AssetClass.FOREX,
                    AssetClass.INDEX,
                },
                base_url="https://query1.finance.yahoo.com",
                rate_limit=2000,  # Very generous
                quality=DataQuality.HIGH,
                priority=1,
                features={"historical", "real_time", "fundamentals", "options"},
            )
        )

        # 2. CoinGecko (Primary for crypto)
        self.register_source(
            DataSource(
                name="coingecko",
                source_type=DataSourceType.FREE_API,
                supported_assets={AssetClass.CRYPTOCURRENCY},
                base_url="https://api.coingecko.com/api/v3",
                rate_limit=50,  # 50 calls/min for free tier
                quality=DataQuality.HIGH,
                priority=1,
                features={"historical", "market_cap", "volume", "market_data"},
            )
        )

        # 3. Alpha Vantage (Stocks + Forex + Crypto)
        self.register_source(
            DataSource(
                name="alpha_vantage",
                source_type=DataSourceType.PREMIUM_API,
                supported_assets={
                    AssetClass.EQUITY,
                    AssetClass.FOREX,
                    AssetClass.CRYPTOCURRENCY,
                    AssetClass.COMMODITY,
                },
                base_url="https://www.alphavantage.co/query",
                requires_api_key=True,
                rate_limit=5,  # 5 calls/min for free tier
                quality=DataQuality.HIGH,
                priority=2,
                features={"technical_indicators", "fundamentals", "real_time"},
            )
        )

        # 4. Binance (Crypto exchange)
        self.register_source(
            DataSource(
                name="binance",
                source_type=DataSourceType.OFFICIAL,
                supported_assets={AssetClass.CRYPTOCURRENCY},
                base_url="https://api.binance.com/api/v3",
                rate_limit=1200,  # 1200 weight/min
                quality=DataQuality.HIGH,
                priority=1,
                features={"real_time", "orderbook", "trades", "klines"},
            )
        )

        # 5. Coinbase (Crypto exchange)
        self.register_source(
            DataSource(
                name="coinbase",
                source_type=DataSourceType.OFFICIAL,
                supported_assets={AssetClass.CRYPTOCURRENCY},
                base_url="https://api.exchange.coinbase.com",
                rate_limit=10,  # 10 req/sec
                quality=DataQuality.HIGH,
                priority=2,
                features={"real_time", "orderbook", "historical"},
            )
        )

        # 6. Twelve Data (Multi-asset)
        self.register_source(
            DataSource(
                name="twelve_data",
                source_type=DataSourceType.PREMIUM_API,
                supported_assets={
                    AssetClass.EQUITY,
                    AssetClass.FOREX,
                    AssetClass.CRYPTOCURRENCY,
                    AssetClass.INDEX,
                },
                base_url="https://api.twelvedata.com",
                requires_api_key=True,
                rate_limit=8,  # 8 calls/min for free tier
                quality=DataQuality.HIGH,
                priority=3,
                features={"technical_indicators", "real_time", "fundamentals"},
            )
        )

        # 7. Polygon.io (Stocks + Crypto)
        self.register_source(
            DataSource(
                name="polygon",
                source_type=DataSourceType.PREMIUM_API,
                supported_assets={AssetClass.EQUITY, AssetClass.CRYPTOCURRENCY, AssetClass.FOREX},
                base_url="https://api.polygon.io",
                requires_api_key=True,
                rate_limit=5,  # 5 calls/min for free tier
                quality=DataQuality.HIGH,
                priority=3,
                features={"real_time", "aggregates", "trades", "quotes"},
            )
        )

        # 8. Finnhub (Stocks)
        self.register_source(
            DataSource(
                name="finnhub",
                source_type=DataSourceType.PREMIUM_API,
                supported_assets={AssetClass.EQUITY},
                base_url="https://finnhub.io/api/v1",
                requires_api_key=True,
                rate_limit=60,  # 60 calls/min for free tier
                quality=DataQuality.HIGH,
                priority=3,
                features={"real_time", "news", "fundamentals", "earnings"},
            )
        )

        # 9. CryptoCompare (Crypto)
        self.register_source(
            DataSource(
                name="cryptocompare",
                source_type=DataSourceType.FREE_API,
                supported_assets={AssetClass.CRYPTOCURRENCY},
                base_url="https://min-api.cryptocompare.com",
                rate_limit=50,  # 50 calls/sec for free tier
                quality=DataQuality.MEDIUM,
                priority=2,
                features={"historical", "social", "news"},
            )
        )

        # 10. Exchangerate.host (Forex)
        self.register_source(
            DataSource(
                name="exchangerate",
                source_type=DataSourceType.FREE_API,
                supported_assets={AssetClass.FOREX},
                base_url="https://api.exchangerate.host",
                rate_limit=1000,  # Very generous
                quality=DataQuality.MEDIUM,
                priority=2,
                features={"historical", "convert", "fluctuation"},
            )
        )

        # 11. IEX Cloud (Stocks)
        self.register_source(
            DataSource(
                name="iex_cloud",
                source_type=DataSourceType.PREMIUM_API,
                supported_assets={AssetClass.EQUITY, AssetClass.INDEX},
                base_url="https://cloud.iexapis.com/stable",
                requires_api_key=True,
                rate_limit=50,  # Depends on plan
                quality=DataQuality.HIGH,
                priority=3,
                features={"real_time", "fundamentals", "news", "stats"},
            )
        )

        # 12. CoinMarketCap (Crypto)
        self.register_source(
            DataSource(
                name="coinmarketcap",
                source_type=DataSourceType.PREMIUM_API,
                supported_assets={AssetClass.CRYPTOCURRENCY},
                base_url="https://pro-api.coinmarketcap.com/v1",
                requires_api_key=True,
                rate_limit=30,  # 333 credits/day for free tier ≈ 30/min
                quality=DataQuality.HIGH,
                priority=2,
                features={"market_cap", "volume", "rankings", "metadata"},
            )
        )

    def register_source(self, source: DataSource):
        """Register a new data source"""
        self.sources[source.name] = source
        logger.info(f"Registered data source: {source.name} (priority: {source.priority})")

    def get_sources_for_asset(
        self, asset_class: AssetClass, require_features: set[str] | None = None
    ) -> list[DataSource]:
        """Get available sources for an asset class, sorted by priority and reliability"""
        sources = []

        for source in self.sources.values():
            # Check if source is enabled and supports the asset
            if not source.enabled or asset_class not in source.supported_assets:
                continue

            # Check if source has required features
            if require_features and not require_features.issubset(source.features):
                continue

            sources.append(source)

        # Sort by priority (lower = better), then by reliability
        sources.sort(key=lambda s: (s.priority, -s.reliability_score))

        return sources

    def get_source(self, name: str) -> DataSource | None:
        """Get a specific data source by name"""
        return self.sources.get(name)

    def get_all_sources(self) -> list[DataSource]:
        """Get all registered sources"""
        return list(self.sources.values())

    def get_sources_by_type(self, source_type: DataSourceType) -> list[DataSource]:
        """Get all sources of a specific type"""
        return [s for s in self.sources.values() if s.source_type == source_type]

    def get_health_report(self) -> dict[str, dict]:
        """Get health report for all sources"""
        report = {}
        for name, source in self.sources.items():
            report[name] = {
                "enabled": source.enabled,
                "reliability": source.reliability_score,
                "success_count": source.success_count,
                "failure_count": source.failure_count,
                "last_error": source.last_error,
                "quality": source.quality.name,
                "priority": source.priority,
            }
        return report


# Global registry instance
_registry: DataSourceRegistry | None = None


def get_data_source_registry() -> DataSourceRegistry:
    """Get the global data source registry instance"""
    global _registry
    if _registry is None:
        _registry = DataSourceRegistry()
    return _registry
