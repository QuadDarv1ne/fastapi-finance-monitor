"""
FastAPI Finance Monitor - Real-time Financial Dashboard
Main application file
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import List, Dict
import requests

app = FastAPI(title="FastAPI Finance Monitor")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections
active_connections: List[WebSocket] = []


class DataFetcher:
    """Fetch financial data from various sources"""
    
    @staticmethod
    async def get_stock_data(symbol: str, period: str = "1d", interval: str = "5m"):
        """Get stock data from Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            
            if df.empty:
                return None
            
            data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "current_price": float(df['Close'].iloc[-1]),
                "change": float(df['Close'].iloc[-1] - df['Close'].iloc[0]),
                "change_percent": float((df['Close'].iloc[-1] - df['Close'].iloc[0]) / df['Close'].iloc[0] * 100),
                "volume": int(df['Volume'].iloc[-1]),
                "chart_data": [
                    {
                        "time": str(idx),
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": int(row['Volume'])
                    }
                    for idx, row in df.tail(50).iterrows()
                ]
            }
            return data
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None
    
    @staticmethod
    async def get_crypto_data(coin_id: str):
        """Get crypto data from CoinGecko"""
        try:
            # Current price
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            }
            response = requests.get(url, params=params, timeout=5)
            price_data = response.json()
            
            if coin_id not in price_data:
                return None
            
            # Historical data
            hist_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
            hist_params = {"vs_currency": "usd", "days": "1", "interval": "hourly"}
            hist_response = requests.get(hist_url, params=hist_params, timeout=5)
            hist_data = hist_response.json()
            
            current_price = price_data[coin_id]["usd"]
            
            data = {
                "symbol": coin_id.upper(),
                "timestamp": datetime.now().isoformat(),
                "current_price": current_price,
                "change_percent": price_data[coin_id].get("usd_24h_change", 0),
                "volume": price_data[coin_id].get("usd_24h_vol", 0),
                "chart_data": [
                    {
                        "time": datetime.fromtimestamp(point[0]/1000).isoformat(),
                        "price": point[1]
                    }
                    for point in hist_data.get("prices", [])[-50:]
                ]
            }
            return data
        except Exception as e:
            print(f"Error fetching {coin_id}: {e}")
            return None


class TechnicalIndicators:
    """Calculate technical indicators"""
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else 50.0
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int = 20) -> float:
        """Calculate Moving Average"""
        ma = prices.rolling(window=period).mean()
        return float(ma.iloc[-1]) if not ma.empty else 0.0


async def broadcast_data(data: dict):
    """Broadcast data to all connected WebSocket clients"""
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        active_connections.remove(conn)


async def data_stream_worker():
    """Background worker to fetch and broadcast data"""
    assets = [
        {"type": "stock", "symbol": "AAPL", "name": "Apple"},
        {"type": "stock", "symbol": "GOOGL", "name": "Google"},
        {"type": "stock", "symbol": "GC=F", "name": "Gold"},
        {"type": "crypto", "symbol": "bitcoin", "name": "Bitcoin"},
        {"type": "crypto", "symbol": "ethereum", "name": "Ethereum"},
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
            
            await asyncio.sleep(30)  # Update every 30 seconds
            
        except Exception as e:
            print(f"Error in data stream: {e}")
            await asyncio.sleep(10)


@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    asyncio.create_task(data_stream_worker())


@app.get("/")
async def get_dashboard():
    """Serve the dashboard HTML"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI Finance Monitor</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #0a0e27;
                color: #e0e0e0;
                padding: 20px;
            }
            .header {
                text-align: center;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
            }
            .header h1 {
                color: white;
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .status {
                display: inline-block;
                padding: 8px 16px;
                background: rgba(255,255,255,0.2);
                border-radius: 20px;
                font-size: 0.9em;
            }
            .status.connected { background: #10b981; }
            .status.disconnected { background: #ef4444; }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .card {
                background: #1a1f3a;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                border: 1px solid #2a2f4a;
            }
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #2a2f4a;
            }
            .asset-name {
                font-size: 1.5em;
                font-weight: bold;
                color: #667eea;
            }
            .asset-symbol {
                font-size: 0.9em;
                color: #9ca3af;
            }
            .price {
                font-size: 2em;
                font-weight: bold;
                margin: 10px 0;
            }
            .change {
                padding: 5px 10px;
                border-radius: 8px;
                font-weight: 600;
            }
            .change.positive { background: #10b981; color: white; }
            .change.negative { background: #ef4444; color: white; }
            .chart {
                height: 300px;
                margin-top: 15px;
            }
            .info-row {
                display: flex;
                justify-content: space-between;
                margin: 10px 0;
                font-size: 0.9em;
                color: #9ca3af;
            }
            .last-update {
                text-align: center;
                color: #6b7280;
                margin-top: 20px;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 FastAPI Finance Monitor</h1>
            <div id="status" class="status disconnected">Connecting...</div>
        </div>
        
        <div id="dashboard" class="grid"></div>
        
        <div class="last-update">
            Last update: <span id="lastUpdate">-</span>
        </div>

        <script>
            let ws = null;
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = '🟢 Connected';
                    document.getElementById('status').className = 'status connected';
                };
                
                ws.onclose = () => {
                    document.getElementById('status').textContent = '🔴 Disconnected';
                    document.getElementById('status').className = 'status disconnected';
                    setTimeout(connect, 3000);
                };
                
                ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    if (message.type === 'update') {
                        updateDashboard(message.data);
                        document.getElementById('lastUpdate').textContent = 
                            new Date(message.timestamp).toLocaleTimeString();
                    }
                };
            }
            
            function updateDashboard(assets) {
                const dashboard = document.getElementById('dashboard');
                dashboard.innerHTML = '';
                
                assets.forEach(asset => {
                    const card = createAssetCard(asset);
                    dashboard.appendChild(card);
                });
            }
            
            function createAssetCard(asset) {
                const card = document.createElement('div');
                card.className = 'card';
                
                const changeClass = asset.change_percent >= 0 ? 'positive' : 'negative';
                const changeSymbol = asset.change_percent >= 0 ? '▲' : '▼';
                
                card.innerHTML = `
                    <div class="card-header">
                        <div>
                            <div class="asset-name">${asset.name}</div>
                            <div class="asset-symbol">${asset.symbol}</div>
                        </div>
                        <div class="change ${changeClass}">
                            ${changeSymbol} ${Math.abs(asset.change_percent).toFixed(2)}%
                        </div>
                    </div>
                    <div class="price">$${asset.current_price.toLocaleString('en-US', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    })}</div>
                    ${asset.volume ? `<div class="info-row">
                        <span>Volume:</span>
                        <span>${asset.volume.toLocaleString('en-US')}</span>
                    </div>` : ''}
                    <div class="chart" id="chart-${asset.symbol}"></div>
                `;
                
                setTimeout(() => {
                    createChart(asset);
                }, 100);
                
                return card;
            }
            
            function createChart(asset) {
                const chartDiv = document.getElementById(`chart-${asset.symbol}`);
                if (!chartDiv || !asset.chart_data) return;
                
                let trace;
                
                if (asset.type === 'stock' && asset.chart_data[0].open !== undefined) {
                    // Candlestick chart for stocks
                    trace = {
                        type: 'candlestick',
                        x: asset.chart_data.map(d => d.time),
                        open: asset.chart_data.map(d => d.open),
                        high: asset.chart_data.map(d => d.high),
                        low: asset.chart_data.map(d => d.low),
                        close: asset.chart_data.map(d => d.close),
                        increasing: {line: {color: '#10b981'}},
                        decreasing: {line: {color: '#ef4444'}}
                    };
                } else {
                    // Line chart for crypto
                    trace = {
                        type: 'scatter',
                        mode: 'lines',
                        x: asset.chart_data.map(d => d.time),
                        y: asset.chart_data.map(d => d.price),
                        line: {
                            color: '#667eea',
                            width: 2
                        },
                        fill: 'tozeroy',
                        fillcolor: 'rgba(102, 126, 234, 0.1)'
                    };
                }
                
                const layout = {
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a',
                    font: { color: '#e0e0e0' },
                    margin: { l: 40, r: 20, t: 20, b: 40 },
                    xaxis: {
                        gridcolor: '#2a2f4a',
                        showgrid: true
                    },
                    yaxis: {
                        gridcolor: '#2a2f4a',
                        showgrid: true
                    },
                    showlegend: false
                };
                
                const config = {
                    responsive: true,
                    displayModeBar: false
                };
                
                Plotly.newPlot(chartDiv, [trace], layout, config);
            }
            
            connect();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


@app.get("/api/assets")
async def get_assets():
    """Get current data for all assets"""
    assets = [
        {"type": "stock", "symbol": "AAPL", "name": "Apple"},
        {"type": "stock", "symbol": "GOOGL", "name": "Google"},
        {"type": "stock", "symbol": "GC=F", "name": "Gold"},
        {"type": "crypto", "symbol": "bitcoin", "name": "Bitcoin"},
        {"type": "crypto", "symbol": "ethereum", "name": "Ethereum"},
    ]
    
    result = []
    for asset in assets:
        if asset["type"] == "stock":
            data = await DataFetcher.get_stock_data(asset["symbol"])
        else:
            data = await DataFetcher.get_crypto_data(asset["symbol"])
        
        if data:
            data["name"] = asset["name"]
            data["type"] = asset["type"]
            result.append(data)
    
    return {"assets": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)