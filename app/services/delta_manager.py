"""Delta manager for sending only changed data in WebSocket updates"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DeltaManager:
    """Управление дельта-обновлениями"""
    
    def __init__(self):
        """Initialize delta manager"""
        self.previous_data: Dict[str, Dict] = {}
    
    def get_delta(self, symbol: str, new_data: Dict) -> Optional[Dict]:
        """
        Returns only changed fields compared to previous data
        
        Args:
            symbol: Asset symbol
            new_data: New data to compare
            
        Returns:
            Dictionary with only changed fields, or None if no changes
        """
        old_data = self.previous_data.get(symbol, {})
        delta = {}
        
        # Compare key fields that typically change
        key_fields = ['current_price', 'change_percent', 'volume', 'open', 'high', 'low']
        for key in key_fields:
            if key not in old_data or old_data[key] != new_data.get(key):
                delta[key] = new_data.get(key)
        
        # Update stored previous data
        self.previous_data[symbol] = new_data.copy()
        
        # Return delta if there are changes, otherwise None
        return delta if delta else None
    
    def clear_symbol_data(self, symbol: str) -> None:
        """
        Clear stored data for a specific symbol
        
        Args:
            symbol: Asset symbol to clear
        """
        if symbol in self.previous_data:
            del self.previous_data[symbol]
    
    def clear_all_data(self) -> None:
        """Clear all stored data"""
        self.previous_data.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get delta manager statistics
        
        Returns:
            Dictionary with statistics
        """
        return {
            "tracked_symbols": len(self.previous_data)
        }