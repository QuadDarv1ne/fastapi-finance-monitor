"""REST API routes for the finance monitor"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import Response
from typing import Dict, List, Optional
from datetime import timedelta
import logging
import sys
import os
import io
import pandas as pd

# Optional imports - pdfkit functionality removed to avoid import issues

# Fix import statements
from app.services.data_fetcher import DataFetcher
from app.services.indicators import TechnicalIndicators
from app.services.watchlist import watchlist_service
from app.services.database_service import DatabaseService
from app.services.alert_service import get_alert_service
from app.services.portfolio_service import get_portfolio_service
from app.services.auth_service import AuthService, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from app.services.monitoring_service import get_monitoring_service
from app.database import get_db
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


@router.get("/asset/{symbol}/historical")
async def get_historical_data(symbol: str, period: str = "1mo", interval: str = "1d", asset_type: str = "stock"):
    """Get historical data for a specific asset with customizable time range and interval"""
    try:
        if asset_type == "stock":
            data = await data_fetcher.get_stock_data(symbol, period=period, interval=interval)
        elif asset_type == "crypto":
            # For crypto, we'll need to fetch historical data differently
            data = await data_fetcher.get_crypto_historical_data(symbol, days=_convert_period_to_days(period))
        else:
            raise HTTPException(status_code=400, detail="Invalid asset type. Use 'stock' or 'crypto'")
        
        if not data:
            raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assets/compare")
async def compare_assets(symbols: List[str] = Query(...), period: str = "1mo"):
    """Compare multiple assets by fetching their historical data"""
    try:
        # Convert symbols to asset format
        assets = []
        for symbol in symbols:
            # Determine asset type based on symbol
            if symbol.lower() in ["bitcoin", "ethereum", "solana", "cardano", "polkadot"]:
                assets.append({"type": "crypto", "symbol": symbol, "name": symbol.title()})
            elif "=" in symbol:
                assets.append({"type": "commodity", "symbol": symbol, "name": symbol})
            else:
                assets.append({"type": "stock", "symbol": symbol, "name": symbol})
        
        # Fetch data for all assets
        asset_data_list = await data_fetcher.get_multiple_assets(assets)
        
        if not asset_data_list:
            raise HTTPException(status_code=404, detail="No data found for the specified assets")
        
        # Format data for comparison
        comparison_data = []
        for asset_data in asset_data_list:
            comparison_data.append({
                "symbol": asset_data["symbol"],
                "name": asset_data["name"],
                "type": asset_data["type"],
                "current_price": asset_data["current_price"],
                "change_percent": asset_data["change_percent"],
                "chart_data": asset_data["chart_data"]
            })
        
        return {"assets": comparison_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _convert_period_to_days(period: str) -> int:
    """Convert period string to days"""
    period_map = {
        "1d": 1,
        "5d": 5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
        "10y": 3650,
        "ytd": 365,  # Simplified
        "max": 3650  # Simplified
    }
    return period_map.get(period, 30)


@router.get("/asset/{symbol}/export")
async def export_asset_data(symbol: str, format: str = "csv", period: str = "1mo", asset_type: str = "stock"):
    """Export asset data in specified format (CSV, Excel, JSON) with enhanced historical data support"""
    try:
        # Fetch historical data based on asset type
        if asset_type.lower() == "crypto":
            data = await data_fetcher.get_crypto_historical_data(symbol.lower(), days=_convert_period_to_days(period))
        else:
            data = await data_fetcher.get_stock_data(symbol, period=period, interval="1d")
            
        if not data or "chart_data" not in data:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Convert to DataFrame
        df = pd.DataFrame(data["chart_data"])
        
        # Add additional metadata columns
        if "symbol" in data:
            df["symbol"] = data["symbol"]
        if "current_price" in data:
            df["current_price"] = data["current_price"]
        
        # Ensure time column is properly formatted
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
        
        # Sort by time if available
        if "time" in df.columns:
            df = df.sort_values("time")
        
        if format.lower() == "csv":
            # Convert to CSV
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={symbol}_{period}_data.csv"}
            )
        elif format.lower() in ["xlsx", "excel"]:
            # Convert to Excel
            import tempfile
            import os
            
            # Create a temporary file
            tmp_file = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
            tmp_filename = tmp_file.name
            tmp_file.close()
            
            try:
                with pd.ExcelWriter(tmp_filename, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name=f'{symbol}_{period}_data')
                    
                    # Add summary statistics sheet
                    if "price" in df.columns or "close" in df.columns:
                        price_col = "price" if "price" in df.columns else "close"
                        summary_data = {
                            "Metric": ["Count", "Mean", "Std Dev", "Min", "Max", "Median"],
                            "Value": [
                                len(df),
                                df[price_col].mean(),
                                df[price_col].std(),
                                df[price_col].min(),
                                df[price_col].max(),
                                df[price_col].median()
                            ]
                        }
                        summary_df = pd.DataFrame(summary_data)
                        summary_df.to_excel(writer, index=False, sheet_name="Summary")
                
                # Read the file content
                with open(tmp_filename, 'rb') as f:
                    excel_data = f.read()
                
                return Response(
                    content=excel_data,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={symbol}_{period}_data.xlsx"}
                )
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_filename):
                    os.unlink(tmp_filename)
        elif format.lower() == "json":
            # Convert to JSON
            json_data = df.to_json(orient="records", date_format="iso")
            
            return Response(
                content=json_data,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={symbol}_{period}_data.json"}
            )
        elif format.lower() == "pdf":
            # PDF export not available, return HTML instead
            logger.warning("PDF export not available, returning HTML instead")
            html_data = df.to_html(index=False)
            return Response(
                content=html_data,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename={symbol}_{period}_data.html"}
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'csv', 'xlsx', or 'json'")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data for {symbol}: {e}")
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


@router.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    monitoring_service = get_monitoring_service()
    return monitoring_service.get_all_metrics()


@router.get("/metrics/system")
async def get_system_metrics():
    """Get system metrics"""
    monitoring_service = get_monitoring_service()
    return monitoring_service.get_system_metrics()


@router.get("/metrics/application")
async def get_application_metrics():
    """Get application metrics"""
    monitoring_service = get_monitoring_service()
    return monitoring_service.get_application_metrics()


@router.get("/users/me")
async def read_users_me(user_data: dict = Depends(get_current_user)):
    """Get current user information - protected endpoint"""
    return {"user_id": user_data["user_id"]}


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
    """Login user and return JWT token"""
    try:
        user = db_service.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"user_id": user.id, "username": user.username}, expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token, 
            "token_type": "bearer",
            "user_id": user.id, 
            "username": user.username
        }
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


# Portfolio routes
@router.post("/portfolios")
async def create_portfolio(name: str, user_id: int,
                          db_service: DatabaseService = Depends(get_database_service)):
    """Create a new portfolio"""
    try:
        portfolio_service = get_portfolio_service(db_service)
        result = await portfolio_service.create_portfolio(user_id, name)
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/{user_id}")
async def get_user_portfolios(user_id: int,
                             db_service: DatabaseService = Depends(get_database_service)):
    """Get all portfolios for a user"""
    try:
        portfolio_service = get_portfolio_service(db_service)
        portfolios = await portfolio_service.get_user_portfolios(user_id)
        return {"portfolios": portfolios}
    except Exception as e:
        logger.error(f"Error getting user portfolios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/detail/{portfolio_id}")
async def get_portfolio_detail(portfolio_id: int,
                              db_service: DatabaseService = Depends(get_database_service)):
    """Get detailed portfolio information"""
    try:
        portfolio_service = get_portfolio_service(db_service)
        portfolio = await portfolio_service.get_portfolio(portfolio_id)
        
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        
        return portfolio
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/portfolios/{portfolio_id}/items")
async def add_to_portfolio(portfolio_id: int, symbol: str, name: str, 
                          quantity: float, purchase_price: float, purchase_date: str, asset_type: str,
                          db_service: DatabaseService = Depends(get_database_service)):
    """Add an item to a portfolio"""
    try:
        portfolio_service = get_portfolio_service(db_service)
        result = await portfolio_service.add_to_portfolio(
            portfolio_id, symbol, name, quantity, purchase_price, purchase_date, asset_type
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/portfolios/{portfolio_id}/items/{symbol}")
async def remove_from_portfolio(portfolio_id: int, symbol: str,
                               db_service: DatabaseService = Depends(get_database_service)):
    """Remove an item from a portfolio"""
    try:
        portfolio_service = get_portfolio_service(db_service)
        success = await portfolio_service.remove_from_portfolio(portfolio_id, symbol)
        
        if success:
            return {"message": "Item removed from portfolio"}
        else:
            raise HTTPException(status_code=404, detail="Item not found in portfolio")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/performance/{portfolio_id}")
async def get_portfolio_performance(portfolio_id: int,
                                   db_service: DatabaseService = Depends(get_database_service)):
    """Get portfolio performance metrics"""
    try:
        portfolio_service = get_portfolio_service(db_service)
        performance = await portfolio_service.calculate_portfolio_performance(portfolio_id)
        
        if "error" in performance:
            raise HTTPException(status_code=500, detail=performance["error"])
        
        return performance
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating portfolio performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios/holdings/{portfolio_id}")
async def get_portfolio_holdings(portfolio_id: int,
                                db_service: DatabaseService = Depends(get_database_service)):
    """Get detailed portfolio holdings"""
    try:
        portfolio_service = get_portfolio_service(db_service)
        holdings = await portfolio_service.get_portfolio_holdings(portfolio_id)
        return {"holdings": holdings}
    except Exception as e:
        logger.error(f"Error getting portfolio holdings: {e}")
        raise HTTPException(status_code=500, detail=str(e))