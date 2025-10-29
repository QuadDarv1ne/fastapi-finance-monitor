"""WebSocket endpoints for real-time data streaming"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict
import asyncio
import json
from datetime import datetime
import logging

from app.services.data_fetcher import DataFetcher
from app.services.watchlist import watchlist_service

logger = logging.getLogger(__name__)

# Active WebSocket connections with user info
active_connections: List[Dict] = []  # {"websocket": WebSocket, "user_id": str}


async def broadcast_data(data: dict):
    """Broadcast data to all connected WebSocket clients"""
    disconnected = []
    for connection_info in active_connections:
        websocket = connection_info["websocket"]
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.error(f"Error sending data to client: {e}")
            disconnected.append(connection_info)
    
    # Remove disconnected clients
    for conn_info in disconnected:
        if conn_info in active_connections:
            active_connections.remove(conn_info)


async def data_stream_worker():
    """Background worker to fetch and broadcast data"""
    data_fetcher = DataFetcher()
    
    while True:
        try:
            # Get all assets that should be monitored
            monitored_assets = watchlist_service.get_all_watchlisted_assets()
            
            # Convert to asset format
            assets = []
            for symbol in monitored_assets:
                # Determine asset type based on symbol
                if symbol in ["bitcoin", "ethereum", "solana", "cardano", "polkadot"]:
                    assets.append({"type": "crypto", "symbol": symbol, "name": symbol.capitalize()})
                elif "=" in symbol:  # Futures/commodities
                    asset_names = {
                        "GC=F": "Gold",
                        "CL=F": "Crude Oil",
                        "SI=F": "Silver"
                    }
                    assets.append({"type": "commodity", "symbol": symbol, "name": asset_names.get(symbol, symbol)})
                else:  # Stocks
                    asset_names = {
                        "AAPL": "Apple",
                        "GOOGL": "Google",
                        "MSFT": "Microsoft",
                        "TSLA": "Tesla",
                        "AMZN": "Amazon",
                        "META": "Meta",
                        "NVDA": "NVIDIA"
                    }
                    assets.append({"type": "stock", "symbol": symbol, "name": asset_names.get(symbol, symbol)})
            
            # Fetch data for all assets
            asset_data = await data_fetcher.get_multiple_assets(assets)
            
            if asset_data:
                await broadcast_data({
                    "type": "update",
                    "data": asset_data,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Update every 30 seconds
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in data stream: {e}")
            await asyncio.sleep(10)


async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket.accept()
    
    # Default user ID - in a real app, this would come from authentication
    user_id = "default"
    
    # Add connection to active connections
    connection_info = {"websocket": websocket, "user_id": user_id}
    active_connections.append(connection_info)
    
    try:
        # Send initial data
        user_watchlist = watchlist_service.get_user_watchlist(user_id)
        await websocket.send_json({
            "type": "init",
            "watchlist": user_watchlist,
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # Handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, user_id, message)
            except json.JSONDecodeError:
                # Echo back non-JSON messages
                await websocket.send_text(f"Received: {data}")
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        if connection_info in active_connections:
            active_connections.remove(connection_info)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if connection_info in active_connections:
            active_connections.remove(connection_info)


async def handle_websocket_message(websocket: WebSocket, user_id: str, message: dict):
    """Handle WebSocket messages from clients"""
    try:
        action = message.get("action")
        
        if action == "add_asset":
            symbol = message.get("symbol", "").upper()
            if symbol:
                success = watchlist_service.add_to_watchlist(user_id, symbol)
                if success:
                    await websocket.send_json({
                        "type": "notification",
                        "message": f"Added {symbol} to your watchlist",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to add {symbol} to your watchlist",
                        "timestamp": datetime.now().isoformat()
                    })
        
        elif action == "remove_asset":
            symbol = message.get("symbol", "").upper()
            if symbol:
                success = watchlist_service.remove_from_watchlist(user_id, symbol)
                if success:
                    await websocket.send_json({
                        "type": "notification",
                        "message": f"Removed {symbol} from your watchlist",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to remove {symbol} from your watchlist",
                        "timestamp": datetime.now().isoformat()
                    })
        
        elif action == "get_watchlist":
            watchlist = watchlist_service.get_user_watchlist(user_id)
            await websocket.send_json({
                "type": "watchlist",
                "data": watchlist,
                "timestamp": datetime.now().isoformat()
            })
        
        elif action == "refresh":
            # Client requested refresh - this will happen automatically
            await websocket.send_json({
                "type": "notification",
                "message": "Data refresh requested",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Error processing your request",
            "timestamp": datetime.now().isoformat()
        })