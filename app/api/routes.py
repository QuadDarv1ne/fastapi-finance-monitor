"""REST API routes for the finance monitor"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_fetcher import DataFetcher
from services.indicators import TechnicalIndicators
from services.watchlist import watchlist_service

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
data_fetcher = DataFetcher()


@router.get("/assets")
async def get_assets(user_id: str = "default"):
    """Get current data for all assets in user's watchlist"""
    try:
        # Get user's watchlist
        watchlist = watchlist_service.get_user_watchlist(user_id)
        
        # Convert to asset format
        assets = []
        asset_names = {
            "AAPL": "Apple",
            "GOOGL": "Google",
            "MSFT": "Microsoft",
            "TSLA": "Tesla",
            "AMZN": "Amazon",
            "META": "Meta",
            "NVDA": "NVIDIA",
            "GC=F": "Gold",
            "CL=F": "Crude Oil"
        }
        
        crypto_names = {
            "bitcoin": "Bitcoin",
            "ethereum": "Ethereum",
            "solana": "Solana",
            "cardano": "Cardano",
            "polkadot": "Polkadot"
        }
        
        for symbol in watchlist:
            if symbol in crypto_names:
                assets.append({"type": "crypto", "symbol": symbol, "name": crypto_names[symbol]})
            elif symbol in asset_names:
                assets.append({"type": "stock", "symbol": symbol, "name": asset_names[symbol]})
            elif "=" in symbol:
                assets.append({"type": "commodity", "symbol": symbol, "name": asset_names.get(symbol, symbol)})
            else:
                # Default to stock
                assets.append({"type": "stock", "symbol": symbol, "name": symbol})
        
        result = await data_fetcher.get_multiple_assets(assets)
        return {"assets": result}
    except Exception as e:
        logger.error(f"Error fetching assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/asset/{symbol}")
async def get_asset(symbol: str, asset_type: str = "stock"):
    """Get data for a specific asset"""
    try:
        if asset_type == "stock":
            data = await data_fetcher.get_stock_data(symbol)
        elif asset_type == "crypto":
            data = await data_fetcher.get_crypto_data(symbol)
        else:
            raise HTTPException(status_code=400, detail="Invalid asset type. Use 'stock' or 'crypto'")
        
        if not data:
            raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/asset/{symbol}/indicators")
async def get_asset_indicators(symbol: str, period: str = "6mo", asset_type: str = "stock"):
    """Get technical indicators for a specific asset"""
    try:
        import yfinance as yf
        import pandas as pd
        
        if asset_type == "stock":
            # Get historical data for technical analysis
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval="1d")
            
            if df.empty:
                raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
            
            # Calculate all indicators
            indicators = TechnicalIndicators.calculate_all_indicators(df)
            return indicators
        else:
            raise HTTPException(status_code=400, detail="Technical indicators only available for stocks")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_assets(query: str = Query(..., min_length=1)):
    """Search for assets by symbol or name"""
    # This is a simplified search - in a real app, you'd have a proper search service
    all_assets = [
        {"type": "stock", "symbol": "AAPL", "name": "Apple Inc."},
        {"type": "stock", "symbol": "GOOGL", "name": "Alphabet Inc."},
        {"type": "stock", "symbol": "MSFT", "name": "Microsoft Corporation"},
        {"type": "stock", "symbol": "TSLA", "name": "Tesla Inc."},
        {"type": "stock", "symbol": "AMZN", "name": "Amazon.com Inc."},
        {"type": "stock", "symbol": "META", "name": "Meta Platforms Inc."},
        {"type": "stock", "symbol": "NFLX", "name": "Netflix Inc."},
        {"type": "stock", "symbol": "NVDA", "name": "NVIDIA Corporation"},
        {"type": "stock", "symbol": "GC=F", "name": "Gold Futures"},
        {"type": "stock", "symbol": "CL=F", "name": "Crude Oil Futures"},
        {"type": "crypto", "symbol": "bitcoin", "name": "Bitcoin"},
        {"type": "crypto", "symbol": "ethereum", "name": "Ethereum"},
        {"type": "crypto", "symbol": "solana", "name": "Solana"},
        {"type": "crypto", "symbol": "cardano", "name": "Cardano"},
        {"type": "crypto", "symbol": "polkadot", "name": "Polkadot"},
    ]
    
    query = query.lower()
    results = [
        asset for asset in all_assets 
        if query in asset["symbol"].lower() or query in asset["name"].lower()
    ]
    
    return {"results": results[:10]}  # Return top 10 matches


@router.post("/watchlist/add")
async def add_to_watchlist(symbol: str, user_id: str = "default"):
    """Add an asset to user's watchlist"""
    try:
        success = watchlist_service.add_to_watchlist(user_id, symbol.upper())
        if success:
            return {"message": f"Added {symbol.upper()} to watchlist", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to add asset to watchlist")
    except Exception as e:
        logger.error(f"Error adding {symbol} to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/remove")
async def remove_from_watchlist(symbol: str, user_id: str = "default"):
    """Remove an asset from user's watchlist"""
    try:
        success = watchlist_service.remove_from_watchlist(user_id, symbol.upper())
        if success:
            return {"message": f"Removed {symbol.upper()} from watchlist", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove asset from watchlist")
    except Exception as e:
        logger.error(f"Error removing {symbol} from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist")
async def get_watchlist(user_id: str = "default"):
    """Get user's watchlist"""
    try:
        watchlist = watchlist_service.get_user_watchlist(user_id)
        return {"watchlist": watchlist}
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Finance monitor is running"}