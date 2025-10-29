"""REST API routes for the finance monitor"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, List, Optional
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.data_fetcher import DataFetcher
from services.indicators import TechnicalIndicators
from services.watchlist import watchlist_service
from services.database_service import DatabaseService
from services.alert_service import get_alert_service
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)
data_fetcher = DataFetcher()


# Dependency to get database service
def get_database_service(db: Session = Depends(get_db)):
    return DatabaseService(db)


@router.get("/assets")
async def get_assets(user_id: str = "default", db_service: DatabaseService = Depends(get_database_service)):
    """Get current data for all assets in user's watchlist"""
    try:
        # For authenticated users, get from database
        # For now, we'll use the existing watchlist service for demo
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


# User authentication routes
@router.post("/users/register")
async def register_user(username: str, email: str, password: str, 
                       db_service: DatabaseService = Depends(get_database_service)):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = db_service.get_user_by_username(username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        existing_email = db_service.get_user_by_email(email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user
        user = db_service.create_user(username, email, password)
        return {"message": "User created successfully", "user_id": user.id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/login")
async def login_user(username: str, password: str, 
                    db_service: DatabaseService = Depends(get_database_service)):
    """Login user"""
    try:
        user = db_service.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # In a real app, you would return a JWT token here
        return {"message": "Login successful", "user_id": user.id, "username": user.username}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/watchlists")
async def create_watchlist(name: str, user_id: int, 
                          db_service: DatabaseService = Depends(get_database_service)):
    """Create a new watchlist for a user"""
    try:
        watchlist = db_service.create_watchlist(user_id, name)
        return {"message": "Watchlist created", "watchlist_id": watchlist.id}
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/watchlists/{user_id}")
async def get_user_watchlists(user_id: int, 
                             db_service: DatabaseService = Depends(get_database_service)):
    """Get all watchlists for a user"""
    try:
        watchlists = db_service.get_user_watchlists(user_id)
        return {"watchlists": [{"id": w.id, "name": w.name} for w in watchlists]}
    except Exception as e:
        logger.error(f"Error getting user watchlists: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users/watchlists/{watchlist_id}/items")
async def add_to_watchlist_db(watchlist_id: int, symbol: str, name: str, asset_type: str,
                             db_service: DatabaseService = Depends(get_database_service)):
    """Add an item to a watchlist"""
    try:
        item = db_service.add_to_watchlist(watchlist_id, symbol, name, asset_type)
        return {"message": "Item added to watchlist", "item_id": item.id}
    except Exception as e:
        logger.error(f"Error adding item to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/watchlists/{watchlist_id}/items/{symbol}")
async def remove_from_watchlist_db(watchlist_id: int, symbol: str,
                                  db_service: DatabaseService = Depends(get_database_service)):
    """Remove an item from a watchlist"""
    try:
        success = db_service.remove_from_watchlist(watchlist_id, symbol)
        if success:
            return {"message": "Item removed from watchlist"}
        else:
            raise HTTPException(status_code=404, detail="Item not found in watchlist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Alert routes
@router.post("/alerts")
async def create_alert(symbol: str, target_price: float, alert_type: str, user_id: int,
                      db_service: DatabaseService = Depends(get_database_service)):
    """Create a price alert"""
    try:
        alert_service = get_alert_service(db_service)
        result = await alert_service.create_price_alert(user_id, symbol, target_price, alert_type)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{alert_id}")
async def remove_alert(alert_id: str, 
                      db_service: DatabaseService = Depends(get_database_service)):
    """Remove a price alert"""
    try:
        alert_service = get_alert_service(db_service)
        success = await alert_service.remove_alert(alert_id)
        
        if success:
            return {"message": "Alert removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Alert not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{user_id}")
async def get_user_alerts(user_id: int,
                         db_service: DatabaseService = Depends(get_database_service)):
    """Get all alerts for a user"""
    try:
        alert_service = get_alert_service(db_service)
        alerts = await alert_service.get_user_alerts(user_id)
        return {"alerts": alerts}
    except Exception as e:
        logger.error(f"Error getting user alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))