"""Tests for the watchlist service"""

import pytest
from app.services.watchlist import WatchlistService


class TestWatchlistService:
    """Test suite for WatchlistService"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.watchlist_service = WatchlistService()
        # Clear any existing data for clean tests
        self.watchlist_service.user_watchlists.clear()
    
    def test_watchlist_initialization(self):
        """Test WatchlistService initialization"""
        assert isinstance(self.watchlist_service.user_watchlists, dict)
        assert len(self.watchlist_service.default_assets) > 0
    
    def test_get_user_watchlist_default_user(self):
        """Test getting watchlist for default user"""
        watchlist = self.watchlist_service.get_user_watchlist()
        assert isinstance(watchlist, list)
        assert len(watchlist) > 0
        # Should contain default assets
        for asset in self.watchlist_service.default_assets:
            assert asset in watchlist
    
    def test_get_user_watchlist_specific_user(self):
        """Test getting watchlist for specific user"""
        user_id = "test_user"
        watchlist = self.watchlist_service.get_user_watchlist(user_id)
        assert isinstance(watchlist, list)
        assert len(watchlist) > 0
        # Should contain default assets for new user
        for asset in self.watchlist_service.default_assets:
            assert asset in watchlist
    
    def test_add_to_watchlist(self):
        """Test adding asset to watchlist"""
        user_id = "test_user"
        symbol = "AMZN"
        
        # Add symbol to watchlist
        result = self.watchlist_service.add_to_watchlist(user_id, symbol)
        assert result is True
        
        # Check that symbol is in watchlist
        watchlist = self.watchlist_service.get_user_watchlist(user_id)
        assert symbol.upper() in watchlist
    
    def test_remove_from_watchlist(self):
        """Test removing asset from watchlist"""
        user_id = "test_user"
        symbol = "AAPL"
        
        # First add the symbol (it should be in default assets)
        self.watchlist_service.add_to_watchlist(user_id, symbol)
        watchlist_before = self.watchlist_service.get_user_watchlist(user_id)
        assert symbol.upper() in watchlist_before
        
        # Remove symbol from watchlist
        result = self.watchlist_service.remove_from_watchlist(user_id, symbol)
        assert result is True
        
        # Check that symbol is no longer in watchlist
        watchlist_after = self.watchlist_service.get_user_watchlist(user_id)
        assert symbol.upper() not in watchlist_after
    
    def test_remove_from_watchlist_nonexistent_user(self):
        """Test removing asset from watchlist of nonexistent user"""
        user_id = "nonexistent_user"
        symbol = "AAPL"
        
        # Try to remove symbol from watchlist of nonexistent user
        result = self.watchlist_service.remove_from_watchlist(user_id, symbol)
        assert result is False
    
    def test_is_in_watchlist(self):
        """Test checking if asset is in watchlist"""
        user_id = "test_user"
        symbol_in = "AAPL"  # Should be in default assets
        symbol_not_in = "NONEXISTENT"
        
        # Check that symbol_in is in watchlist
        result = self.watchlist_service.is_in_watchlist(user_id, symbol_in)
        assert result is True
        
        # Check that symbol_not_in is not in watchlist
        result = self.watchlist_service.is_in_watchlist(user_id, symbol_not_in)
        assert result is False
    
    def test_is_in_watchlist_new_user(self):
        """Test checking if asset is in watchlist for new user"""
        user_id = "new_user"
        symbol_in = "AAPL"  # Should be in default assets
        symbol_not_in = "NONEXISTENT"
        
        # Check that symbol_in is in watchlist for new user
        result = self.watchlist_service.is_in_watchlist(user_id, symbol_in)
        assert result is True
        
        # Check that symbol_not_in is not in watchlist for new user
        result = self.watchlist_service.is_in_watchlist(user_id, symbol_not_in)
        assert result is False
    
    def test_get_all_watchlisted_assets(self):
        """Test getting all watchlisted assets"""
        # Add some assets for different users
        self.watchlist_service.add_to_watchlist("user1", "AMZN")
        self.watchlist_service.add_to_watchlist("user2", "NFLX")
        self.watchlist_service.add_to_watchlist("user1", "TSLA")
        
        all_assets = self.watchlist_service.get_all_watchlisted_assets()
        assert isinstance(all_assets, list)
        assert len(all_assets) > 0
        
        # Should contain default assets and added assets
        for asset in self.watchlist_service.default_assets:
            assert asset in all_assets
        assert "AMZN" in all_assets
        assert "NFLX" in all_assets
        assert "TSLA" in all_assets


if __name__ == "__main__":
    pytest.main([__file__])