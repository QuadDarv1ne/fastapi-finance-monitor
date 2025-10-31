"""WebSocket handlers for real-time data streaming"""
import asyncio
import json
from datetime import datetime, timedelta
import random
import logging
from typing import Dict, List, Optional
import yfinance as yf
import uuid
from fastapi import WebSocket, WebSocketDisconnect

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
    # Stocks - US Companies
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
    
    # Stocks - European Companies
    'NESN.SW': {'name': 'Nestle SA', 'type': 'stock'},
    'ROG.SW': {'name': 'Roche Holding AG', 'type': 'stock'},
    'NOVN.SW': {'name': 'Novartis AG', 'type': 'stock'},
    'SAP.DE': {'name': 'SAP SE', 'type': 'stock'},
    'SIE.DE': {'name': 'Siemens AG', 'type': 'stock'},
    'BMW.DE': {'name': 'Bayerische Motoren Werke AG', 'type': 'stock'},
    'DAI.DE': {'name': 'Daimler AG', 'type': 'stock'},
    'AIR.PA': {'name': 'Airbus SE', 'type': 'stock'},
    'SAN.PA': {'name': 'Sanofi SA', 'type': 'stock'},
    'BNP.PA': {'name': 'BNP Paribas SA', 'type': 'stock'},
    'ENEL.MI': {'name': 'Enel SpA', 'type': 'stock'},
    'ENI.MI': {'name': 'Eni SpA', 'type': 'stock'},
    'UCG.MI': {'name': 'UniCredit SpA', 'type': 'stock'},
    'INGA.NL': {'name': 'ING Groep NV', 'type': 'stock'},
    'ASML.NL': {'name': 'ASML Holding NV', 'type': 'stock'},
    'UNA.NL': {'name': 'Unilever NV', 'type': 'stock'},
    'RDSA.NL': {'name': 'Royal Dutch Shell PLC', 'type': 'stock'},
    'BP.L': {'name': 'BP PLC', 'type': 'stock'},
    'HSBA.L': {'name': 'HSBC Holdings PLC', 'type': 'stock'},
    'BARC.L': {'name': 'Barclays PLC', 'type': 'stock'},
    'VOD.L': {'name': 'Vodafone Group PLC', 'type': 'stock'},
    'AZN.L': {'name': 'AstraZeneca PLC', 'type': 'stock'},
    'GSK.L': {'name': 'GlaxoSmithKline PLC', 'type': 'stock'},
    
    # Stocks - Russian Companies
    'GAZP.ME': {'name': 'Gazprom PJSC', 'type': 'stock'},
    'LKOH.ME': {'name': 'Lukoil PJSC', 'type': 'stock'},
    'SBER.ME': {'name': 'Sberbank of Russia', 'type': 'stock'},
    'ROSN.ME': {'name': 'Rosneft Oil Co.', 'type': 'stock'},
    'GMKN.ME': {'name': 'GMK Norilsk Nickel', 'type': 'stock'},
    'NVTK.ME': {'name': 'Novatek PJSC', 'type': 'stock'},
    'ALRS.ME': {'name': 'Alrosa Co.', 'type': 'stock'},
    'TATN.ME': {'name': 'Tatneft PJSC', 'type': 'stock'},
    'SNGS.ME': {'name': 'Surgutneftegas PJSC', 'type': 'stock'},
    'CHMF.ME': {'name': 'Severstal PJSC', 'type': 'stock'},
    'NLMK.ME': {'name': 'Novolipetsk Steel', 'type': 'stock'},
    'MGNT.ME': {'name': 'Magnit PJSC', 'type': 'stock'},
    'MTSS.ME': {'name': 'MTS PJSC', 'type': 'stock'},
    'FEES.ME': {'name': 'FEES', 'type': 'stock'},
    'HYDR.ME': {'name': 'RusHydro PJSC', 'type': 'stock'},
    
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
    'dogecoin': {'name': 'Dogecoin', 'type': 'crypto'},
    'avalanche': {'name': 'Avalanche', 'type': 'crypto'},
    'polygon': {'name': 'Polygon', 'type': 'crypto'},
    'cosmos': {'name': 'Cosmos', 'type': 'crypto'},
    'monero': {'name': 'Monero', 'type': 'crypto'},
    'tron': {'name': 'TRON', 'type': 'crypto'},
    'vechain': {'name': 'VeChain', 'type': 'crypto'},
    'filecoin': {'name': 'Filecoin', 'type': 'crypto'},
    'theta': {'name': 'Theta Network', 'type': 'crypto'},
    'eos': {'name': 'EOS', 'type': 'crypto'},
    'tezos': {'name': 'Tezos', 'type': 'crypto'},
    'elrond': {'name': 'Elrond', 'type': 'crypto'},
    'flow': {'name': 'Flow', 'type': 'crypto'},
    'klaytn': {'name': 'Klaytn', 'type': 'crypto'},
    'near': {'name': 'NEAR Protocol', 'type': 'crypto'},
    'hedera': {'name': 'Hedera Hashgraph', 'type': 'crypto'},
    'algorand': {'name': 'Algorand', 'type': 'crypto'},
    'iota': {'name': 'IOTA', 'type': 'crypto'},
    'dash': {'name': 'Dash', 'type': 'crypto'},
    'zcash': {'name': 'Zcash', 'type': 'crypto'},
    
    # Precious Metals
    'GC=F': {'name': 'Gold Futures', 'type': 'commodity'},
    'SI=F': {'name': 'Silver Futures', 'type': 'commodity'},
    'PL=F': {'name': 'Platinum Futures', 'type': 'commodity'},
    'PA=F': {'name': 'Palladium Futures', 'type': 'commodity'},
    'HG=F': {'name': 'Copper Futures', 'type': 'commodity'},
    
    # Additional Precious Metals and Commodities
    'XAUUSD=X': {'name': 'Gold Spot', 'type': 'commodity'},
    'XAGUSD=X': {'name': 'Silver Spot', 'type': 'commodity'},
    'XPTUSD=X': {'name': 'Platinum Spot', 'type': 'commodity'},
    'XPDUSD=X': {'name': 'Palladium Spot', 'type': 'commodity'},
    'CL=F': {'name': 'Crude Oil Futures', 'type': 'commodity'},
    'NG=F': {'name': 'Natural Gas Futures', 'type': 'commodity'},
    'CT=F': {'name': 'Cotton Futures', 'type': 'commodity'},
    'KC=F': {'name': 'Coffee Futures', 'type': 'commodity'},
    'SB=F': {'name': 'Sugar Futures', 'type': 'commodity'},
    'CC=F': {'name': 'Cocoa Futures', 'type': 'commodity'},
    'LE=F': {'name': 'Live Cattle Futures', 'type': 'commodity'},
    'HE=F': {'name': 'Lean Hogs Futures', 'type': 'commodity'},
    'ZW=F': {'name': 'Wheat Futures', 'type': 'commodity'},
    'ZC=F': {'name': 'Corn Futures', 'type': 'commodity'},
    'ZO=F': {'name': 'Oat Futures', 'type': 'commodity'},
    'KE=F': {'name': 'Wheat Futures (Kansas)', 'type': 'commodity'},
    'ZR=F': {'name': 'Rough Rice Futures', 'type': 'commodity'},
    'GF=F': {'name': 'Feeder Cattle Futures', 'type': 'commodity'},
    
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
    'GBPJPY': {'name': 'British Pound/Japanese Yen', 'type': 'forex'},
    'AUDJPY': {'name': 'Australian Dollar/Japanese Yen', 'type': 'forex'},
    'NZDJPY': {'name': 'New Zealand Dollar/Japanese Yen', 'type': 'forex'},
    'GBPNZD': {'name': 'British Pound/New Zealand Dollar', 'type': 'forex'},
    'EURAUD': {'name': 'Euro/Australian Dollar', 'type': 'forex'},
    'EURCHF': {'name': 'Euro/Swiss Franc', 'type': 'forex'},
    'CADJPY': {'name': 'Canadian Dollar/Japanese Yen', 'type': 'forex'},
    'CHFJPY': {'name': 'Swiss Franc/Japanese Yen', 'type': 'forex'},
    'USDMXN': {'name': 'US Dollar/Mexican Peso', 'type': 'forex'},
    'USDZAR': {'name': 'US Dollar/South African Rand', 'type': 'forex'},
    'USDRUB': {'name': 'US Dollar/Russian Ruble', 'type': 'forex'},
    'EURRUB': {'name': 'Euro/Russian Ruble', 'type': 'forex'},
    'GBPRUB': {'name': 'British Pound/Russian Ruble', 'type': 'forex'}
}

# Connection limits
MAX_CLIENTS = 1000
HEARTBEAT_INTERVAL = 30  # seconds
CLIENT_TIMEOUT = 120  # seconds

class WebSocketManager:
    """Manage WebSocket connections and data streaming"""
    
    def __init__(self):
        self.connected_clients = set()
        self.data_cache = {}
        self.watchlists = {}
        self.client_info = {}
        self.client_subscriptions = {}
    
    async def connect(self, websocket: WebSocket) -> Optional[str]:
        """Handle new WebSocket connection"""
        # Check connection limits
        if len(self.connected_clients) >= MAX_CLIENTS:
            logger.warning("Maximum client connections reached")
            try:
                await websocket.close(code=1013, reason="Server busy")
            except Exception as e:
                logger.error(f"Error closing WebSocket for max clients: {e}")
            return None
        
        client_id = str(uuid.uuid4())
        
        try:
            await websocket.accept()
            self.connected_clients.add(websocket)
            
            # Store client info
            self.client_info[websocket] = {
                "id": client_id,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "timeframe": "5m",
                "subscriptions": set()
            }
            
            # Initialize subscriptions
            self.client_subscriptions[websocket] = set()
            
            logger.info(f"WebSocket client {client_id} connected. Total clients: {len(self.connected_clients)}")
            
            # Send initial data
            await self.send_initial_data(websocket)
            
            return client_id
            
        except Exception as e:
            logger.error(f"WebSocket connection error for client {client_id}: {e}")
            return None
    
    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        client_id = "unknown"
        if websocket in self.client_info:
            client_id = self.client_info[websocket]["id"]
            
        self.connected_clients.discard(websocket)
        if websocket in self.watchlists:
            del self.watchlists[websocket]
        if websocket in self.client_info:
            del self.client_info[websocket]
        if websocket in self.client_subscriptions:
            del self.client_subscriptions[websocket]
        
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")
        
        logger.info(f"WebSocket client {client_id} disconnected. Total clients: {len(self.connected_clients)}")
    
    async def send_initial_data(self, websocket: WebSocket):
        """Send initial data to newly connected client"""
        try:
            # Get initial data for default instruments
            default_symbols = ['AAPL', 'GOOGL', 'MSFT', 'bitcoin', 'ethereum', 'GC=F']
            assets_data = await self.get_assets_data(default_symbols)
            
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
    
    async def handle_message(self, websocket: WebSocket, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            action = data.get('action')
            
            if action == 'refresh':
                await self.handle_refresh(websocket)
            elif action == 'add_asset':
                await self.handle_add_asset(websocket, data.get('symbol'))
            elif action == 'remove_asset':
                await self.handle_remove_asset(websocket, data.get('symbol'))
            elif action == 'set_timeframe':
                await self.handle_set_timeframe(websocket, data.get('timeframe', '5m'))
            elif action == 'subscribe':
                await self.handle_subscribe(websocket, data.get('symbols', []))
            elif action == 'unsubscribe':
                await self.handle_unsubscribe(websocket, data.get('symbols', []))
            elif action == 'heartbeat':
                await self.handle_heartbeat(websocket)
            else:
                logger.warning(f"Unknown action received: {action}")
                error_message = {
                    "type": "error",
                    "message": f"Unknown action: {action}"
                }
                await websocket.send_text(json.dumps(error_message))
                
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON message: {e}")
            error_message = {
                "type": "error",
                "message": "Invalid JSON format"
            }
            await websocket.send_text(json.dumps(error_message))
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            error_message = {
                "type": "error",
                "message": "Error processing request"
            }
            await websocket.send_text(json.dumps(error_message))
    
    async def handle_refresh(self, websocket: WebSocket):
        """Handle refresh action"""
        try:
            # Refresh all data for client's subscriptions or default symbols
            symbols = list(self.client_subscriptions.get(websocket, set()))
            if not symbols:
                symbols = ['AAPL', 'GOOGL', 'MSFT', 'bitcoin', 'ethereum', 'GC=F']
            
            assets_data = await self.get_assets_data(symbols[:15])  # Limit for performance
            update_message = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "data": assets_data
            }
            await websocket.send_text(json.dumps(update_message))
        except Exception as e:
            logger.error(f"Error handling refresh: {e}")
    
    async def handle_add_asset(self, websocket: WebSocket, symbol: str):
        """Handle add asset action"""
        if symbol:
            try:
                # Add to client subscriptions
                if websocket not in self.client_subscriptions:
                    self.client_subscriptions[websocket] = set()
                self.client_subscriptions[websocket].add(symbol.upper())
                
                # Add to watchlist (in a real app, this would be stored in database)
                if websocket not in self.watchlists:
                    self.watchlists[websocket] = set()
                self.watchlists[websocket].add(symbol.upper())
                
                # Send updated watchlist
                watchlist_message = {
                    "type": "watchlist",
                    "data": list(self.watchlists[websocket])
                }
                await websocket.send_text(json.dumps(watchlist_message))
            except Exception as e:
                logger.error(f"Error adding asset {symbol}: {e}")
    
    async def handle_remove_asset(self, websocket: WebSocket, symbol: str):
        """Handle remove asset action"""
        if symbol and websocket in self.watchlists:
            try:
                self.watchlists[websocket].discard(symbol.upper())
                if websocket in self.client_subscriptions:
                    self.client_subscriptions[websocket].discard(symbol.upper())
                
                # Send updated watchlist
                watchlist_message = {
                    "type": "watchlist",
                    "data": list(self.watchlists[websocket])
                }
                await websocket.send_text(json.dumps(watchlist_message))
            except Exception as e:
                logger.error(f"Error removing asset {symbol}: {e}")
    
    async def handle_set_timeframe(self, websocket: WebSocket, timeframe: str):
        """Handle set timeframe action"""
        try:
            # Update client timeframe
            if websocket in self.client_info:
                self.client_info[websocket]["timeframe"] = timeframe
            # In a real implementation, this would affect data fetching
            # For now, we'll just acknowledge the change
            notification_message = {
                "type": "notification",
                "message": f"Timeframe set to {timeframe}"
            }
            await websocket.send_text(json.dumps(notification_message))
        except Exception as e:
            logger.error(f"Error setting timeframe: {e}")
    
    async def handle_subscribe(self, websocket: WebSocket, symbols: List[str]):
        """Handle subscribe action"""
        if symbols:
            try:
                # Add symbols to client subscriptions
                if websocket not in self.client_subscriptions:
                    self.client_subscriptions[websocket] = set()
                for symbol in symbols:
                    self.client_subscriptions[websocket].add(symbol.upper())
                
                notification_message = {
                    "type": "notification",
                    "message": f"Subscribed to {len(symbols)} assets"
                }
                await websocket.send_text(json.dumps(notification_message))
            except Exception as e:
                logger.error(f"Error subscribing to assets: {e}")
    
    async def handle_unsubscribe(self, websocket: WebSocket, symbols: List[str]):
        """Handle unsubscribe action"""
        if symbols and websocket in self.client_subscriptions:
            try:
                for symbol in symbols:
                    self.client_subscriptions[websocket].discard(symbol.upper())
                
                notification_message = {
                    "type": "notification",
                    "message": f"Unsubscribed from {len(symbols)} assets"
                }
                await websocket.send_text(json.dumps(notification_message))
            except Exception as e:
                logger.error(f"Error unsubscribing from assets: {e}")
    
    async def handle_heartbeat(self, websocket: WebSocket):
        """Handle heartbeat action"""
        try:
            # Update last heartbeat time
            if websocket in self.client_info:
                self.client_info[websocket]["last_heartbeat"] = datetime.now()
                
                # Send heartbeat response
                response = {
                    "type": "heartbeat_response",
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_text(json.dumps(response))
        except Exception as e:
            logger.error(f"Error handling heartbeat: {e}")
    
    async def send_heartbeat(self, websocket: WebSocket):
        """Send heartbeat to client to keep connection alive"""
        try:
            heartbeat_message = {
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_text(json.dumps(heartbeat_message))
        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
    
    async def get_assets_data(self, symbols: List[str]) -> List[Dict]:
        """Get data for multiple assets"""
        assets_data = []
        
        # Process symbols in smaller batches to avoid API limits
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            try:
                batch = symbols[i:i + batch_size]
                batch_data = await self.get_batch_data(batch)
                assets_data.extend(batch_data)
                # Small delay between batches to avoid rate limiting
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                # Continue with next batch instead of failing completely
                continue
        
        return assets_data
    
    async def get_batch_data(self, symbols: List[str]) -> List[Dict]:
        """Get data for a batch of symbols"""
        batch_data = []
        
        # Create tasks for concurrent fetching
        tasks = []
        for symbol in symbols:
            task = self.get_single_asset_data(symbol)
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
    
    async def get_single_asset_data(self, symbol: str) -> Optional[Dict]:
        """Get data for a single asset"""
        try:
            # Use cached data if available and recent
            cache_key = f"{symbol}"
            if cache_key in self.data_cache:
                cached_time, cached_data = self.data_cache[cache_key]
                if datetime.now() - cached_time < timedelta(seconds=30):
                    return cached_data
            
            # Get instrument info
            if symbol in FINANCIAL_INSTRUMENTS:
                instrument_info = FINANCIAL_INSTRUMENTS[symbol]
            else:
                instrument_info = {'name': symbol, 'type': 'asset'}
            
            # Generate mock data for demonstration
            # In a real implementation, you would fetch actual data from an API
            asset_data = self.generate_mock_asset_data(symbol, instrument_info)
            
            # Cache the data
            self.data_cache[cache_key] = (datetime.now(), asset_data)
            return asset_data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    def generate_mock_asset_data(self, symbol: str, instrument_info: Dict) -> Dict:
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
    
    async def data_stream_worker(self):
        """Background worker to stream data to all connected clients"""
        while True:
            try:
                if self.connected_clients:
                    # Get data for a subset of instruments
                    symbols = list(FINANCIAL_INSTRUMENTS.keys())[:15]
                    assets_data = await self.get_assets_data(symbols)
                    
                    # Create update message
                    message = {
                        "type": "update",
                        "timestamp": datetime.now().isoformat(),
                        "data": assets_data
                    }
                    message_str = json.dumps(message)
                    
                    # Send to all connected clients
                    disconnected_clients = set()
                    for client in self.connected_clients:
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
                        await self.disconnect(client)
                
                # Wait before next update
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in data stream worker: {e}")
                await asyncio.sleep(5)  # Wait before retrying

# Global WebSocket manager instance
websocket_manager = WebSocketManager()

async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    client_id = await websocket_manager.connect(websocket)
    if not client_id:
        return
    
    heartbeat_task = None
    try:
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat_worker(websocket))
        
        # Handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=CLIENT_TIMEOUT)
                await websocket_manager.handle_message(websocket, data)
            except asyncio.TimeoutError:
                logger.warning(f"Client {client_id} timed out")
                break
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error receiving message from client {client_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error for client {client_id}: {e}")
    finally:
        # Clean up client resources
        if heartbeat_task:
            heartbeat_task.cancel()
        await websocket_manager.disconnect(websocket)

async def heartbeat_worker(websocket):
    """Send periodic heartbeats to keep connection alive"""
    try:
        while websocket in websocket_manager.connected_clients:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if websocket in websocket_manager.client_info:
                websocket_manager.client_info[websocket]["last_heartbeat"] = datetime.now()
            await websocket_manager.send_heartbeat(websocket)
    except Exception as e:
        logger.error(f"Error in heartbeat worker: {e}")

async def data_stream_worker():
    """Background worker to stream data to all connected clients"""
    await websocket_manager.data_stream_worker()