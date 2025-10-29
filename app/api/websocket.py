"""WebSocket endpoints for real-time data streaming"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json
from datetime import datetime
import logging

from app.services.data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

# Active WebSocket connections
active_connections: List[WebSocket] = []


async def broadcast_data(data: dict):
    """Broadcast data to all connected WebSocket clients"""
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except Exception as e:
            logger.error(f"Error sending data to client: {e}")
            disconnected.append(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


async def data_stream_worker():
    """Background worker to fetch and broadcast data"""
    assets = [
        {"type": "stock", "symbol": "AAPL", "name": "Apple"},
        {"type": "stock", "symbol": "GOOGL", "name": "Google"},
        {"type": "stock", "symbol": "MSFT", "name": "Microsoft"},
        {"type": "stock", "symbol": "TSLA", "name": "Tesla"},
        {"type": "stock", "symbol": "GC=F", "name": "Gold"},
        {"type": "crypto", "symbol": "bitcoin", "name": "Bitcoin"},
        {"type": "crypto", "symbol": "ethereum", "name": "Ethereum"},
        {"type": "crypto", "symbol": "solana", "name": "Solana"},
    ]
    
    while True:
        try:
            all_data = []
            
            for asset in assets:
                if asset["type"] == "stock":
                    data = await DataFetcher.get_stock_data(asset["symbol"])
                else:
                    data = await DataFetcher.get_crypto_data(asset["symbol"])
                
                if data:
                    data["name"] = asset["name"]
                    data["type"] = asset["type"]
                    all_data.append(data)
            
            if all_data:
                await broadcast_data({
                    "type": "update",
                    "data": all_data,
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
    active_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back received messages (can be extended for user interactions)
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        logger.info("Client disconnected")
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)