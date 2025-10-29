"""Portfolio service for tracking user investments"""

from typing import List, Optional, Dict
import logging
from datetime import datetime
from app.models import Portfolio, PortfolioItem
from app.services.database_service import DatabaseService
from app.services.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for portfolio management and tracking"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.data_fetcher = DataFetcher()
    
    async def create_portfolio(self, user_id: int, name: str) -> Dict:
        """Create a new portfolio for a user"""
        try:
            portfolio = self.db_service.create_portfolio(user_id, name)
            created_at = portfolio.created_at
            if created_at is not None:
                created_at_str = created_at.isoformat()
            else:
                created_at_str = None
            return {
                "portfolio_id": portfolio.id,
                "name": str(portfolio.name),
                "created_at": created_at_str
            }
        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            return {"error": str(e)}
    
    async def get_user_portfolios(self, user_id: int) -> List[Dict]:
        """Get all portfolios for a user"""
        try:
            portfolios = self.db_service.get_user_portfolios(user_id)
            result = []
            for p in portfolios:
                created_at = p.created_at
                if created_at is not_at_str = created_at.isoformat()
                else:
                    created_at_str = None
                result.append({
                    "id": p.id,
                    "name": str(p.name),
                    "created_at": created_at_str
                })
            return result
        except Exception as e:
            logger.error(f"Error getting user portfolios: {e}")
            return []
    
    async def get_portfolio(self, portfolio_id: int) -> Optional[Dict]:
        """Get a specific portfolio with its items"""
        try:
            portfolio = self.db_service.get_portfolio(portfolio_id)
            if not portfolio:
                return None
            
            items = await self.get_portfolio_items(portfolio_id)
            
            created_at = portfolio.created_at
            if created_at is not None:
                created_at_str = created_at.isoformat()
            else:
                created_at_str = None
                
            return {
                "id": portfolio.id,
                "name": str(portfolio.name),
                "created_at": created_at_str,
                "items": items
            }
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return None
    
    async def add_to_portfolio(self, portfolio_id: int, symbol: str, name: str, 
                              quantity: float, purchase_price: float, purchase_date: str, 
                              asset_type: str) -> Dict:
        """Add an asset to a portfolio"""
        try:
            item = self.db_service.add_to_portfolio(
                portfolio_id, symbol, name, quantity, purchase_price, purchase_date, asset_type
            )
            
            purchase_date_obj = item.purchase_date
            if purchase_date_obj is not None:
                purchase_date_str = purchase_date_obj.isoformat()
            else:
                purchase_date_str = None
                
            return {
                "item_id": item.id,
                "symbol": str(item.symbol),
                "name": str(item.name),
                "quantity": float(str(item.quantity)),
                "purchase_price": float(str(item.purchase_price)),
                "purchase_date": purchase_date_str,
                "asset_type": str(item.asset_type)
            }
        except Exception as e:
            logger.error(f"Error adding to portfolio: {e}")
            return {"error": str(e)}
    
    async def remove_from_portfolio(self, portfolio_id: int, symbol: str) -> bool:
        """Remove an asset from a portfolio"""
        try:
            return self.db_service.remove_from_portfolio(portfolio_id, symbol)
        except Exception as e:
            logger.error(f"Error removing from portfolio: {e}")
            return False
    
    async def get_portfolio_items(self, portfolio_id: int) -> List[Dict]:
        """Get all items in a portfolio"""
        try:
            items = self.db_service.get_portfolio_items(portfolio_id)
            result = []
            for item in items:
                purchase_date_obj = item.purchase_date
                if purchase_date_obj is not None:
                    purchase_date_str = purchase_date_obj.isoformat()
                else:
                    purchase_date_str = None
                    
                result.append({
                    "id": item.id,
                    "symbol": str(item.symbol),
                    "name": str(item.name),
                    "quantity": float(str(item.quantity)),
                    "purchase_price": float(str(item.purchase_price)),
                    "purchase_date": purchase_date_str,
                    "asset_type": str(item.asset_type)
                })
            return result
        except Exception as e:
            logger.error(f"Error getting portfolio items: {e}")
            return []
    
    async def calculate_portfolio_performance(self, portfolio_id: int) -> Dict:
        """Calculate portfolio performance metrics"""
        try:
            portfolio = self.db_service.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            items = self.db_service.get_portfolio_items(portfolio_id)
            if not items:
                return {"total_value": 0, "total_cost": 0, "total_gain": 0, "total_gain_percent": 0}
            
            total_value = 0.0
            total_cost = 0.0
            
            # Calculate current value and cost for each item
            for item in items:
                # Get current price
                symbol = str(item.symbol)
                asset_type = str(item.asset_type)
                current_price = await self._get_current_price(symbol, asset_type)
                
                if current_price is not None:
                    quantity = float(str(item.quantity))
                    purchase_price = float(str(item.purchase_price))
                    current_value = quantity * current_price
                    cost = quantity * purchase_price
                    
                    total_value += current_value
                    total_cost += cost
            
            total_gain = total_value - total_cost
            total_gain_percent = (total_gain / total_cost * 100) if total_cost > 0 else 0.0
            
            return {
                "total_value": round(total_value, 2),
                "total_cost": round(total_cost, 2),
                "total_gain": round(total_gain, 2),
                "total_gain_percent": round(total_gain_percent, 2)
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio performance: {e}")
            return {"error": str(e)}
    
    async def get_portfolio_holdings(self, portfolio_id: int) -> List[Dict]:
        """Get detailed holdings information for a portfolio"""
        try:
            items = self.db_service.get_portfolio_items(portfolio_id)
            holdings = []
            
            for item in items:
                symbol = str(item.symbol)
                asset_type = str(item.asset_type)
                current_price = await self._get_current_price(symbol, asset_type)
                
                if current_price is not None:
                    quantity = float(str(item.quantity))
                    purchase_price = float(str(item.purchase_price))
                    current_value = quantity * current_price
                    cost = quantity * purchase_price
                    gain = current_value - cost
                    gain_percent = (gain / cost * 100) if cost > 0 else 0.0
                    
                    holdings.append({
                        "symbol": symbol,
                        "name": str(item.name),
                        "quantity": quantity,
                        "purchase_price": purchase_price,
                        "current_price": current_price,
                        "current_value": round(current_value, 2),
                        "cost": round(cost, 2),
                        "gain": round(gain, 2),
                        "gain_percent": round(gain_percent, 2),
                        "asset_type": asset_type
                    })
            
            return holdings
        except Exception as e:
            logger.error(f"Error getting portfolio holdings: {e}")
            return []
    
    async def _get_current_price(self, symbol: str, asset_type: str) -> Optional[float]:
        """Get current price for an asset"""
        try:
            if asset_type == "crypto":
                data = await self.data_fetcher.get_crypto_data(symbol.lower())
            else:
                data = await self.data_fetcher.get_stock_data(symbol)
            
            if data and "current_price" in data:
                return float(data["current_price"])
            
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    async def get_portfolio_history(self, portfolio_id: int, days: int = 30) -> Dict:
        """Get portfolio value history"""
        try:
            # This would typically fetch historical data from a database
            # For now, we'll return a mock response
            return {
                "portfolio_id": portfolio_id,
                "days": days,
                "history": []  # In a real implementation, this would contain historical values
            }
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return {"error": str(e)}


# Global portfolio service instance
portfolio_service = None


def get_portfolio_service(db_service: DatabaseService) -> PortfolioService:
    """Get or create portfolio service instance"""
    global portfolio_service
    if portfolio_service is None:
        portfolio_service = PortfolioService(db_service)
    return portfolio_service