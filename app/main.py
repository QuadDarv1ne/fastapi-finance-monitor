"""FastAPI Finance Monitor - Real-time Financial Dashboard
Main application file
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime
import json
from typing import List
import logging
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our modules
from api.routes import router as api_router
from api.websocket import websocket_endpoint, data_stream_worker
from database import init_db
from services.redis_cache_service import get_redis_cache_service
from services.monitoring_service import get_monitoring_service
from services.advanced_alert_service import get_advanced_alert_service
from middleware.monitoring_middleware import MonitoringMiddleware

app = FastAPI(
    title="FastAPI Finance Monitor",
    description="Real-time financial dashboard for stocks, crypto, and commodities",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)

# Initialize database and cache on startup
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    logger.info("Starting data stream worker")
    init_db()  # Initialize database
    
    # Initialize Redis cache
    redis_cache = get_redis_cache_service()
    await redis_cache.connect()
    
    # Start monitoring service
    monitoring_service = get_monitoring_service()
    asyncio.create_task(monitoring_service.log_periodic_metrics())
    
    # Start advanced alert monitoring
    from services.database_service import DatabaseService
    from database import SessionLocal
    db = SessionLocal()
    try:
        db_service = DatabaseService(db)
        advanced_alert_service = get_advanced_alert_service(db_service)
        asyncio.create_task(advanced_alert_service.start_monitoring())
    finally:
        db.close()
    
    asyncio.create_task(data_stream_worker())

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint_wrapper(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    monitoring_service = get_monitoring_service()
    monitoring_service.increment_active_connections()
    try:
        await websocket_endpoint(websocket)
    finally:
        monitoring_service.decrement_active_connections()

# Serve the dashboard HTML
@app.get("/", response_class=HTMLResponse)
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
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
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
                position: relative;
            }
            .header h1 {
                color: white;
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .header p {
                color: rgba(255,255,255,0.8);
                font-size: 1.1em;
                max-width: 800px;
                margin: 0 auto;
            }
            .status-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 15px;
                flex-wrap: wrap;
                gap: 10px;
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
            .controls {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .search-box {
                padding: 12px 15px;
                border-radius: 8px;
                border: 1px solid #2a2f4a;
                background: #1a1f3a;
                color: #e0e0e0;
                width: 300px;
                font-size: 16px;
            }
            .btn {
                padding: 12px 20px;
                border-radius: 8px;
                border: none;
                background: #667eea;
                color: white;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s ease;
            }
            .btn:hover {
                background: #5a67d8;
                transform: translateY(-2px);
            }
            .btn-secondary {
                background: #4c5a8c;
            }
            .btn-secondary:hover {
                background: #3d4870;
            }
            .btn-success {
                background: #10b981;
            }
            .btn-success:hover {
                background: #059669;
            }
            .btn-warning {
                background: #f59e0b;
            }
            .btn-warning:hover {
                background: #d97706;
            }
            .btn-info {
                background: #3b82f6;
            }
            .btn-info:hover {
                background: #2563eb;
            }
            .btn-export {
                background: #8b5cf6;
            }
            .btn-export:hover {
                background: #7c3aed;
            }
            .btn-compare {
                background: #ec4899;
            }
            .btn-compare:hover {
                background: #db2777;
            }
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
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.4);
            }
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #2a2f4a;
            }
            .asset-info {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .asset-icon {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
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
            .asset-type {
                font-size: 0.8em;
                padding: 3px 8px;
                border-radius: 10px;
                background: rgba(102, 126, 234, 0.2);
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
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }
            .change.positive { background: #10b981; color: white; }
            .change.negative { background: #ef4444; color: white; }
            .chart {
                height: 300px;
                margin-top: 15px;
            }
            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 15px;
                margin: 15px 0;
            }
            .info-item {
                background: rgba(42, 47, 74, 0.5);
                padding: 12px;
                border-radius: 10px;
                text-align: center;
            }
            .info-label {
                font-size: 0.8em;
                color: #9ca3af;
                margin-bottom: 5px;
            }
            .info-value {
                font-size: 1.1em;
                font-weight: bold;
            }
            .last-update {
                text-align: center;
                color: #6b7280;
                margin-top: 20px;
                font-size: 0.9em;
            }
            .empty-state {
                text-align: center;
                padding: 50px;
                color: #9ca3af;
            }
            .empty-state i {
                font-size: 3em;
                margin-bottom: 20px;
                color: #667eea;
            }
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
                justify-content: center;
                flex-wrap: wrap;
            }
            .tab {
                padding: 10px 20px;
                border-radius: 8px;
                background: #1a1f3a;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .tab.active {
                background: #667eea;
            }
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 8px;
                background: #10b981;
                color: white;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                transform: translateX(200%);
                transition: transform 0.3s ease;
                z-index: 1000;
            }
            .notification.show {
                transform: translateX(0);
            }
            .notification.error {
                background: #ef4444;
            }
            .watchlist-btn {
                background: none;
                border: none;
                color: #9ca3af;
                cursor: pointer;
                font-size: 1.2em;
                transition: color 0.3s ease;
            }
            .watchlist-btn.active {
                color: #fbbf24;
            }
            .watchlist-btn:hover {
                color: #fbbf24;
            }
            .indicators-panel {
                background: #1a1f3a;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                border: 1px solid #2a2f4a;
            }
            .indicators-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            .indicator-item {
                background: rgba(42, 47, 74, 0.5);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
            }
            .indicator-value {
                font-size: 1.5em;
                font-weight: bold;
                margin: 5px 0;
            }
            .indicator-positive { color: #10b981; }
            .indicator-negative { color: #ef4444; }
            .portfolio-summary {
                display: flex;
                justify-content: space-around;
                flex-wrap: wrap;
                gap: 20px;
                margin: 20px 0;
            }
            .portfolio-item {
                text-align: center;
                padding: 15px;
                background: rgba(42, 47, 74, 0.5);
                border-radius: 10px;
                min-width: 150px;
            }
            .portfolio-value {
                font-size: 1.8em;
                font-weight: bold;
                margin: 10px 0;
            }
            .portfolio-label {
                color: #9ca3af;
                font-size: 0.9em;
            }
            .alert-form {
                background: #1a1f3a;
                border-radius: 15px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                border: 1px solid #2a2f4a;
            }
            .form-row {
                display: flex;
                gap: 10px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }
            .form-group {
                flex: 1;
                min-width: 150px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                color: #9ca3af;
            }
            .form-control {
                width: 100%;
                padding: 10px;
                border-radius: 8px;
                border: 1px solid #2a2f4a;
                background: #2a2f4a;
                color: #e0e0e0;
            }
            .time-controls {
                display: flex;
                justify-content: center;
                gap: 5px;
                margin: 15px 0;
                flex-wrap: wrap;
            }
            .time-btn {
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #2a2f4a;
                background: #1a1f3a;
                color: #9ca3af;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
            }
            .time-btn.active {
                background: #667eea;
                color: white;
                border-color: #667eea;
            }
            .time-btn:hover {
                background: #2a2f4a;
                color: white;
            }
            .historical-controls {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin: 15px 0;
                flex-wrap: wrap;
            }
            .historical-btn {
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #2a2f4a;
                background: #1a1f3a;
                color: #9ca3af;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
            }
            .historical-btn.active {
                background: #667eea;
                color: white;
                border-color: #667eea;
            }
            .historical-btn:hover {
                background: #2a2f4a;
                color: white;
            }
            .export-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                z-index: 1001;
                justify-content: center;
                align-items: center;
                display: none;
            }
            .export-modal-content {
                background: #1a1f3a;
                padding: 30px;
                border-radius: 15px;
                width: 90%;
                max-width: 500px;
            }
            .export-modal h2 {
                margin-bottom: 20px;
            }
            .export-options {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin: 20px 0;
            }
            .export-option {
                padding: 15px;
                border-radius: 8px;
                background: #2a2f4a;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .export-option:hover {
                background: #667eea;
                transform: translateY(-2px);
            }
            .export-option i {
                font-size: 2em;
                margin-bottom: 10px;
                display: block;
            }
            .compare-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                z-index: 1001;
                justify-content: center;
                align-items: center;
                display: none;
            }
            .compare-modal-content {
                background: #1a1f3a;
                padding: 30px;
                border-radius: 15px;
                width: 90%;
                max-width: 600px;
                max-height: 80vh;
                overflow-y: auto;
            }
            .compare-modal h2 {
                margin-bottom: 20px;
            }
            .compare-assets-list {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin: 20px 0;
                max-height: 300px;
                overflow-y: auto;
            }
            .compare-asset-item {
                padding: 10px 15px;
                border-radius: 8px;
                background: #2a2f4a;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .compare-asset-item:hover {
                background: #667eea;
            }
            .compare-asset-item.selected {
                background: #10b981;
            }
            .compare-asset-item i {
                width: 24px;
                height: 24px;
                border-radius: 50%;
                background: #4c5a8c;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
            }
            .compare-chart-container {
                height: 400px;
                margin-top: 20px;
            }
            .compare-controls {
                display: flex;
                gap: 10px;
                margin: 20px 0;
                flex-wrap: wrap;
            }
            .compare-period-btn {
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #2a2f4a;
                background: #1a1f3a;
                color: #9ca3af;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
            }
            .compare-period-btn.active {
                background: #667eea;
                color: white;
                border-color: #667eea;
            }
            .compare-period-btn:hover {
                background: #2a2f4a;
                color: white;
            }
            
            /* Login Modal */
            .login-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                z-index: 1002;
                justify-content: center;
                align-items: center;
                display: none;
            }
            .login-modal-content {
                background: #1a1f3a;
                padding: 30px;
                border-radius: 15px;
                width: 90%;
                max-width: 400px;
            }
            .login-modal h2 {
                margin-bottom: 20px;
                text-align: center;
            }
            .login-form-group {
                margin-bottom: 20px;
            }
            .login-form-group label {
                display: block;
                margin-bottom: 5px;
                color: #9ca3af;
            }
            .login-form-control {
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                border: 1px solid #2a2f4a;
                background: #2a2f4a;
                color: #e0e0e0;
                font-size: 16px;
            }
            .login-btn {
                width: 100%;
                padding: 12px;
                border-radius: 8px;
                border: none;
                background: #667eea;
                color: white;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s ease;
                margin-top: 10px;
            }
            .login-btn:hover {
                background: #5a67d8;
            }
            .auth-links {
                text-align: center;
                margin-top: 15px;
                color: #9ca3af;
            }
            .auth-links a {
                color: #667eea;
                text-decoration: none;
                cursor: pointer;
            }
            .auth-links a:hover {
                text-decoration: underline;
            }
            @media (max-width: 768px) {
                .grid {
                    grid-template-columns: 1fr;
                }
                .header h1 {
                    font-size: 2em;
                }
                .search-box {
                    width: 100%;
                }
                .controls {
                    flex-direction: column;
                    align-items: center;
                }
                .portfolio-summary {
                    flex-direction: column;
                }
                .time-controls {
                    flex-wrap: wrap;
                }
                .export-options {
                    grid-template-columns: 1fr;
                }
                .compare-assets-list {
                    flex-direction: column;
                }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1><i class="fas fa-chart-line"></i> FastAPI Finance Monitor</h1>
            <p>Real-time monitoring of stocks, cryptocurrencies, and commodities</p>
            <div class="status-bar">
                <div id="status" class="status disconnected">Connecting...</div>
                <div class="status">Updates every 30 seconds</div>
                <div id="userStatus" class="status" style="display: none;">Logged in as <span id="username"></span></div>
                <button id="loginBtn" class="btn" style="display: none;" onclick="showLoginModal()">Login</button>
                <button id="logoutBtn" class="btn btn-secondary" style="display: none;" onclick="logout()">Logout</button>
            </div>
        </div>
        
        <!-- Login Modal -->
        <div id="loginModal" class="login-modal">
            <div class="login-modal-content">
                <h2><i class="fas fa-user"></i> Login</h2>
                <div class="login-form-group">
                    <label for="loginUsername">Username</label>
                    <input type="text" id="loginUsername" class="login-form-control" placeholder="Enter your username">
                </div>
                <div class="login-form-group">
                    <label for="loginPassword">Password</label>
                    <input type="password" id="loginPassword" class="login-form-control" placeholder="Enter your password">
                </div>
                <button class="login-btn" onclick="login()">Login</button>
                <div class="auth-links">
                    <p>Don't have an account? <a onclick="showRegisterForm()">Register</a></p>
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                    <button class="btn btn-secondary" onclick="closeLoginModal()">Cancel</button>
                </div>
            </div>
        </div>
        
        <div class="tabs">
            <div class="tab active" data-tab="all">All Assets</div>
            <div class="tab" data-tab="stocks">Stocks</div>
            <div class="tab" data-tab="crypto">Crypto</div>
            <div class="tab" data-tab="commodities">Commodities</div>
            <div class="tab" data-tab="forex">Forex</div>
            <div class="tab" data-tab="watchlist">My Watchlist</div>
            <div class="tab" data-tab="portfolio">Portfolio</div>
        </div>
        
        <div class="time-controls">
            <button class="time-btn" data-interval="1m">1m</button>
            <button class="time-btn active" data-interval="5m">5m</button>
            <button class="time-btn" data-interval="10m">10m</button>
            <button class="time-btn" data-interval="30m">30m</button>
            <button class="time-btn" data-interval="1h">1h</button>
            <button class="time-btn" data-interval="3h">3h</button>
            <button class="time-btn" data-interval="6h">6h</button>
            <button class="time-btn" data-interval="12h">12h</button>
            <button class="time-btn" data-interval="1d">1d</button>
        </div>
        
        <div class="historical-controls" id="historicalControls" style="display: none;">
            <button class="historical-btn" data-period="1d">1D</button>
            <button class="historical-btn" data-period="5d">5D</button>
            <button class="historical-btn active" data-period="1mo">1M</button>
            <button class="historical-btn" data-period="3mo">3M</button>
            <button class="historical-btn" data-period="6mo">6M</button>
            <button class="historical-btn" data-period="1y">1Y</button>
            <button class="historical-btn" data-period="5y">5Y</button>
        </div>
        
        <div class="controls">
            <input type="text" id="symbolInput" class="search-box" placeholder="Search assets (e.g. AAPL, Bitcoin)">
            <button class="btn" onclick="searchAssets()"><i class="fas fa-search"></i> Search</button>
            <button class="btn btn-secondary" onclick="refreshData()"><i class="fas fa-sync-alt"></i> Refresh</button>
            <button class="btn btn-success" onclick="showAddAssetModal()"><i class="fas fa-plus"></i> Add Asset</button>
            <button class="btn btn-warning" onclick="showCreateAlertModal()"><i class="fas fa-bell"></i> Create Alert</button>
            <button class="btn btn-info" onclick="toggleAutoRefresh()"><i class="fas fa-play"></i> Auto Refresh</button>
            <button class="btn btn-compare" onclick="showCompareModal()"><i class="fas fa-chart-bar"></i> Compare Assets</button>
        </div>
        
        <!-- Portfolio Summary -->
        <div class="portfolio-summary" id="portfolioSummary" style="display: none;">
            <div class="portfolio-item">
                <div class="portfolio-label">Total Value</div>
                <div class="portfolio-value" id="totalValue">$0.00</div>
            </div>
            <div class="portfolio-item">
                <div class="portfolio-label">Total Gain/Loss</div>
                <div class="portfolio-value" id="totalGain">$0.00</div>
            </div>
            <div class="portfolio-item">
                <div class="portfolio-label">Return</div>
                <div class="portfolio-value" id="totalReturn">0.00%</div>
            </div>
        </div>
        
        <!-- Technical Indicators Panel -->
        <div class="indicators-panel" id="indicatorsPanel" style="display: none;">
            <h3><i class="fas fa-chart-bar"></i> Technical Indicators</h3>
            <div class="indicators-grid" id="indicatorsGrid">
                <!-- Indicators will be populated here -->
            </div>
        </div>
        
        <!-- Alert Form -->
        <div class="alert-form" id="alertForm" style="display: none;">
            <h3><i class="fas fa-bell"></i> Create Price Alert</h3>
            <div class="form-row">
                <div class="form-group">
                    <label for="alertSymbol">Asset Symbol</label>
                    <input type="text" id="alertSymbol" class="form-control" placeholder="e.g. AAPL">
                </div>
                <div class="form-group">
                    <label for="alertPrice">Target Price</label>
                    <input type="number" id="alertPrice" class="form-control" step="0.01" placeholder="e.g. 150.00">
                </div>
                <div class="form-group">
                    <label for="alertType">Alert Type</label>
                    <select id="alertType" class="form-control">
                        <option value="above">Price Above</option>
                        <option value="below">Price Below</option>
                    </select>
                </div>
            </div>
            <button class="btn btn-success" onclick="createAlert()"><i class="fas fa-bell"></i> Create Alert</button>
        </div>
        
        <div id="dashboard" class="grid">
            <div class="empty-state">
                <i class="fas fa-spinner fa-spin"></i>
                <h3>Loading financial data...</h3>
                <p>Please wait while we fetch the latest market information</p>
            </div>
        </div>
        
        <div class="last-update">
            Last update: <span id="lastUpdate">-</span>
        </div>
        
        <div id="notification" class="notification">
            Asset added to watchlist!
        </div>
        
        <!-- Add Asset Modal -->
        <div id="addAssetModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1001; justify-content: center; align-items: center;">
            <div style="background: #1a1f3a; padding: 30px; border-radius: 15px; width: 90%; max-width: 500px;">
                <h2 style="margin-bottom: 20px;"><i class="fas fa-plus-circle"></i> Add Asset to Watchlist</h2>
                <input type="text" id="newAssetSymbol" class="search-box" placeholder="Enter symbol (e.g. AAPL, BTC)" style="width: 100%; margin-bottom: 15px;">
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="btn btn-secondary" onclick="closeAddAssetModal()">Cancel</button>
                    <button class="btn btn-success" onclick="addAssetToWatchlist()">Add</button>
                </div>
            </div>
        </div>
        
        <!-- Create Alert Modal -->
        <div id="createAlertModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1001; justify-content: center; align-items: center;">
            <div style="background: #1a1f3a; padding: 30px; border-radius: 15px; width: 90%; max-width: 500px;">
                <h2 style="margin-bottom: 20px;"><i class="fas fa-bell"></i> Create Price Alert</h2>
                <div class="form-row">
                    <div class="form-group">
                        <label for="modalAlertSymbol">Asset Symbol</label>
                        <input type="text" id="modalAlertSymbol" class="form-control" placeholder="e.g. AAPL">
                    </div>
                    <div class="form-group">
                        <label for="modalAlertPrice">Target Price</label>
                        <input type="number" id="modalAlertPrice" class="form-control" step="0.01" placeholder="e.g. 150.00">
                    </div>
                </div>
                <div class="form-group">
                    <label for="modalAlertType">Alert Type</label>
                    <select id="modalAlertType" class="form-control">
                        <option value="above">Price Above</option>
                        <option value="below">Price Below</option>
                    </select>
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                    <button class="btn btn-secondary" onclick="closeCreateAlertModal()">Cancel</button>
                    <button class="btn btn-success" onclick="createAlertFromModal()">Create Alert</button>
                </div>
            </div>
        </div>
        
        <!-- Export Modal -->
        <div id="exportModal" class="export-modal">
            <div class="export-modal-content">
                <h2><i class="fas fa-file-export"></i> Export Data</h2>
                <p>Export historical data for <span id="exportSymbol"></span></p>
                <div class="export-options">
                    <div class="export-option" onclick="exportData('csv')">
                        <i class="fas fa-file-csv"></i>
                        <div>CSV Format</div>
                    </div>
                    <div class="export-option" onclick="exportData('xlsx')">
                        <i class="fas fa-file-excel"></i>
                        <div>Excel Format</div>
                    </div>
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="btn btn-secondary" onclick="closeExportModal()">Cancel</button>
                </div>
            </div>
        </div>
        
        <!-- Compare Modal -->
        <div id="compareModal" class="compare-modal">
            <div class="compare-modal-content">
                <h2><i class="fas fa-chart-bar"></i> Compare Assets</h2>
                <p>Select assets to compare their performance</p>
                
                <div class="compare-controls">
                    <button class="compare-period-btn active" data-period="1mo">1M</button>
                    <button class="compare-period-btn" data-period="3mo">3M</button>
                    <button class="compare-period-btn" data-period="6mo">6M</button>
                    <button class="compare-period-btn" data-period="1y">1Y</button>
                    <button class="compare-period-btn" data-period="5y">5Y</button>
                </div>
                
                <div class="compare-assets-list" id="compareAssetsList">
                    <!-- Assets will be populated here -->
                </div>
                
                <div class="compare-chart-container" id="compareChartContainer">
                    <div class="empty-state">
                        <i class="fas fa-chart-line"></i>
                        <h3>Select assets to compare</h3>
                        <p>Choose at least two assets to see their performance comparison</p>
                    </div>
                </div>
                
                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                    <button class="btn btn-secondary" onclick="closeCompareModal()">Close</button>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let currentAssets = [];
            let userWatchlist = new Set();
            let activeTab = 'all';
            let selectedAsset = null;
            let currentTimeframe = '5m';
            let currentHistoricalPeriod = '1mo';
            let autoRefreshEnabled = true;
            let refreshInterval = null;
            let selectedCompareAssets = new Set();
            let comparePeriod = '1mo';
            let authToken = null;
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = '🟢 Connected';
                    document.getElementById('status').className = 'status connected';
                    showNotification('Connected to real-time data stream');
                    
                    // Request data with current timeframe
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({action: 'set_timeframe', timeframe: currentTimeframe}));
                    }
                };
                
                ws.onclose = () => {
                    document.getElementById('status').textContent = '🔴 Disconnected';
                    document.getElementById('status').className = 'status disconnected';
                    setTimeout(connect, 3000);
                };
                
                ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        handleMessage(message);
                    } catch (e) {
                        console.error('Error parsing message:', e);
                    }
                };
            }
            
            // Authentication functions
            function showLoginModal() {
                document.getElementById('loginModal').style.display = 'flex';
                document.getElementById('loginUsername').focus();
            }
            
            function closeLoginModal() {
                document.getElementById('loginModal').style.display = 'none';
                document.getElementById('loginUsername').value = '';
                document.getElementById('loginPassword').value = '';
            }
            
            async function login() {
                const username = document.getElementById('loginUsername').value.trim();
                const password = document.getElementById('loginPassword').value;
                
                if (!username || !password) {
                    showNotification('Please fill in all fields', 'error');
                    return;
                }
                
                try {
                    const response = await fetch('/api/users/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                        },
                        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || 'Login failed');
                    }
                    
                    const data = await response.json();
                    authToken = data.access_token;
                    
                    // Update UI
                    document.getElementById('username').textContent = data.username;
                    document.getElementById('userStatus').style.display = 'inline-block';
                    document.getElementById('loginBtn').style.display = 'none';
                    document.getElementById('logoutBtn').style.display = 'inline-block';
                    
                    closeLoginModal();
                    showNotification(`Welcome, ${data.username}!`);
                    
                    // Store token in localStorage for persistence
                    localStorage.setItem('authToken', authToken);
                    localStorage.setItem('username', data.username);
                } catch (error) {
                    console.error('Login error:', error);
                    showNotification(error.message || 'Login failed', 'error');
                }
            }
            
            function logout() {
                authToken = null;
                
                // Update UI
                document.getElementById('userStatus').style.display = 'none';
                document.getElementById('loginBtn').style.display = 'inline-block';
                document.getElementById('logoutBtn').style.display = 'none';
                
                // Clear stored token
                localStorage.removeItem('authToken');
                localStorage.removeItem('username');
                
                showNotification('You have been logged out');
            }
            
            function checkAuthStatus() {
                // Check if user is already logged in
                const token = localStorage.getItem('authToken');
                const username = localStorage.getItem('username');
                
                if (token && username) {
                    authToken = token;
                    document.getElementById('username').textContent = username;
                    document.getElementById('userStatus').style.display = 'inline-block';
                    document.getElementById('loginBtn').style.display = 'none';
                    document.getElementById('logoutBtn').style.display = 'inline-block';
                } else {
                    document.getElementById('loginBtn').style.display = 'inline-block';
                }
            }
            
            function showRegisterForm() {
                closeLoginModal();
                showNotification('Registration feature coming soon!');
            }
            
            function handleMessage(message) {
                if (message.type === 'update') {
                    currentAssets = message.data;
                    updateDashboard(message.data);
                    document.getElementById('lastUpdate').textContent = 
                        new Date(message.timestamp).toLocaleTimeString();
                } else if (message.type === 'init') {
                    // Initialize user watchlist
                    if (message.watchlist) {
                        userWatchlist = new Set(message.watchlist);
                    }
                } else if (message.type === 'notification') {
                    showNotification(message.message);
                } else if (message.type === 'error') {
                    showNotification(message.message, 'error');
                } else if (message.type === 'watchlist') {
                    if (message.data) {
                        userWatchlist = new Set(message.data);
                        if (activeTab === 'watchlist') {
                            updateDashboard(currentAssets);
                        }
                    }
                }
            }
            
            function updateTimeframe(interval) {
                currentTimeframe = interval;
                
                // Update active button
                document.querySelectorAll('.time-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                event.target.classList.add('active');
                
                // Request new data with selected timeframe
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({action: 'set_timeframe', timeframe: interval}));
                    showNotification(`Timeframe changed to ${interval}`);
                }
            }
            
            function updateHistoricalPeriod(period) {
                currentHistoricalPeriod = period;
                
                // Update active button
                document.querySelectorAll('.historical-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                event.target.classList.add('active');
                
                // Fetch historical data for selected asset
                if (selectedAsset) {
                    fetchHistoricalData(selectedAsset, period);
                }
            }
            
            function updateComparePeriod(period) {
                comparePeriod = period;
                
                // Update active button
                document.querySelectorAll('.compare-period-btn').forEach(btn => {
                    btn.classList.remove('active');
                });
                event.target.classList.add('active');
                
                // Update comparison chart if assets are selected
                if (selectedCompareAssets.size > 0) {
                    loadComparisonData();
                }
            }
            
            function fetchHistoricalData(symbol, period) {
                // In a real implementation, this would fetch from the API
                showNotification(`Fetching historical data for ${symbol} (${period})`);
                
                // Mock implementation - in a real app, you would make an API call
                setTimeout(() => {
                    showNotification(`Historical data loaded for ${symbol}`);
                }, 1000);
            }
            
            function toggleAutoRefresh() {
                autoRefreshEnabled = !autoRefreshEnabled;
                const button = event.target.closest('.btn');
                
                if (autoRefreshEnabled) {
                    button.innerHTML = '<i class="fas fa-pause"></i> Pause';
                    button.classList.remove('btn-info');
                    button.classList.add('btn-warning');
                    
                    // Start auto refresh
                    refreshInterval = setInterval(() => {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({action: 'refresh'}));
                        }
                    }, 30000); // 30 seconds
                } else {
                    button.innerHTML = '<i class="fas fa-play"></i> Auto Refresh';
                    button.classList.remove('btn-warning');
                    button.classList.add('btn-info');
                    
                    // Stop auto refresh
                    if (refreshInterval) {
                        clearInterval(refreshInterval);
                        refreshInterval = null;
                    }
                }
            }
            
            function updateDashboard(assets) {
                // Filter assets based on active tab
                let filteredAssets = assets;
                if (activeTab === 'stocks') {
                    filteredAssets = assets.filter(asset => asset.type === 'stock');
                } else if (activeTab === 'crypto') {
                    filteredAssets = assets.filter(asset => asset.type === 'crypto');
                } else if (activeTab === 'commodities') {
                    filteredAssets = assets.filter(asset => asset.type === 'commodity');
                } else if (activeTab === 'forex') {
                    filteredAssets = assets.filter(asset => asset.type === 'forex');
                } else if (activeTab === 'watchlist') {
                    filteredAssets = assets.filter(asset => userWatchlist.has(asset.symbol));
                } else if (activeTab === 'portfolio') {
                    // For portfolio tab, we'll show a different view
                    showPortfolioView(assets);
                    return;
                }
                
                // Show/hide elements based on tab
                document.getElementById('portfolioSummary').style.display = 'none';
                document.getElementById('indicatorsPanel').style.display = 'none';
                document.getElementById('alertForm').style.display = 'none';
                document.getElementById('historicalControls').style.display = 'none';
                
                const dashboard = document.getElementById('dashboard');
                
                if (filteredAssets.length === 0) {
                    let emptyMessage = '';
                    if (activeTab === 'watchlist') {
                        emptyMessage = `
                            <div class="empty-state">
                                <i class="fas fa-star"></i>
                                <h3>Your Watchlist is Empty</h3>
                                <p>Add assets to your watchlist to track them here</p>
                                <button class="btn" onclick="showAddAssetModal()" style="margin-top: 20px;">
                                    <i class="fas fa-plus"></i> Add Asset
                                </button>
                            </div>
                        `;
                    } else {
                        emptyMessage = `
                            <div class="empty-state">
                                <i class="fas fa-search"></i>
                                <h3>No assets found</h3>
                                <p>Try searching for a different asset or check back later</p>
                            </div>
                        `;
                    }
                    dashboard.innerHTML = emptyMessage;
                    return;
                }
                
                dashboard.innerHTML = '';
                
                filteredAssets.forEach(asset => {
                    const card = createAssetCard(asset);
                    dashboard.appendChild(card);
                });
            }
            
            function showPortfolioView(assets) {
                const dashboard = document.getElementById('dashboard');
                dashboard.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-wallet"></i>
                        <h3>Portfolio Management</h3>
                        <p>Track your investments and monitor performance</p>
                        <button class="btn btn-success" onclick="showCreatePortfolioModal()" style="margin-top: 20px;">
                            <i class="fas fa-plus"></i> Create Portfolio
                        </button>
                    </div>
                `;
                
                // Show portfolio summary
                document.getElementById('portfolioSummary').style.display = 'flex';
                
                // Update portfolio summary with mock data
                updatePortfolioSummary();
            }
            
            function updatePortfolioSummary() {
                // Mock portfolio data - in a real app, this would come from the backend
                document.getElementById('totalValue').textContent = '$25,430.75';
                document.getElementById('totalGain').textContent = '+$1,245.30';
                document.getElementById('totalGain').className = 'portfolio-value indicator-positive';
                document.getElementById('totalReturn').textContent = '+5.15%';
                document.getElementById('totalReturn').className = 'portfolio-value indicator-positive';
            }
            
            function createAssetCard(asset) {
                const card = document.createElement('div');
                card.className = 'card';
                card.dataset.symbol = asset.symbol;
                
                const changeClass = asset.change_percent >= 0 ? 'positive' : 'negative';
                const changeSymbol = asset.change_percent >= 0 ? '<i class="fas fa-arrow-up"></i>' : '<i class="fas fa-arrow-down"></i>';
                const assetIcon = getAssetIcon(asset.symbol);
                const assetTypeClass = asset.type === 'stock' ? 'Stock' : 
                                     asset.type === 'crypto' ? 'Crypto' : 
                                     asset.type === 'commodity' ? 'Commodity' : 
                                     asset.type === 'forex' ? 'Forex' : 'Asset';
                const isInWatchlist = userWatchlist.has(asset.symbol);
                
                card.innerHTML = `
                    <div class="card-header">
                        <div class="asset-info">
                            <div class="asset-icon">${assetIcon}</div>
                            <div>
                                <div class="asset-name">${asset.name}</div>
                                <div class="asset-symbol">${asset.symbol}</div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <button class="watchlist-btn ${isInWatchlist ? 'active' : ''}" 
                                    onclick="toggleWatchlist('${asset.symbol}')" 
                                    title="${isInWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}">
                                <i class="fas fa-star"></i>
                            </button>
                            <div>
                                <div class="asset-type">${assetTypeClass}</div>
                                <div class="change ${changeClass}">
                                    ${changeSymbol} ${Math.abs(asset.change_percent).toFixed(2)}%
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="price">$${formatPrice(asset.current_price)}</div>
                    <div class="info-grid">
                        ${asset.open ? `
                        <div class="info-item">
                            <div class="info-label">Open</div>
                            <div class="info-value">$${formatPrice(asset.open)}</div>
                        </div>` : ''}
                        ${asset.high ? `
                        <div class="info-item">
                            <div class="info-label">High</div>
                            <div class="info-value">$${formatPrice(asset.high)}</div>
                        </div>` : ''}
                        ${asset.low ? `
                        <div class="info-item">
                            <div class="info-label">Low</div>
                            <div class="info-value">$${formatPrice(asset.low)}</div>
                        </div>` : ''}
                        ${asset.volume ? `
                        <div class="info-item">
                            <div class="info-label">Volume</div>
                            <div class="info-value">${formatNumber(asset.volume)}</div>
                        </div>` : ''}
                        ${asset.market_cap ? `
                        <div class="info-item">
                            <div class="info-label">Market Cap</div>
                            <div class="info-value">$${formatLargeNumber(asset.market_cap)}</div>
                        </div>` : ''}
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 15px;">
                        <button class="btn btn-secondary" onclick="showIndicators('${asset.symbol}')">
                            <i class="fas fa-chart-line"></i> Indicators
                        </button>
                        <button class="btn btn-warning" onclick="showCreateAlertForAsset('${asset.symbol}')">
                            <i class="fas fa-bell"></i> Alert
                        </button>
                        <button class="btn btn-info" onclick="showHistoricalData('${asset.symbol}')">
                            <i class="fas fa-history"></i> Historical
                        </button>
                        <button class="btn btn-export" onclick="showExportModal('${asset.symbol}')">
                            <i class="fas fa-file-export"></i> Export
                        </button>
                    </div>
                    <div class="chart" id="chart-${asset.symbol}"></div>
                `;
                
                setTimeout(() => {
                    createChart(asset);
                }, 100);
                
                return card;
            }
            
            function showHistoricalData(symbol) {
                selectedAsset = symbol;
                document.getElementById('historicalControls').style.display = 'flex';
                showNotification(`Showing historical data for ${symbol}`);
                fetchHistoricalData(symbol, currentHistoricalPeriod);
            }
            
            function showExportModal(symbol) {
                selectedAsset = symbol;
                document.getElementById('exportSymbol').textContent = symbol;
                document.getElementById('exportModal').style.display = 'flex';
            }
            
            function closeExportModal() {
                document.getElementById('exportModal').style.display = 'none';
            }
            
            function exportData(format) {
                if (!selectedAsset) return;
                
                // Create download link
                const url = `/api/asset/${selectedAsset}/export?format=${format}&period=${currentHistoricalPeriod}`;
                const link = document.createElement('a');
                link.href = url;
                link.download = `${selectedAsset}_data.${format}`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                closeExportModal();
                showNotification(`Exporting ${selectedAsset} data as ${format.toUpperCase()}`);
            }
            
            function showCompareModal() {
                document.getElementById('compareModal').style.display = 'flex';
                populateCompareAssetsList();
            }
            
            function closeCompareModal() {
                document.getElementById('compareModal').style.display = 'none';
                selectedCompareAssets.clear();
            }
            
            function populateCompareAssetsList() {
                const container = document.getElementById('compareAssetsList');
                container.innerHTML = '';
                
                // Use current assets or a default list
                const assetsToDisplay = currentAssets.length > 0 ? currentAssets : [
                    {symbol: 'AAPL', name: 'Apple', type: 'stock'},
                    {symbol: 'GOOGL', name: 'Google', type: 'stock'},
                    {symbol: 'MSFT', name: 'Microsoft', type: 'stock'},
                    {symbol: 'bitcoin', name: 'Bitcoin', type: 'crypto'},
                    {symbol: 'ethereum', name: 'Ethereum', type: 'crypto'},
                    {symbol: 'GC=F', name: 'Gold', type: 'commodity'}
                ];
                
                assetsToDisplay.forEach(asset => {
                    const assetItem = document.createElement('div');
                    assetItem.className = `compare-asset-item ${selectedCompareAssets.has(asset.symbol) ? 'selected' : ''}`;
                    assetItem.dataset.symbol = asset.symbol;
                    assetItem.innerHTML = `
                        <i>${getAssetIcon(asset.symbol)}</i>
                        <span>${asset.name} (${asset.symbol})</span>
                    `;
                    assetItem.onclick = () => toggleCompareAsset(asset.symbol);
                    container.appendChild(assetItem);
                });
            }
            
            function toggleCompareAsset(symbol) {
                if (selectedCompareAssets.has(symbol)) {
                    selectedCompareAssets.delete(symbol);
                } else {
                    selectedCompareAssets.add(symbol);
                }
                
                // Update UI
                populateCompareAssetsList();
                
                // Load comparison data if at least 2 assets are selected
                if (selectedCompareAssets.size >= 2) {
                    loadComparisonData();
                } else {
                    // Show empty state
                    document.getElementById('compareChartContainer').innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-chart-line"></i>
                            <h3>Select assets to compare</h3>
                            <p>Choose at least two assets to see their performance comparison</p>
                        </div>
                    `;
                }
            }
            
            async function loadComparisonData() {
                if (selectedCompareAssets.size < 2) return;
                
                try {
                    showNotification('Loading comparison data...');
                    
                    // Create query string for symbols
                    const symbols = Array.from(selectedCompareAssets).join(',');
                    const url = `/api/assets/compare?symbols=${encodeURIComponent(symbols)}&period=${comparePeriod}`;
                    
                    const response = await fetch(url);
                    if (!response.ok) {
                        throw new Error('Failed to load comparison data');
                    }
                    
                    const data = await response.json();
                    renderComparisonChart(data.assets);
                    
                } catch (error) {
                    console.error('Error loading comparison data:', error);
                    showNotification('Error loading comparison data', 'error');
                }
            }
            
            function renderComparisonChart(assets) {
                const container = document.getElementById('compareChartContainer');
                
                // Prepare data for chart
                const traces = [];
                
                assets.forEach(asset => {
                    // Normalize prices to percentage change from first point
                    if (asset.chart_data && asset.chart_data.length > 0) {
                        const firstPrice = asset.chart_data[0].price || asset.chart_data[0].close;
                        const normalizedPrices = asset.chart_data.map(point => {
                            const price = point.price || point.close;
                            return ((price - firstPrice) / firstPrice) * 100;
                        });
                        
                        traces.push({
                            type: 'scatter',
                            mode: 'lines',
                            x: asset.chart_data.map(point => point.time),
                            y: normalizedPrices,
                            name: `${asset.name} (${asset.symbol})`,
                            line: {
                                width: 3
                            }
                        });
                    }
                });
                
                const layout = {
                    paper_bgcolor: '#1a1f3a',
                    plot_bgcolor: '#1a1f3a',
                    font: { color: '#e0e0e0' },
                    margin: { l: 60, r: 20, t: 40, b: 60 },
                    xaxis: {
                        gridcolor: '#2a2f4a',
                        showgrid: true,
                        tickfont: { size: 12 }
                    },
                    yaxis: {
                        gridcolor: '#2a2f4a',
                        showgrid: true,
                        tickfont: { size: 12 },
                        title: {
                            text: 'Performance (%)',
                            font: { size: 14 }
                        },
                        tickformat: '.1f'
                    },
                    showlegend: true,
                    legend: {
                        orientation: 'h',
                        y: -0.3,
                        x: 0.5,
                        xanchor: 'center'
                    }
                };
                
                const config = {
                    responsive: true,
                    displayModeBar: true
                };
                
                // Clear container and create chart
                container.innerHTML = '<div id="comparisonChart" style="width:100%;height:100%;"></div>';
                Plotly.newPlot('comparisonChart', traces, layout, config);
                
                showNotification(`Showing comparison for ${assets.length} assets`);
            }
            
            function getAssetIcon(symbol) {
                const icons = {
                    'AAPL': 'A',
                    'GOOGL': 'G',
                    'MSFT': 'M',
                    'TSLA': 'T',
                    'AMZN': 'A',
                    'META': 'M',
                    'NVDA': 'N',
                    'NFLX': 'N',
                    'DIS': 'D',
                    'V': 'V',
                    'JPM': 'J',
                    'WMT': 'W',
                    'PG': 'P',
                    'KO': 'K',
                    'XOM': 'X',
                    'bitcoin': '₿',
                    'ethereum': 'Ξ',
                    'solana': '◎',
                    'cardano': '₳',
                    'polkadot': '●',
                    'litecoin': 'Ł',
                    'chainlink': '⬡',
                    'GC=F': 'G',
                    'CL=F': 'O',
                    'SI=F': 'S',
                    'HG=F': 'C',
                    'EURUSD': '€',
                    'GBPUSD': '£',
                    'USDJPY': '¥',
                    'AUDUSD': 'A',
                    'USDCAD': 'C'
                };
                return icons[symbol] || symbol.charAt(0).toUpperCase();
            }
            
            function formatPrice(price) {
                if (price < 1) {
                    return price.toFixed(6);
                } else if (price < 100) {
                    return price.toFixed(2);
                } else {
                    return price.toFixed(2);
                }
            }
            
            function formatNumber(num) {
                if (num >= 1000000000) {
                    return (num / 1000000000).toFixed(1) + 'B';
                } else if (num >= 1000000) {
                    return (num / 1000000).toFixed(1) + 'M';
                } else if (num >= 1000) {
                    return (num / 1000).toFixed(1) + 'K';
                } else {
                    return num.toString();
                }
            }
            
            function formatLargeNumber(num) {
                if (num >= 1000000000000) {
                    return (num / 1000000000000).toFixed(1) + 'T';
                } else if (num >= 1000000000) {
                    return (num / 1000000000).toFixed(1) + 'B';
                } else if (num >= 1000000) {
                    return (num / 1000000).toFixed(1) + 'M';
                } else {
                    return formatNumber(num);
                }
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
                    // Line chart for crypto, commodities and others
                    trace = {
                        type: 'scatter',
                        mode: 'lines',
                        x: asset.chart_data.map(d => d.time || d.timestamp),
                        y: asset.chart_data.map(d => d.price || d.close),
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
                        showgrid: true,
                        tickfont: { size: 10 },
                        title: {
                            text: currentTimeframe,
                            font: { size: 12, color: '#9ca3af' }
                        }
                    },
                    yaxis: {
                        gridcolor: '#2a2f4a',
                        showgrid: true,
                        tickfont: { size: 10 },
                        tickformat: asset.current_price < 1 ? '.6f' : '.2f'
                    },
                    showlegend: false
                };
                
                const config = {
                    responsive: true,
                    displayModeBar: false
                };
                
                Plotly.newPlot(chartDiv, [trace], layout, config);
            }
            
            function searchAssets() {
                const query = document.getElementById('symbolInput').value.trim();
                if (query) {
                    // In a real app, this would call an API endpoint
                    showNotification(`Searching for: ${query}`);
                    document.getElementById('symbolInput').value = '';
                }
            }
            
            function refreshData() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({action: 'refresh'}));
                    showNotification('Refreshing data...');
                }
            }
            
            function toggleWatchlist(symbol) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    if (userWatchlist.has(symbol)) {
                        ws.send(JSON.stringify({action: 'remove_asset', symbol: symbol}));
                        userWatchlist.delete(symbol);
                        showNotification(`Removed ${symbol} from watchlist`);
                    } else {
                        ws.send(JSON.stringify({action: 'add_asset', symbol: symbol}));
                        userWatchlist.add(symbol);
                        showNotification(`Added ${symbol} to watchlist`);
                    }
                    
                    // Update UI if we're on the watchlist tab
                    if (activeTab === 'watchlist') {
                        updateDashboard(currentAssets);
                    }
                }
            }
            
            function showAddAssetModal() {
                document.getElementById('addAssetModal').style.display = 'flex';
                document.getElementById('newAssetSymbol').focus();
            }
            
            function closeAddAssetModal() {
                document.getElementById('addAssetModal').style.display = 'none';
                document.getElementById('newAssetSymbol').value = '';
            }
            
            function addAssetToWatchlist() {
                const symbol = document.getElementById('newAssetSymbol').value.trim().toUpperCase();
                if (symbol && ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({action: 'add_asset', symbol: symbol}));
                    userWatchlist.add(symbol);
                    closeAddAssetModal();
                    showNotification(`Added ${symbol} to watchlist`);
                    
                    // Update UI if we're on the watchlist tab
                    if (activeTab === 'watchlist') {
                        updateDashboard(currentAssets);
                    }
                }
            }
            
            function showIndicators(symbol) {
                selectedAsset = symbol;
                document.getElementById('indicatorsPanel').style.display = 'block';
                loadIndicators(symbol);
            }
            
            function loadIndicators(symbol) {
                // Mock indicators data - in a real app, this would fetch from API
                const indicators = {
                    rsi: 62.5,
                    macd: { value: 1.25, signal: 0.85 },
                    bollinger: { upper: 155.30, middle: 148.75, lower: 142.20 },
                    ma_20: 148.75,
                    ma_50: 142.30
                };
                
                const grid = document.getElementById('indicatorsGrid');
                grid.innerHTML = `
                    <div class="indicator-item">
                        <div class="info-label">RSI (14)</div>
                        <div class="indicator-value ${indicators.rsi > 70 ? 'indicator-negative' : indicators.rsi < 30 ? 'indicator-positive' : ''}">
                            ${indicators.rsi.toFixed(1)}
                        </div>
                        <div class="info-label">${indicators.rsi > 70 ? 'Overbought' : indicators.rsi < 30 ? 'Oversold' : 'Neutral'}</div>
                    </div>
                    <div class="indicator-item">
                        <div class="info-label">MACD</div>
                        <div class="indicator-value ${indicators.macd.value > indicators.macd.signal ? 'indicator-positive' : 'indicator-negative'}">
                            ${indicators.macd.value.toFixed(2)}
                        </div>
                        <div class="info-label">Signal: ${indicators.macd.signal.toFixed(2)}</div>
                    </div>
                    <div class="indicator-item">
                        <div class="info-label">MA (20)</div>
                        <div class="indicator-value indicator-positive">
                            $${indicators.ma_20.toFixed(2)}
                        </div>
                        <div class="info-label">Trend: Bullish</div>
                    </div>
                    <div class="indicator-item">
                        <div class="info-label">MA (50)</div>
                        <div class="indicator-value indicator-positive">
                            $${indicators.ma_50.toFixed(2)}
                        </div>
                        <div class="info-label">Trend: Bullish</div>
                    </div>
                    <div class="indicator-item">
                        <div class="info-label">Bollinger Bands</div>
                        <div class="info-label">Upper: $${indicators.bollinger.upper.toFixed(2)}</div>
                        <div class="info-label">Lower: $${indicators.bollinger.lower.toFixed(2)}</div>
                    </div>
                `;
            }
            
            function showCreateAlertModal() {
                document.getElementById('createAlertModal').style.display = 'flex';
                document.getElementById('modalAlertSymbol').focus();
            }
            
            function closeCreateAlertModal() {
                document.getElementById('createAlertModal').style.display = 'none';
                document.getElementById('modalAlertSymbol').value = '';
                document.getElementById('modalAlertPrice').value = '';
            }
            
            function showCreateAlertForAsset(symbol) {
                document.getElementById('createAlertModal').style.display = 'flex';
                document.getElementById('modalAlertSymbol').value = symbol;
                document.getElementById('modalAlertPrice').focus();
            }
            
            function createAlertFromModal() {
                const symbol = document.getElementById('modalAlertSymbol').value.trim().toUpperCase();
                const price = parseFloat(document.getElementById('modalAlertPrice').value);
                const type = document.getElementById('modalAlertType').value;
                
                if (symbol && !isNaN(price) && ws && ws.readyState === WebSocket.OPEN) {
                    // In a real app, this would send to the backend
                    ws.send(JSON.stringify({
                        action: 'create_alert',
                        symbol: symbol,
                        target_price: price,
                        alert_type: type
                    }));
                    
                    closeCreateAlertModal();
                    showNotification(`Alert created for ${symbol} at $${price}`);
                } else {
                    showNotification('Please fill in all fields correctly', 'error');
                }
            }
            
            function showCreatePortfolioModal() {
                showNotification('Portfolio creation feature coming soon!');
            }
            
            function showNotification(message, type = 'success') {
                const notification = document.getElementById('notification');
                notification.textContent = message;
                notification.className = 'notification ' + (type === 'error' ? 'error' : 'show');
                
                setTimeout(() => {
                    notification.classList.remove('show');
                    notification.classList.remove('error');
                }, 3000);
            }
            
            // Tab switching
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    activeTab = tab.dataset.tab;
                    updateDashboard(currentAssets);
                });
            });
            
            // Timeframe switching
            document.querySelectorAll('.time-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    updateTimeframe(e.target.dataset.interval);
                });
            });
            
            // Historical period switching
            document.querySelectorAll('.historical-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    updateHistoricalPeriod(e.target.dataset.period);
                });
            });
            
            // Compare period switching
            document.querySelectorAll('.compare-period-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    updateComparePeriod(e.target.dataset.period);
                });
            });
            
            // Allow Enter key to search
            document.getElementById('symbolInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchAssets();
                }
            });
            
            // Allow Enter key to add asset in modal
            document.getElementById('newAssetSymbol').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    addAssetToWatchlist();
                }
            });
            
            // Allow Enter key to login
            document.getElementById('loginPassword').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    login();
                }
            });
            
            // Close modals when clicking outside
            document.getElementById('addAssetModal').addEventListener('click', function(e) {
                if (e.target.id === 'addAssetModal') {
                    closeAddAssetModal();
                }
            });
            
            document.getElementById('createAlertModal').addEventListener('click', function(e) {
                if (e.target.id === 'createAlertModal') {
                    closeCreateAlertModal();
                }
            });
            
            document.getElementById('exportModal').addEventListener('click', function(e) {
                if (e.target.id === 'exportModal') {
                    closeExportModal();
                }
            });
            
            document.getElementById('compareModal').addEventListener('click', function(e) {
                if (e.target.id === 'compareModal') {
                    closeCompareModal();
                }
            });
            
            document.getElementById('loginModal').addEventListener('click', function(e) {
                if (e.target.id === 'loginModal') {
                    closeLoginModal();
                }
            });
            
            // Initialize
            checkAuthStatus();
            connect();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)