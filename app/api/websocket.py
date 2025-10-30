"""WebSocket handlers for real-time data streaming"""
import asyncio
import json
from datetime import datetime, timedelta
import random
import logging
from typing import Dict, List, Optional
import yfinance as yf
import uuid

logger = logging.getLogger(__name__)

# Global variables for WebSocket connections and data
connected_clients = set()
data_cache = {}
watchlists = {}
client_info = {}  # Store additional info about clients
client_subscriptions = {}  # Track client subscriptions

# Timeframe mapping for data intervals
TIMEFRAME_MAPPING = {
    '1m': '1m',
    '5m': '5m',
    '10m': '15m',  # Yahoo Finance uses 15m for 10m equivalent
    '30m': '30m',
    '1h': '1h',
    '3h': '1h',    # Yahoo Finance doesn't have 3h, using 1h
    '6h': '1h',    # Yahoo Finance doesn't have 6h, using 1h
    '12h': '1h',   # Yahoo Finance doesn't have 12h, using 1h
    '1d': '1d'
}

# Expanded list of financial instruments
FINANCIAL_INSTRUMENTS = {
    # Stocks
    'AAPL': {'name': 'Apple Inc.', 'type': 'stock'},
    'GOOGL': {'name': 'Alphabet Inc.', 'type': 'stock'},
    'MSFT': {'name': 'Microsoft Corp.', 'type': 'stock'},
    'TSLA': {'name': 'Tesla Inc.', 'type': 'stock'},
    'AMZN': {'name': 'Amazon.com Inc.', 'type': 'stock'},
    'META': {'name': 'Meta Platforms Inc.', 'type': 'stock'},
    'NVDA': {'name': 'NVIDIA Corp.', 'type': 'stock'},
    'NFLX': {'name': 'Netflix Inc.', 'type': 'stock'},
    'DIS': {'name': 'The Walt Disney Co.', 'type': 'stock'},
    'V': {'name': 'Visa Inc.', 'type': 'stock'},
    'JPM': {'name': 'JPMorgan Chase & Co.', 'type': 'stock'},
    'WMT': {'name': 'Walmart Inc.', 'type': 'stock'},
    'PG': {'name': 'Procter & Gamble Co.', 'type': 'stock'},
    'KO': {'name': 'The Coca-Cola Co.', 'type': 'stock'},
    'XOM': {'name': 'Exxon Mobil Corp.', 'type': 'stock'},
    'BA': {'name': 'Boeing Co.', 'type': 'stock'},
    'IBM': {'name': 'International Business Machines Corp.', 'type': 'stock'},
    'GS': {'name': 'Goldman Sachs Group Inc.', 'type': 'stock'},
    'HD': {'name': 'Home Depot Inc.', 'type': 'stock'},
    'MA': {'name': 'Mastercard Inc.', 'type': 'stock'},
    
    # Cryptocurrencies
    'bitcoin': {'name': 'Bitcoin', 'type': 'crypto'},
    'ethereum': {'name': 'Ethereum', 'type': 'crypto'},
    'solana': {'name': 'Solana', 'type': 'crypto'},
    'cardano': {'name': 'Cardano', 'type': 'crypto'},
    'polkadot': {'name': 'Polkadot', 'type': 'crypto'},
    'litecoin': {'name': 'Litecoin', 'type': 'crypto'},
    'chainlink': {'name': 'Chainlink', 'type': 'crypto'},
    'bitcoin-cash': {'name': 'Bitcoin Cash', 'type': 'crypto'},
    'stellar': {'name': 'Stellar', 'type': 'crypto'},
    'uniswap': {'name': 'Uniswap', 'type': 'crypto'},
    
    # Commodities
    'GC=F': {'name': 'Gold Futures', 'type': 'commodity'},
    'CL=F': {'name': 'Crude Oil Futures', 'type': 'commodity'},
    'SI=F': {'name': 'Silver Futures', 'type': 'commodity'},
    'HG=F': {'name': 'Copper Futures', 'type': 'commodity'},
    'NG=F': {'name': 'Natural Gas Futures', 'type': 'commodity'},
    'PL=F': {'name': 'Platinum Futures', 'type': 'commodity'},
    'PA=F': {'name': 'Palladium Futures', 'type': 'commodity'},
    'CT=F': {'name': 'Cotton Futures', 'type': 'commodity'},
    'KC=F': {'name': 'Coffee Futures', 'type': 'commodity'},
    'SB=F': {'name': 'Sugar Futures', 'type': 'commodity'},
    
    # Forex pairs
    'EURUSD': {'name': 'Euro/US Dollar', 'type': 'forex'},
    'GBPUSD': {'name': 'British Pound/US Dollar', 'type': 'forex'},
    'USDJPY': {'name': 'US Dollar/Japanese Yen', 'type': 'forex'},
    'AUDUSD': {'name': 'Australian Dollar/US Dollar', 'type': 'forex'},
    'USDCAD': {'name': 'US Dollar/Canadian Dollar', 'type': 'forex'},
    'USDCHF': {'name': 'US Dollar/Swiss Franc', 'type': 'forex'},
    'NZDUSD': {'name': 'New Zealand Dollar/US Dollar', 'type': 'forex'},
    'EURGBP': {'name': 'Euro/British Pound', 'type': 'forex'},
    'EURJPY': {'name': 'Euro/Japanese Yen', 'type': 'forex'},
    'GBPJPY': {'name': 'British Pound/Japanese Yen', 'type': 'forex'}
}

# Connection limits
MAX_CLIENTS = 1000
HEARTBEAT_INTERVAL = 30  # seconds
CLIENT_TIMEOUT = 120  # seconds

async def websocket_endpoint(websocket):
    """Handle WebSocket connections with improved error handling and client management"""
    # Check connection limits
    if len(connected_clients) >= MAX_CLIENTS:
        logger.warning("Maximum client connections reached")
        try:
            await websocket.close(code=1013, reason="Server busy")
        except Exception as e:
            logger.error(f"Error closing WebSocket for max clients: {e}")
        return
    
    client_id = str(uuid.uuid4())
    
    try:
        await websocket.accept()
        connected_clients.add(websocket)
        
        # Store client info
        client_info[websocket] = {
            "id": client_id,
            "connected_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "timeframe": "5m",
            "subscriptions": set()  # Track client subscriptions
        }
        
        # Initialize subscriptions
        client_subscriptions[websocket] = set()
        
        logger.info(f"WebSocket client {client_id} connected. Total clients: {len(connected_clients)}")
        
        # Send initial data
        await send_initial_data(websocket)
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat_worker(websocket))
        
        # Handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=CLIENT_TIMEOUT)
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except asyncio.TimeoutError:
                logger.warning(f"Client {client_id} timed out")
                break
            except Exception as e:
                logger.error(f"Error receiving message from client {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for client {client_id}: {e}")
    finally:
        # Clean up client resources
        connected_clients.discard(websocket)
        if websocket in watchlists:
            del watchlists[websocket]
        if websocket in client_info:
            del client_info[websocket]
        if websocket in client_subscriptions:
            del client_subscriptions[websocket]
        
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket for client {client_id}: {e}")
        
        logger.info(f"WebSocket client {client_id} disconnected. Total clients: {len(connected_clients)}")

async def heartbeat_worker(websocket):
    """Send periodic heartbeats to keep connection alive"""
    try:
        while websocket in connected_clients:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if websocket in client_info:
                client_info[websocket]["last_heartbeat"] = datetime.now()
            await send_heartbeat(websocket)
    except Exception as e:
        logger.error(f"Error in heartbeat worker: {e}")

async def send_initial_data(websocket):
    """Send initial data to newly connected client with improved error handling"""
    try:
        # Get initial data for default instruments
        default_symbols = ['AAPL', 'GOOGL', 'MSFT', 'bitcoin', 'ethereum', 'GC=F']
        assets_data = await get_assets_data(default_symbols)
        
        # Send initialization message
        init_message = {
            "type": "init",
            "timestamp": datetime.now().isoformat(),
            "data": assets_data
        }
        await websocket.send_text(json.dumps(init_message))
        
        # Send periodic updates
        update_message = {
            "type": "update",
            "timestamp": datetime.now().isoformat(),
            "data": assets_data
        }
        await websocket.send_text(json.dumps(update_message))
        
    except Exception as e:
        logger.error(f"Error sending initial data: {e}")
        error_message = {
            "type": "error",
            "message": "Error initializing connection"
        }
        await websocket.send_text(json.dumps(error_message))

async def handle_websocket_message(websocket, message):
    """Handle incoming WebSocket messages with improved error handling"""
    try:
        action = message.get('action')
        
        if action == 'refresh':
            # Refresh all data for client's subscriptions or default symbols
            symbols = list(client_subscriptions.get(websocket, set()))
            if not symbols:
                symbols = ['AAPL', 'GOOGL', 'MSFT', 'bitcoin', 'ethereum', 'GC=F']
            
            assets_data = await get_assets_data(symbols[:15])  # Limit for performance
            update_message = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "data": assets_data
            }
            await websocket.send_text(json.dumps(update_message))
            
        elif action == 'add_asset':
            symbol = message.get('symbol')
            if symbol:
                # Add to client subscriptions
                if websocket not in client_subscriptions:
                    client_subscriptions[websocket] = set()
                client_subscriptions[websocket].add(symbol.upper())
                
                # Add to watchlist (in a real app, this would be stored in database)
                if websocket not in watchlists:
                    watchlists[websocket] = set()
                watchlists[websocket].add(symbol.upper())
                
                # Send updated watchlist
                watchlist_message = {
                    "type": "watchlist",
                    "data": list(watchlists[websocket])
                }
                await websocket.send_text(json.dumps(watchlist_message))
                
        elif action == 'remove_asset':
            symbol = message.get('symbol')
            if symbol and websocket in watchlists:
                watchlists[websocket].discard(symbol.upper())
                if websocket in client_subscriptions:
                    client_subscriptions[websocket].discard(symbol.upper())
                
                # Send updated watchlist
                watchlist_message = {
                    "type": "watchlist",
                    "data": list(watchlists[websocket])
                }
                await websocket.send_text(json.dumps(watchlist_message))
                
        elif action == 'set_timeframe':
            timeframe = message.get('timeframe', '5m')
            # Update client timeframe
            if websocket in client_info:
                client_info[websocket]["timeframe"] = timeframe
            # In a real implementation, this would affect data fetching
            # For now, we'll just acknowledge the change
            notification_message = {
                "type": "notification",
                "message": f"Timeframe set to {timeframe}"
            }
            await websocket.send_text(json.dumps(notification_message))
            
        elif action == 'subscribe':
            symbols = message.get('symbols', [])
            if symbols:
                # Add symbols to client subscriptions
                if websocket not in client_subscriptions:
                    client_subscriptions[websocket] = set()
                for symbol in symbols:
                    client_subscriptions[websocket].add(symbol.upper())
                
                notification_message = {
                    "type": "notification",
                    "message": f"Subscribed to {len(symbols)} assets"
                }
                await websocket.send_text(json.dumps(notification_message))
                
        elif action == 'unsubscribe':
            symbols = message.get('symbols', [])
            if symbols and websocket in client_subscriptions:
                for symbol in symbols:
                    client_subscriptions[websocket].discard(symbol.upper())
                
                notification_message = {
                    "type": "notification",
                    "message": f"Unsubscribed from {len(symbols)} assets"
                }
                await websocket.send_text(json.dumps(notification_message))
                
        elif action == 'heartbeat':
            # Update last heartbeat time
            if websocket in client_info:
                client_info[websocket]["last_heartbeat"] = datetime.now()
                
                # Send heartbeat response
                response = {
                    "type": "heartbeat_response",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(response))
                
        else:
            logger.warning(f"Unknown action received: {action}")
            error_message = {
                "type": "error",
                "message": f"Unknown action: {action}"
            }
            await websocket.send_text(json.dumps(error_message))
            
    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        error_message = {
            "type": "error",
            "message": "Error processing request"
        }
        await websocket.send_text(json.dumps(error_message))

async def send_heartbeat(websocket):
    """Send heartbeat to client to keep connection alive"""
    try:
        heartbeat_message = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_text(json.dumps(heartbeat_message))
    except Exception as e:
        logger.error(f"Error sending heartbeat: {e}")

async def get_assets_data(symbols: List[str]) -> List[Dict]:
    """Get data for multiple assets with improved error handling"""
    assets_data = []
    
    # Process symbols in smaller batches to avoid API limits
    batch_size = 5
    for i in range(0, len(symbols), batch_size):
        try:
            batch = symbols[i:i + batch_size]
            batch_data = await get_batch_data(batch)
            assets_data.extend(batch_data)
            # Small delay between batches to avoid rate limiting
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
            # Continue with next batch instead of failing completely
            continue
    
    return assets_data

async def get_batch_data(symbols: List[str]) -> List[Dict]:
    """Get data for a batch of symbols"""
    batch_data = []
    
    # Create tasks for concurrent fetching
    tasks = []
    for symbol in symbols:
        task = get_single_asset_data(symbol)
        tasks.append(task)
    
    # Gather results with error handling
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        try:
            if isinstance(result, Exception):
                logger.error(f"Error fetching data for {symbols[i]}: {result}")
                # Add error data to maintain structure
                batch_data.append({
                    "symbol": symbols[i],
                    "name": symbols[i],
                    "type": "error",
                    "error": str(result)
                })
            elif result is not None and not isinstance(result, BaseException):
                batch_data.append(result)
        except Exception as e:
            logger.error(f"Error processing result for {symbols[i]}: {e}")
    
    return batch_data

async def get_single_asset_data(symbol: str) -> Optional[Dict]:
    """Get data for a single asset"""
    try:
        # Use cached data if available and recent
        cache_key = f"{symbol}"
        if cache_key in data_cache:
            cached_time, cached_data = data_cache[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=30):
                return cached_data
        
        # Get instrument info
        if symbol in FINANCIAL_INSTRUMENTS:
            instrument_info = FINANCIAL_INSTRUMENTS[symbol]
        else:
            instrument_info = {'name': symbol, 'type': 'asset'}
        
        # Generate mock data for demonstration
        # In a real implementation, you would fetch actual data from an API
        asset_data = generate_mock_asset_data(symbol, instrument_info)
        
        # Cache the data
        data_cache[cache_key] = (datetime.now(), asset_data)
        return asset_data
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None

def generate_mock_asset_data(symbol: str, instrument_info: Dict) -> Dict:
    """Generate mock asset data for demonstration"""
    # Base price based on symbol (for consistency)
    base_prices = {
        'AAPL': 175.50, 'GOOGL': 2750.00, 'MSFT': 330.00, 'TSLA': 250.00,
        'AMZN': 3200.00, 'META': 320.00, 'NVDA': 450.00, 'NFLX': 400.00,
        'bitcoin': 45000.00, 'ethereum': 3000.00, 'solana': 100.00,
        'GC=F': 1950.00, 'CL=F': 85.00, 'EURUSD': 1.08
    }
    
    base_price = base_prices.get(symbol, 100.0)
    
    # Generate random price movement
    change_percent = random.uniform(-5, 5)
    current_price = base_price * (1 + change_percent / 100)
    
    # Generate chart data (last 24 points)
    chart_data = []
    for i in range(24):
        time_point = (datetime.now() - timedelta(minutes=i*5)).isoformat()
        price_point = current_price * (1 + random.uniform(-0.5, 0.5) / 100)
        chart_data.append({
            "time": time_point,
            "price": round(price_point, 2)
        })
    
    # For stocks, generate OHLC data
    if instrument_info['type'] == 'stock':
        chart_data = []
        for i in range(24):
            time_point = (datetime.now() - timedelta(minutes=i*5)).isoformat()
            base = current_price * (1 + random.uniform(-1, 1) / 100)
            open_price = base * (1 + random.uniform(-0.2, 0.2) / 100)
            high_price = max(open_price, base) * (1 + random.uniform(0, 0.5) / 100)
            low_price = min(open_price, base) * (1 - random.uniform(0, 0.5) / 100)
            close_price = base
            chart_data.append({
                "time": time_point,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2)
            })
    
    return {
        "symbol": symbol,
        "name": instrument_info['name'],
        "type": instrument_info['type'],
        "current_price": round(current_price, 2),
        "change_percent": round(change_percent, 2),
        "open": round(current_price * (1 - random.uniform(-1, 1) / 100), 2),
        "high": round(current_price * (1 + random.uniform(0, 2) / 100), 2),
        "low": round(current_price * (1 - random.uniform(0, 2) / 100), 2),
        "volume": random.randint(1000000, 100000000),
        "market_cap": random.randint(1000000000, 1000000000000) if instrument_info['type'] == 'stock' else None,
        "chart_data": chart_data
    }

async def data_stream_worker():
    """Background worker to stream data to all connected clients with improved error handling"""
    while True:
        try:
            if connected_clients:
                # Get data for a subset of instruments
                symbols = list(FINANCIAL_INSTRUMENTS.keys())[:15]
                assets_data = await get_assets_data(symbols)
                
                # Create update message
                message = {
                    "type": "update",
                    "timestamp": datetime.now().isoformat(),
                    "data": assets_data
                }
                message_str = json.dumps(message)
                
                # Send to all connected clients
                disconnected_clients = set()
                for client in connected_clients:
                    try:
                        # Check if client is still alive by sending a small message
                        await asyncio.wait_for(client.send_text(message_str), timeout=10.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"Client timeout during data send")
                        disconnected_clients.add(client)
                    except Exception as e:
                        logger.error(f"Error sending data to client: {e}")
                        disconnected_clients.add(client)
                
                # Remove disconnected clients
                for client in disconnected_clients:
                    connected_clients.discard(client)
                    if client in watchlists:
                        del watchlists[client]
                    if client in client_info:
                        del client_info[client]
                    if client in client_subscriptions:
                        del client_subscriptions[client]
            
            # Wait before next update
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            logger.error(f"Error in data stream worker: {e}")
            await asyncio.sleep(5)  # Wait before retrying