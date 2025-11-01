"""Subscription manager for handling client subscriptions to assets"""

from typing import Dict, List, Set, Optional
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Управление подписками клиентов"""
    
    def __init__(self):
        """Initialize subscription manager"""
        # Track client subscriptions: client_id -> set of symbols
        self.client_subscriptions: Dict[str, Set[str]] = {}
        # Track symbol subscribers: symbol -> set of client_ids
        self.symbol_subscribers: Dict[str, Set[str]] = {}
    
    def subscribe(self, client_id: str, symbols: List[str]) -> None:
        """
        Subscribe a client to symbols
        
        Args:
            client_id: Client identifier
            symbols: List of symbols to subscribe to
        """
        # Initialize client subscriptions if not exists
        if client_id not in self.client_subscriptions:
            self.client_subscriptions[client_id] = set()
        
        # Add symbols to client subscriptions
        for symbol in symbols:
            symbol_upper = symbol.upper()
            self.client_subscriptions[client_id].add(symbol_upper)
            
            # Add client to symbol subscribers
            if symbol_upper not in self.symbol_subscribers:
                self.symbol_subscribers[symbol_upper] = set()
            self.symbol_subscribers[symbol_upper].add(client_id)
    
    def unsubscribe(self, client_id: str, symbols: List[str]) -> None:
        """
        Unsubscribe a client from symbols
        
        Args:
            client_id: Client identifier
            symbols: List of symbols to unsubscribe from
        """
        if client_id in self.client_subscriptions:
            # Remove symbols from client subscriptions
            for symbol in symbols:
                symbol_upper = symbol.upper()
                self.client_subscriptions[client_id].discard(symbol_upper)
                
                # Remove client from symbol subscribers
                if symbol_upper in self.symbol_subscribers:
                    self.symbol_subscribers[symbol_upper].discard(client_id)
                    # Clean up empty symbol subscriber lists
                    if not self.symbol_subscribers[symbol_upper]:
                        del self.symbol_subscribers[symbol_upper]
    
    def unsubscribe_all(self, client_id: str) -> None:
        """
        Unsubscribe a client from all symbols
        
        Args:
            client_id: Client identifier
        """
        if client_id in self.client_subscriptions:
            # Get all symbols the client was subscribed to
            symbols = list(self.client_subscriptions[client_id])
            
            # Remove client from all symbol subscribers
            for symbol in symbols:
                if symbol in self.symbol_subscribers:
                    self.symbol_subscribers[symbol].discard(client_id)
                    # Clean up empty symbol subscriber lists
                    if not self.symbol_subscribers[symbol]:
                        del self.symbol_subscribers[symbol]
            
            # Remove client subscriptions
            del self.client_subscriptions[client_id]
    
    def get_client_subscriptions(self, client_id: str) -> Set[str]:
        """
        Get symbols a client is subscribed to
        
        Args:
            client_id: Client identifier
            
        Returns:
            Set of symbols the client is subscribed to
        """
        return self.client_subscriptions.get(client_id, set())
    
    def get_symbol_subscribers(self, symbol: str) -> Set[str]:
        """
        Get clients subscribed to a symbol
        
        Args:
            symbol: Asset symbol
            
        Returns:
            Set of client IDs subscribed to the symbol
        """
        return self.symbol_subscribers.get(symbol.upper(), set())
    
    def get_all_subscribed_symbols(self) -> List[str]:
        """
        Get all symbols that have subscribers
        
        Returns:
            List of symbols with subscribers
        """
        return list(self.symbol_subscribers.keys())
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get subscription statistics
        
        Returns:
            Dictionary with subscription statistics
        """
        total_subscriptions = sum(len(symbols) for symbols in self.client_subscriptions.values())
        return {
            "total_clients": len(self.client_subscriptions),
            "total_symbols": len(self.symbol_subscribers),
            "total_subscriptions": total_subscriptions
        }