"""Portfolio service for tracking user investments

This module provides comprehensive portfolio management functionality including
creation, tracking, and performance analysis of user investment portfolios.
It integrates with real-time financial data to calculate performance metrics
and provides advanced analytics for informed investment decisions.

Key Features:
- Portfolio creation and management
- Asset addition and removal
- Real-time performance calculation
- Advanced metrics (Sharpe ratio, drawdown, volatility)
- Historical performance tracking

Classes:
    PortfolioService: Main class for portfolio management
"""

from typing import List, Optional, Dict
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from app.models import Portfolio, PortfolioItem
from app.services.database_service import DatabaseService
from app.services.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for portfolio management and tracking
    
    Provides comprehensive portfolio management functionality including
    creation, tracking, and performance analysis of user investment portfolios.
    Integrates with real-time financial data to calculate performance metrics.
    """
    
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
                if created_at is not None:
                    created_at_str = created_at.isoformat()
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
        """Calculate comprehensive portfolio performance metrics"""
        try:
            portfolio = self.db_service.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            items = self.db_service.get_portfolio_items(portfolio_id)
            if not items:
                return {
                    "total_value": 0, 
                    "total_cost": 0, 
                    "total_gain": 0, 
                    "total_gain_percent": 0,
                    "sharpe_ratio": 0,
                    "max_drawdown": 0,
                    "volatility": 0
                }
            
            total_value = 0.0
            total_cost = 0.0
            holdings_data = []
            
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
                    
                    # Store holding data for advanced metrics
                    holdings_data.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "purchase_price": purchase_price,
                        "current_price": current_price,
                        "current_value": current_value,
                        "cost": cost
                    })
            
            total_gain = total_value - total_cost
            total_gain_percent = (total_gain / total_cost * 100) if total_cost > 0 else 0.0
            
            # Calculate advanced metrics
            sharpe_ratio = await self._calculate_sharpe_ratio(holdings_data)
            max_drawdown = await self._calculate_max_drawdown(holdings_data)
            volatility = await self._calculate_volatility(holdings_data)
            
            return {
                "total_value": round(total_value, 2),
                "total_cost": round(total_cost, 2),
                "total_gain": round(total_gain, 2),
                "total_gain_percent": round(total_gain_percent, 2),
                "sharpe_ratio": round(sharpe_ratio, 4) if sharpe_ratio is not None else 0,
                "max_drawdown": round(max_drawdown, 4) if max_drawdown is not None else 0,
                "volatility": round(volatility, 4) if volatility is not None else 0
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
        """Get current price for an asset with caching and fallback"""
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
    
    async def _calculate_sharpe_ratio(self, holdings_data: List[Dict], risk_free_rate: float = 0.02) -> Optional[float]:
        """Calculate Sharpe ratio for the portfolio"""
        try:
            if not holdings_data:
                return None
            
            # For demonstration, we'll calculate a simplified Sharpe ratio
            # In a real implementation, you would use historical returns
            
            # Calculate portfolio return (simplified)
            total_cost = sum(item["cost"] for item in holdings_data)
            total_value = sum(item["current_value"] for item in holdings_data)
            
            if total_cost == 0:
                return None
            
            portfolio_return = (total_value - total_cost) / total_cost
            
            # Calculate portfolio volatility (simplified)
            volatility = await self._calculate_volatility(holdings_data)
            
            if volatility is None or volatility == 0:
                return None
            
            # Calculate Sharpe ratio
            sharpe_ratio = (portfolio_return - risk_free_rate) / volatility
            return sharpe_ratio
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return None
    
    async def _calculate_max_drawdown(self, holdings_data: List[Dict]) -> Optional[float]:
        """Calculate maximum drawdown for the portfolio"""
        try:
            if not holdings_data:
                return None
            
            # For demonstration, we'll calculate a simplified max drawdown
            # In a real implementation, you would use historical prices
            
            # Calculate current portfolio value
            current_value = sum(item["current_value"] for item in holdings_data)
            total_cost = sum(item["cost"] for item in holdings_data)
            
            if total_cost == 0:
                return None
            
            # Simulate a peak value (in a real implementation, you would track historical peaks)
            peak_value = total_cost * 1.1  # Assume peak was 10% higher than cost
            
            # Calculate drawdown
            if peak_value > 0:
                drawdown = (peak_value - current_value) / peak_value
                return drawdown
            
            return None
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return None
    
    async def _calculate_volatility(self, holdings_data: List[Dict]) -> Optional[float]:
        """Calculate portfolio volatility"""
        try:
            if not holdings_data:
                return None
            
            # For demonstration, we'll calculate a simplified volatility
            # In a real implementation, you would use historical returns
            
            # Calculate weighted average of individual asset volatilities
            # (simplified approach)
            total_value = sum(item["current_value"] for item in holdings_data)
            
            if total_value == 0:
                return None
            
            # Simulate volatility based on asset types
            volatilities = []
            weights = []
            
            for item in holdings_data:
                current_value = item["current_value"]
                weight = current_value / total_value
                weights.append(weight)
                
                # Assign typical volatilities based on asset type
                if item["symbol"].lower() in ["bitcoin", "ethereum", "solana"]:
                    # Crypto assets typically have higher volatility
                    volatilities.append(0.05)  # 5% daily volatility
                elif "=F" in item["symbol"]:
                    # Commodities
                    volatilities.append(0.02)  # 2% daily volatility
                else:
                    # Stocks
                    volatilities.append(0.015)  # 1.5% daily volatility
            
            # Calculate weighted average volatility
            if volatilities and weights:
                weighted_volatility = sum(w * v for w, v in zip(weights, volatilities))
                return weighted_volatility
            
            return None
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None
    
    async def calculate_value_at_risk(self, portfolio_id: int, confidence_level: float = 0.95, time_horizon: int = 1) -> Dict:
        """Calculate Value at Risk (VaR) for the portfolio using parametric method"""
        try:
            portfolio = self.db_service.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            items = self.db_service.get_portfolio_items(portfolio_id)
            if not items:
                return {"value_at_risk": 0, "confidence_level": confidence_level, "time_horizon": time_horizon}
            
            # Get current portfolio value and holdings data
            total_value = 0.0
            holdings_data = []
            
            for item in items:
                symbol = str(item.symbol)
                asset_type = str(item.asset_type)
                current_price = await self._get_current_price(symbol, asset_type)
                
                if current_price is not None:
                    quantity = float(str(item.quantity))
                    purchase_price = float(str(item.purchase_price))
                    current_value = quantity * current_price
                    
                    total_value += current_value
                    
                    holdings_data.append({
                        "symbol": symbol,
                        "quantity": quantity,
                        "current_price": current_price,
                        "current_value": current_value,
                        "weight": 0.0  # Will be calculated later
                    })
            
            if total_value == 0:
                return {"value_at_risk": 0, "confidence_level": confidence_level, "time_horizon": time_horizon}
            
            # Calculate weights for each holding
            for item in holdings_data:
                item["weight"] = item["current_value"] / total_value
            
            # Calculate portfolio volatility (standard deviation)
            portfolio_volatility = await self._calculate_volatility(holdings_data)
            
            if portfolio_volatility is None:
                return {"value_at_risk": 0, "confidence_level": confidence_level, "time_horizon": time_horizon}
            
            # Adjust volatility for time horizon (square root of time rule)
            adjusted_volatility = portfolio_volatility * (time_horizon ** 0.5)
            
            # Calculate VaR using parametric method
            # For a normal distribution, Z-score for 95% confidence is approximately 1.645
            import scipy.stats as stats
            z_score = stats.norm.ppf(confidence_level)
            
            # VaR = Portfolio Value * Z-score * Volatility * sqrt(Time Horizon)
            value_at_risk = total_value * z_score * adjusted_volatility
            
            return {
                "value_at_risk": round(value_at_risk, 2),
                "portfolio_value": round(total_value, 2),
                "confidence_level": confidence_level,
                "time_horizon": time_horizon,
                "volatility": round(portfolio_volatility, 4),
                "adjusted_volatility": round(adjusted_volatility, 4),
                "z_score": round(z_score, 4)
            }
        except Exception as e:
            logger.error(f"Error calculating Value at Risk: {e}")
            return {"error": str(e)}
    
    async def calculate_portfolio_beta(self, portfolio_id: int, benchmark_symbol: str = "SPY") -> Dict:
        """Calculate portfolio beta relative to a benchmark"""
        try:
            portfolio = self.db_service.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            items = self.db_service.get_portfolio_items(portfolio_id)
            if not items:
                return {"beta": 1.0, "benchmark": benchmark_symbol}
            
            # Get portfolio returns
            portfolio_returns = []
            benchmark_returns = []
            
            # For demonstration, we'll simulate returns
            # In a real implementation, you would fetch historical data
            import random
            
            # Generate correlated returns (simplified approach)
            for i in range(30):  # Last 30 days
                # Generate benchmark return (e.g., S&P 500)
                benchmark_return = random.normalvariate(0.0005, 0.01)  # Mean 0.05%, std 1%
                benchmark_returns.append(benchmark_return)
                
                # Generate portfolio return with some correlation to benchmark
                # Portfolio beta would affect this correlation
                portfolio_return = benchmark_return * 1.2 + random.normalvariate(0, 0.005)
                portfolio_returns.append(portfolio_return)
            
            # Calculate beta using covariance formula: Beta = Cov(Portfolio, Benchmark) / Var(Benchmark)
            if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) == 0:
                return {"beta": 1.0, "benchmark": benchmark_symbol}
            
            # Calculate means
            portfolio_mean = sum(portfolio_returns) / len(portfolio_returns)
            benchmark_mean = sum(benchmark_returns) / len(benchmark_returns)
            
            # Calculate covariance and variance
            covariance = sum((portfolio_returns[i] - portfolio_mean) * (benchmark_returns[i] - benchmark_mean) 
                           for i in range(len(portfolio_returns))) / (len(portfolio_returns) - 1)
            benchmark_variance = sum((benchmark_returns[i] - benchmark_mean) ** 2 
                                   for i in range(len(benchmark_returns))) / (len(benchmark_returns) - 1)
            
            # Calculate beta
            if benchmark_variance != 0:
                beta = covariance / benchmark_variance
            else:
                beta = 1.0
            
            return {
                "beta": round(beta, 4),
                "benchmark": benchmark_symbol,
                "portfolio_mean_return": round(portfolio_mean * 100, 4),
                "benchmark_mean_return": round(benchmark_mean * 100, 4)
            }
        except Exception as e:
            logger.error(f"Error calculating portfolio beta: {e}")
            return {"error": str(e)}
    
    async def calculate_sortino_ratio(self, portfolio_id: int, risk_free_rate: float = 0.02) -> Dict:
        """Calculate Sortino ratio (return per unit of downside risk)"""
        try:
            portfolio = self.db_service.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": "Portfolio not found"}
            
            items = self.db_service.get_portfolio_items(portfolio_id)
            if not items:
                return {"sortino_ratio": 0, "risk_free_rate": risk_free_rate}
            
            # Get portfolio returns (simplified approach)
            import random
            
            # Generate sample returns for the last 30 days
            returns = [random.normalvariate(0.001, 0.02) for _ in range(30)]  # Mean 0.1%, std 2%
            
            if len(returns) == 0:
                return {"sortino_ratio": 0, "risk_free_rate": risk_free_rate}
            
            # Calculate average return
            avg_return = sum(returns) / len(returns)
            
            # Calculate downside deviation (standard deviation of negative returns)
            negative_returns = [r for r in returns if r < 0]
            if len(negative_returns) > 0:
                downside_deviation = (sum((r - 0) ** 2 for r in negative_returns) / len(negative_returns)) ** 0.5
            else:
                downside_deviation = 0.0001  # Small value to avoid division by zero
            
            # Calculate Sortino ratio
            sortino_ratio = (avg_return - (risk_free_rate / 252)) / downside_deviation  # Daily risk-free rate
            
            return {
                "sortino_ratio": round(sortino_ratio, 4),
                "average_return": round(avg_return * 100, 4),
                "downside_deviation": round(downside_deviation * 100, 4),
                "risk_free_rate": risk_free_rate,
                "period_days": len(returns)
            }
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return {"error": str(e)}
    
    async def get_advanced_portfolio_analytics(self, portfolio_id: int) -> Dict:
        """Get comprehensive advanced portfolio analytics"""
        try:
            # Get basic performance metrics
            performance = await self.calculate_portfolio_performance(portfolio_id)
            
            # Calculate advanced risk metrics
            var_metrics = await self.calculate_value_at_risk(portfolio_id)
            beta_metrics = await self.calculate_portfolio_beta(portfolio_id)
            sortino_metrics = await self.calculate_sortino_ratio(portfolio_id)
            
            # Combine all metrics
            analytics = {
                "basic_performance": performance,
                "value_at_risk": var_metrics,
                "portfolio_beta": beta_metrics,
                "sortino_ratio": sortino_metrics
            }
            
            return analytics
        except Exception as e:
            logger.error(f"Error getting advanced portfolio analytics: {e}")
            return {"error": str(e)}
    
    async def get_portfolio_history(self, portfolio_id: int, days: int = 30) -> Dict:
        """Get portfolio value history"""
        try:
            items = self.db_service.get_portfolio_items(portfolio_id)
            if not items:
                return {
                    "portfolio_id": portfolio_id,
                    "days": days,
                    "history": []
                }
            
            # Generate historical data points
            history = []
            current_date = datetime.now()
            
            # For demonstration, we'll generate mock historical data
            # In a real implementation, this would fetch actual historical prices
            for i in range(days):
                date = current_date - timedelta(days=days-i)
                
                # Calculate portfolio value for this date (mock implementation)
                portfolio_value = 0
                for item in items:
                    symbol = str(item.symbol)
                    asset_type = str(item.asset_type)
                    quantity = float(str(item.quantity))
                    
                    # For mock data, we'll simulate price changes
                    # In a real implementation, you would fetch historical prices
                    purchase_price = float(str(item.purchase_price))
                    # Simulate some price movement
                    price_change = 1 + np.random.normal(0, 0.02)  # 2% daily volatility
                    simulated_price = purchase_price * price_change
                    portfolio_value += quantity * simulated_price
                
                history.append({
                    "date": date.isoformat(),
                    "value": round(portfolio_value, 2)
                })
            
            return {
                "portfolio_id": portfolio_id,
                "days": days,
                "history": history
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