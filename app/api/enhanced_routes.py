"""Enhanced API routes for multi-source data fetching

This module provides API endpoints for accessing enhanced data fetching capabilities
with multi-source support, health monitoring, and asset classification.

Endpoints:
    GET /api/v2/asset/{symbol} - Fetch asset data with automatic source selection
    GET /api/v2/sources/health - Get health report for all data sources
    GET /api/v2/sources/list - List all available data sources
    POST /api/v2/classify - Classify asset type from symbol
"""

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.data_sources_registry import AssetClass, get_data_source_registry
from app.services.enhanced_data_fetcher import get_enhanced_data_fetcher

logger = logging.getLogger(__name__)

router_v2 = APIRouter(prefix="/api/v2", tags=["Enhanced Data"])


class AssetRequest(BaseModel):
    """Request model for asset data"""

    symbol: str
    asset_class: str | None = None  # auto-detect if None
    require_features: list[str] | None = None


class ClassifyRequest(BaseModel):
    """Request model for asset classification"""

    symbol: str


class ClassifyResponse(BaseModel):
    """Response model for asset classification"""

    symbol: str
    asset_class: str
    confidence: str


@router_v2.get("/asset/{symbol}")
async def get_asset_enhanced(
    symbol: str,
    asset_class: str | None = Query(
        None, description="Asset class (equity, cryptocurrency, forex, etc.)"
    ),
    require_real_time: bool = Query(False, description="Require real-time data"),
    require_historical: bool = Query(False, description="Require historical data"),
):
    """
    Fetch asset data with enhanced multi-source support

    **Features:**
    - Automatic source selection based on asset type
    - Intelligent fallback to alternative sources
    - Source health monitoring
    - Data quality indicators

    **Parameters:**
    - symbol: Asset symbol (e.g., AAPL, bitcoin, EURUSD)
    - asset_class: Optional asset classification (auto-detected if not provided)
    - require_real_time: Require real-time data capability
    - require_historical: Require historical data capability

    **Example:**
    ```
    GET /api/v2/asset/AAPL
    GET /api/v2/asset/bitcoin?asset_class=cryptocurrency
    GET /api/v2/asset/EURUSD?require_real_time=true
    ```
    """
    try:
        fetcher = get_enhanced_data_fetcher()

        # Parse asset class if provided
        asset_class_enum = None
        if asset_class:
            try:
                asset_class_enum = AssetClass[asset_class.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid asset_class: {asset_class}. Valid options: {[e.name for e in AssetClass]}",
                ) from None

        # Build required features set
        require_features = set()
        if require_real_time:
            require_features.add("real_time")
        if require_historical:
            require_features.add("historical")

        # Fetch data
        data = await fetcher.fetch_with_fallback(
            symbol=symbol,
            asset_class=asset_class_enum,
            require_features=require_features if require_features else None,
        )

        if not data:
            raise HTTPException(status_code=404, detail=f"No data available for symbol: {symbol}")

        return {
            "success": True,
            "data": data,
            "metadata": {
                "symbol": symbol,
                "requested_asset_class": asset_class,
                "detected_asset_class": data.get("asset_type"),
                "data_source": data.get("source"),
                "data_quality": data.get("data_quality"),
                "timestamp": data.get("timestamp"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching enhanced asset data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {e!s}") from e


@router_v2.get("/sources/health")
async def get_sources_health():
    """
    Get health report for all data sources

    Returns reliability scores, success/failure counts, and last errors for each source.

    **Example Response:**
    ```json
    {
      "yahoo_finance": {
        "enabled": true,
        "reliability": 98.5,
        "success_count": 197,
        "failure_count": 3,
        "last_error": null,
        "quality": "HIGH",
        "priority": 1
      },
      "coingecko": {
        "enabled": true,
        "reliability": 95.2,
        ...
      }
    }
    ```
    """
    try:
        fetcher = get_enhanced_data_fetcher()
        health = fetcher.get_source_health()

        return {
            "success": True,
            "sources": health,
            "summary": {
                "total_sources": len(health),
                "enabled_sources": sum(1 for s in health.values() if s["enabled"]),
                "average_reliability": (
                    sum(s["reliability"] for s in health.values()) / len(health) if health else 0
                ),
            },
        }
    except Exception as e:
        logger.error(f"Error getting sources health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health report: {e!s}") from e


@router_v2.get("/sources/list")
async def list_sources(
    asset_class: str | None = Query(None, description="Filter by asset class"),
    source_type: str | None = Query(
        None, description="Filter by source type (free_api, premium_api, etc.)"
    ),
    enabled_only: bool = Query(True, description="Show only enabled sources"),
):
    """
    List all available data sources with filtering

    **Parameters:**
    - asset_class: Filter by asset class (equity, cryptocurrency, etc.)
    - source_type: Filter by source type (free_api, premium_api, official, etc.)
    - enabled_only: Show only enabled sources

    **Example:**
    ```
    GET /api/v2/sources/list
    GET /api/v2/sources/list?asset_class=cryptocurrency
    GET /api/v2/sources/list?source_type=free_api&enabled_only=false
    ```
    """
    try:
        registry = get_data_source_registry()
        sources = registry.get_all_sources()

        # Apply filters
        if enabled_only:
            sources = [s for s in sources if s.enabled]

        if asset_class:
            try:
                asset_class_enum = AssetClass[asset_class.upper()]
                sources = [s for s in sources if asset_class_enum in s.supported_assets]
            except KeyError:
                raise HTTPException(status_code=400, detail=f"Invalid asset_class: {asset_class}")

        if source_type:
            sources = [s for s in sources if s.source_type.value == source_type]

        # Format response
        sources_data = []
        for source in sources:
            sources_data.append(
                {
                    "name": source.name,
                    "type": source.source_type.value,
                    "supported_assets": [a.value for a in source.supported_assets],
                    "requires_api_key": source.requires_api_key,
                    "rate_limit": source.rate_limit,
                    "quality": source.quality.name,
                    "priority": source.priority,
                    "enabled": source.enabled,
                    "features": list(source.features),
                    "reliability": source.reliability_score,
                    "base_url": source.base_url,
                }
            )

        return {"success": True, "sources": sources_data, "count": len(sources_data)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sources: {e!s}") from e


@router_v2.post("/classify")
async def classify_asset(request: ClassifyRequest):
    """
    Classify asset type from symbol

    Analyzes the symbol and returns the detected asset classification.

    **Example Request:**
    ```json
    {
      "symbol": "AAPL"
    }
    ```

    **Example Response:**
    ```json
    {
      "success": true,
      "symbol": "AAPL",
      "asset_class": "equity",
      "confidence": "high"
    }
    ```
    """
    try:
        fetcher = get_enhanced_data_fetcher()
        asset_class = fetcher._classify_asset(request.symbol)

        # Determine confidence based on symbol patterns
        confidence = "high"
        symbol_upper = request.symbol.upper()

        # High confidence patterns
        if (
            symbol_upper.endswith("=F")
            or symbol_upper.startswith("^")
            or any(crypto in symbol_upper for crypto in ["BTC", "ETH", "BITCOIN", "ETHEREUM"])
        ):
            confidence = "high"
        # Low confidence for generic tickers
        elif len(request.symbol) <= 5 and request.symbol.isalnum():
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "success": True,
            "symbol": request.symbol,
            "asset_class": asset_class.value,
            "confidence": confidence,
            "description": {
                AssetClass.EQUITY: "Stocks, ETFs, and equity securities",
                AssetClass.CRYPTOCURRENCY: "Cryptocurrencies and tokens",
                AssetClass.FOREX: "Foreign exchange currency pairs",
                AssetClass.COMMODITY: "Commodities and futures",
                AssetClass.INDEX: "Market indices",
                AssetClass.FIXED_INCOME: "Bonds and fixed income",
                AssetClass.DERIVATIVE: "Options, futures, and derivatives",
            }.get(asset_class, "Unknown asset class"),
        }

    except Exception as e:
        logger.error(f"Error classifying asset {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to classify asset: {e!s}") from e


@router_v2.get("/sources/{source_name}/status")
async def get_source_status(source_name: str):
    """
    Get detailed status for a specific data source

    **Example:**
    ```
    GET /api/v2/sources/yahoo_finance/status
    ```
    """
    try:
        registry = get_data_source_registry()
        source = registry.get_source(source_name)

        if not source:
            raise HTTPException(status_code=404, detail=f"Source not found: {source_name}")

        return {
            "success": True,
            "source": {
                "name": source.name,
                "type": source.source_type.value,
                "enabled": source.enabled,
                "supported_assets": [a.value for a in source.supported_assets],
                "base_url": source.base_url,
                "requires_api_key": source.requires_api_key,
                "rate_limit": f"{source.rate_limit} req/min",
                "quality": source.quality.name,
                "priority": source.priority,
                "features": list(source.features),
                "health": {
                    "reliability_score": source.reliability_score,
                    "success_count": source.success_count,
                    "failure_count": source.failure_count,
                    "last_error": source.last_error,
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting source status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get source status: {e!s}") from e
