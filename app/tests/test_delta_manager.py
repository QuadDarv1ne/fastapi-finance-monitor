"""Tests for the delta manager service"""

import pytest
from app.services.delta_manager import DeltaManager


class TestDeltaManager:
    """Test suite for DeltaManager"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.delta_manager = DeltaManager()
        # Clear any existing data for clean tests
        self.delta_manager.clear_all_data()
    
    def test_delta_manager_initialization(self):
        """Test DeltaManager initialization"""
        assert isinstance(self.delta_manager.previous_data, dict)
        assert len(self.delta_manager.previous_data) == 0
    
    def test_get_delta_first_data(self):
        """Test getting delta for first data (should return all key fields)"""
        symbol = "AAPL"
        new_data = {
            "symbol": "AAPL",
            "current_price": 150.0,
            "change_percent": 2.5,
            "volume": 1000000,
            "open": 148.0,
            "high": 151.0,
            "low": 147.5
        }
        
        delta = self.delta_manager.get_delta(symbol, new_data)
        assert delta is not None
        assert "current_price" in delta
        assert "change_percent" in delta
        assert "volume" in delta
        assert "open" in delta
        assert "high" in delta
        assert "low" in delta
        assert delta["current_price"] == 150.0
        assert delta["change_percent"] == 2.5
    
    def test_get_delta_no_changes(self):
        """Test getting delta when there are no changes"""
        symbol = "AAPL"
        data = {
            "symbol": "AAPL",
            "current_price": 150.0,
            "change_percent": 2.5,
            "volume": 1000000,
            "open": 148.0,
            "high": 151.0,
            "low": 147.5
        }
        
        # First call - should return delta
        delta1 = self.delta_manager.get_delta(symbol, data)
        assert delta1 is not None
        
        # Second call with same data - should return None
        delta2 = self.delta_manager.get_delta(symbol, data)
        assert delta2 is None
    
    def test_get_delta_with_changes(self):
        """Test getting delta when there are changes"""
        symbol = "AAPL"
        old_data = {
            "symbol": "AAPL",
            "current_price": 150.0,
            "change_percent": 2.5,
            "volume": 1000000,
            "open": 148.0,
            "high": 151.0,
            "low": 147.5
        }
        
        new_data = {
            "symbol": "AAPL",
            "current_price": 152.0,  # Changed
            "change_percent": 2.5,    # Same
            "volume": 1100000,        # Changed
            "open": 148.0,            # Same
            "high": 153.0,            # Changed
            "low": 147.5              # Same
        }
        
        # First call
        self.delta_manager.get_delta(symbol, old_data)
        
        # Second call with changed data
        delta = self.delta_manager.get_delta(symbol, new_data)
        assert delta is not None
        assert "current_price" in delta
        assert delta["current_price"] == 152.0
        assert "volume" in delta
        assert delta["volume"] == 1100000
        assert "high" in delta
        assert delta["high"] == 153.0
        # Fields that didn't change should not be in delta
        assert "change_percent" not in delta
        assert "open" not in delta
        assert "low" not in delta
    
    def test_clear_symbol_data(self):
        """Test clearing data for specific symbol"""
        symbol1 = "AAPL"
        symbol2 = "GOOGL"
        data1 = {"symbol": "AAPL", "current_price": 150.0}
        data2 = {"symbol": "GOOGL", "current_price": 2500.0}
        
        # Add data for both symbols
        self.delta_manager.get_delta(symbol1, data1)
        self.delta_manager.get_delta(symbol2, data2)
        
        # Verify both symbols are tracked
        stats = self.delta_manager.get_stats()
        assert stats["tracked_symbols"] == 2
        
        # Clear data for one symbol
        self.delta_manager.clear_symbol_data(symbol1)
        
        # Verify only one symbol is tracked
        stats = self.delta_manager.get_stats()
        assert stats["tracked_symbols"] == 1
        
        # Verify that the cleared symbol's data is gone by adding new data
        new_data1 = {"symbol": "AAPL", "current_price": 155.0}
        delta1 = self.delta_manager.get_delta(symbol1, new_data1)
        # Should return all fields since previous data was cleared
        assert delta1 is not None
        assert "current_price" in delta1
        
        # For the other symbol, add new data and check that delta is returned
        new_data2 = {"symbol": "GOOGL", "current_price": 2600.0}
        delta2 = self.delta_manager.get_delta(symbol2, new_data2)
        # Should return only changed fields
        assert delta2 is not None
        assert delta2["current_price"] == 2600.0
    
    def test_clear_all_data(self):
        """Test clearing all data"""
        symbol1 = "AAPL"
        symbol2 = "GOOGL"
        data1 = {"symbol": "AAPL", "current_price": 150.0}
        data2 = {"symbol": "GOOGL", "current_price": 2500.0}
        
        # Add data for both symbols
        self.delta_manager.get_delta(symbol1, data1)
        self.delta_manager.get_delta(symbol2, data2)
        
        # Verify both symbols are tracked
        stats = self.delta_manager.get_stats()
        assert stats["tracked_symbols"] == 2
        
        # Clear all data
        self.delta_manager.clear_all_data()
        
        # Verify no symbols are tracked
        stats = self.delta_manager.get_stats()
        assert stats["tracked_symbols"] == 0
        
        # Verify that getting delta for a symbol works (as if it's the first time)
        delta = self.delta_manager.get_delta(symbol1, data1)
        assert delta is not None
    
    def test_get_stats(self):
        """Test getting delta manager statistics"""
        # Initially empty
        stats = self.delta_manager.get_stats()
        assert stats["tracked_symbols"] == 0
        
        # Add some data
        self.delta_manager.get_delta("AAPL", {"symbol": "AAPL", "current_price": 150.0})
        self.delta_manager.get_delta("GOOGL", {"symbol": "GOOGL", "current_price": 2500.0})
        
        # Check stats
        stats = self.delta_manager.get_stats()
        assert stats["tracked_symbols"] == 2


if __name__ == "__main__":
    pytest.main([__file__])