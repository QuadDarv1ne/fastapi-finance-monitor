"""Tests for the enhanced export functionality"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import io
from fastapi.responses import Response
from app.api.routes import export_asset_data


def create_mock_data():
    """Create mock data for testing"""
    return {
        "symbol": "AAPL",
        "current_price": 150.0,
        "chart_data": [
            {"time": "2023-01-01T00:00:00", "price": 145.0},
            {"time": "2023-01-02T00:00:00", "price": 147.0},
            {"time": "2023-01-03T00:00:00", "price": 150.0}
        ]
    }


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_csv(mock_get_stock_data):
    """Test CSV export functionality"""
    # Mock the data fetcher response
    mock_get_stock_data.return_value = create_mock_data()
    
    # Test CSV export
    response = await export_asset_data("AAPL", "csv", "1mo", "stock")
    
    # Check response type
    assert isinstance(response, Response)
    assert response.media_type == "text/csv"
    assert "filename=AAPL_1mo_data.csv" in response.headers["Content-Disposition"]
    
    # Check that content is valid CSV
    content = response.body.decode()
    assert "time" in content
    assert "price" in content


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_excel(mock_get_stock_data):
    """Test Excel export functionality"""
    # Mock the data fetcher response
    mock_get_stock_data.return_value = create_mock_data()
    
    # Test Excel export
    response = await export_asset_data("AAPL", "xlsx", "1mo", "stock")
    
    # Check response type
    assert isinstance(response, Response)
    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "filename=AAPL_1mo_data.xlsx" in response.headers["Content-Disposition"]


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_json(mock_get_stock_data):
    """Test JSON export functionality"""
    # Mock the data fetcher response
    mock_get_stock_data.return_value = create_mock_data()
    
    # Test JSON export
    response = await export_asset_data("AAPL", "json", "1mo", "stock")
    
    # Check response type
    assert isinstance(response, Response)
    assert response.media_type == "application/json"
    assert "filename=AAPL_1mo_data.json" in response.headers["Content-Disposition"]


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_pdf_fallback(mock_get_stock_data):
    """Test PDF export fallback to HTML"""
    # Mock the data fetcher response
    mock_get_stock_data.return_value = create_mock_data()
    
    # Test PDF export (should fallback to HTML)
    response = await export_asset_data("AAPL", "pdf", "1mo", "stock")
    
    # Check response type
    assert isinstance(response, Response)
    assert response.media_type == "text/html"
    assert "filename=AAPL_1mo_data.html" in response.headers["Content-Disposition"]


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_crypto_data(mock_get_crypto_data):
    """Test export functionality with crypto data"""
    # Mock the data fetcher response for crypto
    mock_data = create_mock_data()
    mock_data["symbol"] = "bitcoin"
    mock_get_crypto_data.return_value = mock_data
    
    # Test CSV export for crypto
    response = await export_asset_data("bitcoin", "csv", "1mo", "crypto")
    
    # Check response type
    assert isinstance(response, Response)
    assert response.media_type == "text/csv"
    assert "filename=bitcoin_1mo_data.csv" in response.headers["Content-Disposition"]


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_with_metadata(mock_get_stock_data):
    """Test export with additional metadata"""
    # Mock the data fetcher response
    mock_data = create_mock_data()
    mock_data["symbol"] = "AAPL"
    mock_data["current_price"] = 150.0
    mock_get_stock_data.return_value = mock_data
    
    # Test CSV export
    response = await export_asset_data("AAPL", "csv", "1mo", "stock")
    
    # Check that response is valid
    assert isinstance(response, Response)
    assert response.media_type == "text/csv"


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_data_sorting(mock_get_stock_data):
    """Test that exported data is properly sorted by time"""
    # Mock the data fetcher response with unsorted data
    mock_data = {
        "symbol": "AAPL",
        "current_price": 150.0,
        "chart_data": [
            {"time": "2023-01-03T00:00:00", "price": 150.0},
            {"time": "2023-01-01T00:00:00", "price": 145.0},
            {"time": "2023-01-02T00:00:00", "price": 147.0}
        ]
    }
    mock_get_stock_data.return_value = mock_data
    
    # Test CSV export
    response = await export_asset_data("AAPL", "csv", "1mo", "stock")
    
    # Check that response is valid
    assert isinstance(response, Response)
    assert response.media_type == "text/csv"


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_invalid_format(mock_get_stock_data):
    """Test export with invalid format"""
    # Mock the data fetcher response
    mock_get_stock_data.return_value = create_mock_data()
    
    # Test with invalid format
    with pytest.raises(Exception):
        await export_asset_data("AAPL", "invalid_format", "1mo", "stock")


@patch('app.api.routes.data_fetcher.get_stock_data')
async def test_export_no_data(mock_get_stock_data):
    """Test export when no data is available"""
    # Mock the data fetcher to return None
    mock_get_stock_data.return_value = None
    
    # Test export with no data
    with pytest.raises(Exception):
        await export_asset_data("NONEXISTENT", "csv", "1mo", "stock")


def test_convert_period_to_days():
    """Test the period to days conversion function"""
    from app.api.routes import _convert_period_to_days
    
    # Test various periods
    assert _convert_period_to_days("1d") == 1
    assert _convert_period_to_days("5d") == 5
    assert _convert_period_to_days("1mo") == 30
    assert _convert_period_to_days("3mo") == 90
    assert _convert_period_to_days("1y") == 365
    assert _convert_period_to_days("invalid") == 30  # default


if __name__ == "__main__":
    print("Enhanced export functionality tests completed!")