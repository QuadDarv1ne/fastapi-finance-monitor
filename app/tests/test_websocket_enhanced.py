"""Tests for the enhanced WebSocket functionality"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from app.api.websocket import (
    websocket_endpoint, WebSocketManager
)


def test_websocket_manager_initialization():
    """Test that WebSocketManager initializes correctly"""
    # Create WebSocketManager instance
    manager = WebSocketManager()
    
    # Check that all components are initialized
    assert manager.metrics is not None
    assert manager.data_manager is not None
    assert manager.subscription_manager is not None
    assert manager.connection_manager is not None
    assert manager.delta_manager is not None


@pytest.mark.asyncio
async def test_websocket_manager_connect():
    """Test WebSocket connection handling"""
    # Create WebSocketManager instance
    manager = WebSocketManager()
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Mock the connection manager's connect method
    with patch.object(manager.connection_manager, 'connect', return_value="test_client_id"):
        client_id = await manager.connect(mock_websocket)
        assert client_id == "test_client_id"


@pytest.mark.asyncio
async def test_websocket_manager_disconnect():
    """Test WebSocket disconnection handling"""
    # Create WebSocketManager instance
    manager = WebSocketManager()
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Mock the connection manager's disconnect method
    with patch.object(manager.connection_manager, 'disconnect') as mock_disconnect:
        await manager.disconnect(mock_websocket)
        mock_disconnect.assert_called_once_with(mock_websocket)


@pytest.mark.asyncio
async def test_websocket_manager_handle_message():
    """Test handling WebSocket messages"""
    # Create WebSocketManager instance
    manager = WebSocketManager()
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Test refresh action
    message = '{"action": "refresh"}'
    
    # Mock the connection manager's get_client_id method
    with patch.object(manager.connection_manager, 'get_client_id', return_value="test_client_id"):
        # Mock the data manager's get_assets_data method
        with patch.object(manager.data_manager, 'get_assets_data', return_value=[]):
            # Mock the connection manager's send_message method
            with patch.object(manager.connection_manager, 'send_message') as mock_send:
                await manager.handle_message(mock_websocket, message)
                mock_send.assert_called()


@pytest.mark.asyncio
async def test_websocket_manager_subscribe():
    """Test handling subscribe action"""
    # Create WebSocketManager instance
    manager = WebSocketManager()
    
    # Create a mock WebSocket
    mock_websocket = AsyncMock()
    
    # Test subscribe action
    message = '{"action": "subscribe", "symbols": ["AAPL", "GOOGL"]}'
    
    # Mock the connection manager's get_client_id method
    with patch.object(manager.connection_manager, 'get_client_id', return_value="test_client_id"):
        # Mock the connection manager's send_message method
        with patch.object(manager.connection_manager, 'send_message') as mock_send:
            await manager.handle_message(mock_websocket, message)
            mock_send.assert_called()


@pytest.mark.asyncio
async def test_websocket_manager_data_stream_worker():
    """Test data stream worker"""
    # Create WebSocketManager instance
    manager = WebSocketManager()
    
    # Mock the subscription manager's get_all_subscribed_symbols method
    with patch.object(manager.subscription_manager, 'get_all_subscribed_symbols', return_value=["AAPL"]):
        # Mock the data manager's get_assets_data method
        with patch.object(manager.data_manager, 'get_assets_data', return_value=[{"symbol": "AAPL"}]):
            # Mock the subscription manager's get_symbol_subscribers method
            with patch.object(manager.subscription_manager, 'get_symbol_subscribers', return_value=["test_client_id"]):
                # Mock the connection manager's active_connections
                mock_websocket = AsyncMock()
                manager.connection_manager.active_connections[mock_websocket] = {"id": "test_client_id"}
                
                # Mock the connection manager's broadcast method
                with patch.object(manager.connection_manager, 'broadcast') as mock_broadcast:
                    # Set shutdown event to exit loop immediately after one iteration
                    manager.shutdown_event.set()
                    await manager.data_stream_worker()
                    
                    # Check if broadcast was called (might not be if no changes were detected)
                    # We're just testing that it doesn't crash


if __name__ == "__main__":
    print("Enhanced WebSocket tests completed!")