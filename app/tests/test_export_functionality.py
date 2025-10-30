"""Tests for data export functionality"""

import pytest
import asyncio
import pandas as pd
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.main import app


class TestExportFunctionality:
    """Test suite for data export functionality"""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.client = TestClient(app)
    
    @patch('app.services.data_fetcher.DataFetcher.get_stock_data')
    def test_export_csv(self, mock_get_stock_data):
        """Test exporting data as CSV"""
        # Mock stock data
        mock_data = {
            "symbol": "AAPL",
            "chart_data": [
                {"time": "2023-01-01", "open": 150.0, "high": 155.0, "low": 149.0, "close": 153.0, "volume": 1000000},
                {"time": "2023-01-02", "open": 153.0, "high": 157.0, "low": 152.0, "close": 156.0, "volume": 1200000}
            ]
        }
        mock_get_stock_data.return_value = mock_data
        
        # Make request to export endpoint
        response = self.client.get("/api/asset/AAPL/export?format=csv&period=1mo")
        
        # Assertions
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "AAPL_data.csv" in response.headers["content-disposition"]
        assert len(response.content) > 0
    
    @patch('app.services.data_fetcher.DataFetcher.get_stock_data')
    def test_export_excel(self, mock_get_stock_data):
        """Test exporting data as Excel"""
        # Mock stock data
        mock_data = {
            "symbol": "AAPL",
            "chart_data": [
                {"time": "2023-01-01", "open": 150.0, "high": 155.0, "low": 149.0, "close": 153.0, "volume": 1000000},
                {"time": "2023-01-02", "open": 153.0, "high": 157.0, "low": 152.0, "close": 156.0, "volume": 1200000}
            ]
        }
        mock_get_stock_data.return_value = mock_data
        
        # Make request to export endpoint
        response = self.client.get("/api/asset/AAPL/export?format=xlsx&period=1mo")
        
        # Assertions
        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert "AAPL_data.xlsx" in response.headers["content-disposition"]
        assert len(response.content) > 0
    
    @patch('app.services.data_fetcher.DataFetcher.get_stock_data')
    def test_export_invalid_format(self, mock_get_stock_data):
        """Test exporting data with invalid format"""
        # Mock stock data
        mock_data = {
            "symbol": "AAPL",
            "chart_data": [
                {"time": "2023-01-01", "open": 150.0, "high": 155.0, "low": 149.0, "close": 153.0, "volume": 1000000}
            ]
        }
        mock_get_stock_data.return_value = mock_data
        
        # Make request to export endpoint with invalid format
        response = self.client.get("/api/asset/AAPL/export?format=pdf&period=1mo")
        
        # Assertions
        assert response.status_code == 400
        assert "Invalid format" in response.json()["detail"]
    
    @patch('app.services.data_fetcher.DataFetcher.get_stock_data')
    def test_export_no_data(self, mock_get_stock_data):
        """Test exporting when no data is available"""
        # Mock no data
        mock_get_stock_data.return_value = None
        
        # Make request to export endpoint
        response = self.client.get("/api/asset/NONEXISTENT/export?format=csv&period=1mo")
        
        # Assertions
        assert response.status_code == 404
        assert "No data found" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__])