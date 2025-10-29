"""Watchlist service for managing user favorites"""

from typing import Dict, List, Set
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WatchlistService:
    """Manage user watchlists and favorites"""
    
    def __init__(self):
        # In-memory storage for watchlists
        # In a real application, this would be a database
        self.user_watchlists: Dict[str, Set[str]] = {}
        self.default_assets = [
            "AAPL", "GOOGL", "MSFT", "TSLA", "GC=F",
            "bitcoin", "ethereum", "solana"
        ]
    
    def get_user_watchlist(self, user_id: str = "default") -> List[str]:
        """Get a user's watchlist"""
        try:
            if user_id not in self.user_watchlists:
                # Return default assets for new users
                self.user_watchlists[user_id] = set(self.default_assets)
            
            return list(self.user_watchlists[user_id])
        except Exception as e:
            logger.error(f"Error getting watchlist for user {user_id}: {e}")
            return self.default_assets
    
    def add_to_watchlist(self, user_id: str, symbol: str) -> bool:
        """Add an asset to a user's watchlist"""
        try:
            if user_id not in self.user_watchlists:
                self.user_watchlists[user_id] = set(self.default_assets)
            
            self.user_watchlists[user_id].add(symbol.upper())
            logger.info(f"Added {symbol} to watchlist for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding {symbol} to watchlist for user {user_id}: {e}")
            return False
    
    def remove_from_watchlist(self, user_id: str, symbol: str) -> bool:
        """Remove an asset from a user's watchlist"""
        try:
            if user_id in self.user_watchlists:
                self.user_watchlists[user_id].discard(symbol.upper())
                logger.info(f"Removed {symbol} from watchlist for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing {symbol} from watchlist for user {user_id}: {e}")
            return False
    
    def is_in_watchlist(self, user_id: str, symbol: str) -> bool:
        """Check if an asset is in a user's watchlist"""
        try:
            if user_id not in self.user_watchlists:
                return symbol.upper() in [s.upper() for s in self.default_assets]
            
            return symbol.upper() in self.user_watchlists[user_id]
        except Exception as e:
            logger.error(f"Error checking watchlist for {symbol} and user {user_id}: {e}")
            return False
    
    def get_all_watchlisted_assets(self) -> List[str]:
        """Get all assets that are in any user's watchlist"""
        try:
            all_symbols = set()
            for watchlist in self.user_watchlists.values():
                all_symbols.update(watchlist)
            return list(all_symbols)
        except Exception as e:
            logger.error(f"Error getting all watchlisted assets: {e}")
            return self.default_assets


# Global instance
watchlist_service = WatchlistService()