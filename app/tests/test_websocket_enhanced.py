"""Tests for the enhanced WebSocket functionality"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from app.api.websocket import (
    websocket_endpoint, send_initial_data, handle_websocket_message,
    get_assets_data, send_heartbeat, client_info
)


def test_client_info_structure():
    """Test that client_info has the expected structure"""
    # Check that client_info is a dictionary
    assert isinstance(client_info, dict)


@patch('app.api.websocket.get_assets_data')
async def test_send_initial_data(mock_get_assets):
    """Test sending initial data to WebSocket client"""
    # Mock the assets data
    mock_get_assets.return_value = [
        {"symbol": "AAPL", "name": "Apple", "type": "stock", "current_price": 150.0}
    ]
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Test the function
    await send_initial_data(mock_websocket)
    
    # Check that send_text was called
    assert mock_websocket.send_text.called
    
    # Check the calls
    calls = mock_websocket.send_text.call_args_list
    assert len(calls) == 2  # init message and update message
    
    # Check the first call (init message)
    init_call = calls[0]
    init_data = json.loads(init_call[0][0])
    assert init_data["type"] == "init"
    
    # Check the second call (update message)
    update_call = calls[1]
    update_data = json.loads(update_call[0][0])
    assert update_data["type"] == "update"


async def test_send_heartbeat():
    """Test sending heartbeat to WebSocket client"""
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Test the function
    await send_heartbeat(mock_websocket)
    
    # Check that send_text was called
    assert mock_websocket.send_text.called
    
    # Check the call
    call = mock_websocket.send_text.call_args
    data = json.loads(call[0][0])
    assert data["type"] == "heartbeat"
    assert "timestamp" in data


@patch('app.api.websocket.get_batch_data')
async def test_get_assets_data(mock_get_batch):
    """Test getting assets data"""
    # Mock the batch data
    mock_get_batch.return_value = [
        {"symbol": "AAPL", "name": "Apple", "type": "stock", "current_price": 150.0},
        {"symbol": "GOOGL", "name": "Google", "type": "stock", "current_price": 2500.0}
    ]
    
    # Test the function
    symbols = ["AAPL", "GOOGL"]
    result = await get_assets_data(symbols)
    
    # Check the result
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["symbol"] == "AAPL"
    assert result[1]["symbol"] == "GOOGL"


async def test_handle_websocket_message_refresh():
    """Test handling refresh message"""
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Test refresh message
    message = {"action": "refresh"}
    
    # Mock get_assets_data to avoid external dependencies
    with patch('app.api.websocket.get_assets_data') as mock_get_assets:
        mock_get_assets.return_value = [
            {"symbol": "AAPL", "name": "Apple", "type": "stock", "current_price": 150.0}
        ]
        
        await handle_websocket_message(mock_websocket, message)
        
        # Check that send_text was called
        assert mock_websocket.send_text.called


async def test_handle_websocket_message_add_asset():
    """Test handling add asset message"""
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Test add asset message
    message = {"action": "add_asset", "symbol": "AAPL"}
    
    await handle_websocket_message(mock_websocket, message)
    
    # Check that send_text was called for watchlist update
    assert mock_websocket.send_text.called


async def test_handle_websocket_message_remove_asset():
    """Test handling remove asset message"""
    from app.api.websocket import watchlists
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Add an asset to the watchlist first
    watchlists[mock_websocket] = {"AAPL"}
    
    # Test remove asset message
    message = {"action": "remove_asset", "symbol": "AAPL"}
    
    await handle_websocket_message(mock_websocket, message)
    
    # Check that send_text was called for watchlist update
    assert mock_websocket.send_text.called


async def test_handle_websocket_message_set_timeframe():
    """Test handling set timeframe message"""
    from app.api.websocket import client_info
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Add client info
    client_info[mock_websocket] = {"timeframe": "5m"}
    
    # Test set timeframe message
    message = {"action": "set_timeframe", "timeframe": "1h"}
    
    await handle_websocket_message(mock_websocket, message)
    
    # Check that send_text was called
    assert mock_websocket.send_text.called
    
    # Check that timeframe was updated
    assert client_info[mock_websocket]["timeframe"] == "1h"


async def test_handle_websocket_message_heartbeat():
    """Test handling heartbeat message"""
    from app.api.websocket import client_info
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Add client info
    client_info[mock_websocket] = {"last_heartbeat": datetime.now()}
    
    # Test heartbeat message
    message = {"action": "heartbeat"}
    
    await handle_websocket_message(mock_websocket, message)
    
    # Check that send_text was called
    assert mock_websocket.send_text.called


async def test_handle_websocket_message_unknown_action():
    """Test handling unknown action message"""
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Test unknown action message
    message = {"action": "unknown_action"}
    
    await handle_websocket_message(mock_websocket, message)
    
    # Check that send_text was called with error message
    assert mock_websocket.send_text.called


if __name__ == "__main__":
    print("Enhanced WebSocket tests completed!")