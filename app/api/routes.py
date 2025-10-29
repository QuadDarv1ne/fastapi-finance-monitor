"""REST API routes for the finance monitor"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List
import logging

from app.services.data_fetcher import DataFetcher

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/assets")
async def get_assets():
    """Get current data for all assets"""
    assets = [
        {"type": "stock", "symbol": "AAPL", "name": "Apple"},
        {"type": "stock", "symbol": "GOOGL", "name": "Google"},
        {"type": "stock", "symbol": "GC=F", "name": "Gold"},
        {"type": "crypto", "symbol": "bitcoin", "name": "Bitcoin"},
        {"type": "crypto", "symbol": "ethereum", "name": "Ethereum"},
    ]
    
    result = []
    for asset in assets:
        if asset["type"] == "stock":
            data = await DataFetcher.get_stock_data(asset["symbol"])
        else:
            data = await DataFetcher.get_crypto_data(asset["symbol"])
        
        if data:
            data["name"] = asset["name"]
            data["type"] = asset["type"]
            result.append(data)
    
    return {"assets": result}


@router.get("/asset/{symbol}")
async def get_asset(symbol: str, asset_type: str = "stock"):
    """Get data for a specific asset"""
    try:
        if asset_type == "stock":
            data = await DataFetcher.get_stock_data(symbol)
        elif asset_type == "crypto":
            data = await DataFetcher.get_crypto_data(symbol)
        else:
            raise HTTPException(status_code=400, detail="Invalid asset type")
        
        if not data:
            raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")
        
        return data
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Finance monitor is running"}