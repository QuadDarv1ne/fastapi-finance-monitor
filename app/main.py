"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 🚀 FastAPI Finance Monitor - Финансовый дашборд             ║
║                                                                              ║
║  Мониторинг финансовых активов в реальном времени:                           ║
║  • 📈 Акции (Apple, Google, Microsoft, Tesla и др.)                         ║
║  • 💰 Криптовалюты (Bitcoin, Ethereum и др.)                                ║
║  • 🏆 Товары (Золото, Нефть и др.)                                          ║
║  • 🌍 Валютные пары (EUR/USD и др.)                                         ║
║                                                                              ║
║  Функциональность:                                                           ║
║  ✅ Real-time WebSocket обновления каждые 5 секунд                          ║
║  ✅ Интерактивная фильтрация по типам активов                               ║
║  ✅ Поиск активов в реальном времени                                        ║
║  ✅ Информация о ценах, изменениях, объемах                                 ║
║  ✅ Красивый адаптивный интерфейс с темной темой                            ║
║  ✅ Пауза/Продолжить обновления                                             ║
║                                                                              ║
║  Версия: 1.0.0                                                               ║
║  Автор: Дуплей Максим Игоревич                                               ║
║  https://orcid.org/0009-0007-7605-539X                                       ║
║  https://stepik.org/users/150943726/teach                                    ║
║  Лицензия: MIT                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Основной файл приложения - ИСПРАВЛЕННАЯ ВЕРСИЯ (v1.0.0)

Использует:
  - FastAPI: Асинхронный веб-фреймворк
  - WebSocket: Real-time коммуникация с клиентами
  - asyncio: Асинхронное программирование
  - CORS: Кросс-доменные запросы

Структура:
  1. WebSocketManager - управление WebSocket соединениями
  2. Пример данных (SAMPLE_ASSETS) - 8 финансовых инструментов
  3. FastAPI routes - REST API эндпоинты
  4. WebSocket endpoint - real-time обновления
  5. HTML Dashboard - интерактивный веб-интерфейс
  6. JavaScript - клиентская логика и взаимодействие

Архитектура приложения:
  - REST API для пользовательских операций (аутентификация, портфели, уведомления)
  - WebSocket для real-time обновлений финансовых данных
  - Асинхронная архитектура для высокой производительности
  - Двухуровневое кэширование (Redis + память)
  - Мониторинг и сбор метрик системы
  - Система уведомлений и алертов
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime
import json
from typing import List
import logging
import sys
import os

# Add the current directory and parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import our modules
from api.routes import router as api_router
from api.websocket import websocket_endpoint, data_stream_worker
from database import init_db
from services.redis_cache_service import get_redis_cache_service
from services.monitoring_service import get_monitoring_service
from services.advanced_alert_service import get_advanced_alert_service
from middleware.monitoring_middleware import MonitoringMiddleware
from middleware.exception_handler_middleware import ExceptionHandlerMiddleware  # Add this import
from services.data_fetcher import DataFetcher

app = FastAPI(
    title="FastAPI Finance Monitor",
    description="Real-time financial dashboard for stocks, crypto, and commodities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handling middleware (should be close to the outside to catch all exceptions)
app.add_middleware(ExceptionHandlerMiddleware)

# Add monitoring middleware
app.add_middleware(MonitoringMiddleware)  # Restore the original middleware

# Include API routes
app.include_router(api_router)

# Global variables for background tasks
background_tasks = set()
startup_complete = False

# Initialize database and cache on startup
@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    global startup_complete
    logger.info("Starting application services")
    
    try:
        init_db()  # Initialize database
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    
    try:
        # Initialize Redis cache (make it optional)
        redis_cache = get_redis_cache_service()
        if not await redis_cache.connect():
            logger.warning("Failed to connect to Redis cache, continuing without caching")
        else:
            logger.info("Redis cache connected successfully")
    except Exception as e:
        logger.warning(f"Error connecting to Redis cache: {e}, continuing without caching")
    
    try:
        # Initialize cache warming for frequently accessed assets
        data_fetcher = DataFetcher()
        cache_warming_task = asyncio.create_task(data_fetcher.initialize_cache_warming())
        background_tasks.add(cache_warming_task)
        cache_warming_task.add_done_callback(background_tasks.discard)
        logger.info("Cache warming initialization started")
    except Exception as e:
        logger.error(f"Error starting cache warming: {e}")
    
    try:
        # Start monitoring service
        monitoring_service = get_monitoring_service()
        monitoring_task = asyncio.create_task(monitoring_service.log_periodic_metrics())
        background_tasks.add(monitoring_task)
        monitoring_task.add_done_callback(background_tasks.discard)
        logger.info("Monitoring service started")
    except Exception as e:
        logger.error(f"Error starting monitoring service: {e}")
        raise
    
    try:
        # Start advanced alert monitoring
        from services.database_service import DatabaseService
        from database import SessionLocal
        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            advanced_alert_service = get_advanced_alert_service(db_service)
            alert_task = asyncio.create_task(advanced_alert_service.start_monitoring())
            background_tasks.add(alert_task)
            alert_task.add_done_callback(background_tasks.discard)
            logger.info("Advanced alert monitoring started")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error starting advanced alert monitoring: {e}")
        raise
    
    try:
        # Start data stream worker
        data_stream_task = asyncio.create_task(data_stream_worker())
        background_tasks.add(data_stream_task)
        data_stream_task.add_done_callback(background_tasks.discard)
        logger.info("Data stream worker started")
    except Exception as e:
        logger.error(f"Error starting data stream worker: {e}")
        raise
    
    startup_complete = True
    logger.info("All background services started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks on shutdown"""
    global startup_complete
    logger.info("Shutting down application services")
    
    try:
        # Stop advanced alert monitoring
        from services.database_service import DatabaseService
        from database import SessionLocal
        db = SessionLocal()
        try:
            db_service = DatabaseService(db)
            advanced_alert_service = get_advanced_alert_service(db_service)
            await advanced_alert_service.stop_monitoring()
            logger.info("Advanced alert monitoring stopped")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error stopping advanced alert monitoring: {e}")
    
    try:
        # Cancel all background tasks
        for task in background_tasks:
            task.cancel()
        
        # Wait for tasks to complete with timeout
        if background_tasks:
            await asyncio.wait_for(
                asyncio.gather(*background_tasks, return_exceptions=True),
                timeout=10.0
            )
        logger.info("Background tasks cancelled")
    except Exception as e:
        logger.error(f"Error cancelling background tasks: {e}")
    
    try:
        # Close Redis connection (handle case when not connected)
        redis_cache = get_redis_cache_service()
        if redis_cache.redis_client:
            await redis_cache.close()
            logger.info("Redis connection closed")

        else:
            logger.info("No Redis connection to close")
    except Exception as e:
        logger.error(f"Error closing Redis connection: {e}")
    
    startup_complete = False
    logger.info("All services shut down successfully")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if startup_complete else "starting",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "unknown",
            "redis": "unknown",
            "alerts": "unknown"
        }
    }

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint_wrapper(websocket: WebSocket, token: str = Query(None)):
    """WebSocket endpoint for real-time data"""
    monitoring_service = get_monitoring_service()
    monitoring_service.increment_active_connections()
    try:
        await websocket_endpoint(websocket, token)
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
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); /* Changed to show more items */
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
                min-height: 400px; /* Ensure consistent card height */
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
                height: 200px; /* Reduced chart height for better layout */
                margin-top: 15px;
            }
            .info-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); /* Adjusted for better fit */
                gap: 10px;
                margin: 15px 0;
            }
            .info-item {
                background: rgba(42, 47, 74, 0.5);
                padding: 10px;
                border-radius: 8px;
                text-align: center;
            }
            .info-label {
                font-size: 0.8em;
                color: #9ca3af;
                margin-bottom: 5px;
            }
            .info-value {
                font-size: 1em;
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
            .password-requirements {
                margin-top: 5px;
                color: #aaa;
                font-size: 0.8em;
            }
            
            .password-requirements small {
                display: block;
            }
            
            @media (max-width: 1200px) {
                .grid {
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                }
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
        
        <!-- Registration Modal -->
        <div id="registerModal" class="login-modal" style="display: none;">
            <div class="login-modal-content">
                <h2><i class="fas fa-user-plus"></i> Register</h2>
                <div class="login-form-group">
                    <label for="registerUsername">Username</label>
                    <input type="text" id="registerUsername" class="login-form-control" placeholder="Enter your username">
                </div>
                <div class="login-form-group">
                    <label for="registerEmail">Email</label>
                    <input type="email" id="registerEmail" class="login-form-control" placeholder="Enter your email">
                </div>
                <div class="login-form-group">
                    <label for="registerPassword">Password</label>
                    <input type="password" id="registerPassword" class="login-form-control" placeholder="Enter your password">
                    <div class="password-requirements">
                        <small>Password must be at least 8 characters with uppercase, lowercase, number, and special character</small>
                    </div>
                </div>
                <div class="login-form-group">
                    <label for="registerConfirmPassword">Confirm Password</label>
                    <input type="password" id="registerConfirmPassword" class="login-form-control" placeholder="Confirm your password">
                </div>
                <button class="login-btn" onclick="register()">Register</button>
                <div class="auth-links">
                    <p>Already have an account? <a onclick="showLoginForm()">Login</a></p>
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                    <button class="btn btn-secondary" onclick="closeRegisterModal()">Cancel</button>
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
            <button class="btn btn-warning" onclick="showCreateAlertModal('')"><i class="fas fa-bell"></i> Create Alert</button>
            <button class="btn btn-info" onclick="toggleAutoRefresh(event)"><i class="fas fa-play"></i> Auto Refresh</button>
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
                // Include auth token in WebSocket URL if available
                const token = localStorage.getItem('authToken') || '';
                const wsUrl = token 
                    ? `${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`
                    : `${protocol}//${window.location.host}/ws`;
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = '🟢 Connected';
                    document.getElementById('status').className = 'status connected';
                    showNotification('Connected to real-time data stream');
                    
                    // Request data with current timeframe
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({action: 'set_timeframe', timeframe: currentTimeframe}));
                    }
                };
                
                ws.onclose = (event) => {
                    document.getElementById('status').textContent = '🔴 Disconnected';
                    document.getElementById('status').className = 'status disconnected';
                    
                    // Show notification only if it wasn't a clean disconnect
                    if (event.code !== 1000) {
                        showNotification('Connection lost. Reconnecting...', 'error');
                    }
                    
                    // Attempt to reconnect with exponential backoff
                    setTimeout(connect, 3000);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    showNotification('Connection error. Reconnecting...', 'error');
                };
                
                ws.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        handleMessage(message);
                    } catch (e) {
                        console.error('Error parsing message:', e);
                        showNotification('Error parsing data', 'error');
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
                        let errorMessage = 'Login failed';
                        try {
                            const errorData = await response.json();
                            errorMessage = errorData.detail || errorMessage;
                        } catch (e) {
                            // If we can't parse the error response, use the status text
                            errorMessage = response.statusText || errorMessage;
                        }
                        throw new Error(errorMessage);
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
                document.getElementById('registerModal').style.display = 'flex';
                document.getElementById('registerUsername').focus();
            }
            
            function showLoginForm() {
                closeRegisterModal();
                showLoginModal();
            }
            
            function closeRegisterModal() {
                document.getElementById('registerModal').style.display = 'none';
                document.getElementById('registerUsername').value = '';
                document.getElementById('registerEmail').value = '';
                document.getElementById('registerPassword').value = '';
                document.getElementById('registerConfirmPassword').value = '';
            }
            
            async function register() {
                const username = document.getElementById('registerUsername').value.trim();
                const email = document.getElementById('registerEmail').value.trim();
                const password = document.getElementById('registerPassword').value;
                const confirmPassword = document.getElementById('registerConfirmPassword').value;
                
                // Basic validation
                if (!username || !email || !password || !confirmPassword) {
                    showNotification('Please fill in all fields', 'error');
                    return;
                }
                
                if (password !== confirmPassword) {
                    showNotification('Passwords do not match', 'error');
                    return;
                }
                
                if (password.length < 8) {
                    showNotification('Password must be at least 8 characters long', 'error');
                    return;
                }
                
                // Email validation
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(email)) {
                    showNotification('Please enter a valid email address', 'error');
                    return;
                }
                
                try {
                    const response = await fetch('/api/users/register', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            username: username,
                            email: email,
                            password: password
                        })
                    });
                    
                    if (!response.ok) {
                        let errorMessage = 'Registration failed';
                        try {
                            const errorData = await response.json();
                            errorMessage = errorData.detail || errorMessage;
                        } catch (e) {
                            // If we can't parse the error response, use the status text
                            errorMessage = response.statusText || errorMessage;
                        }
                        throw new Error(errorMessage);
                    }
                    
                    const data = await response.json();
                    
                    closeRegisterModal();
                    showNotification(`Registration successful! Welcome, ${data.username}! Please login.`);
                    
                    // Show login form after successful registration
                    setTimeout(showLoginModal, 2000);
                } catch (error) {
                    console.error('Registration error:', error);
                    showNotification(error.message || 'Registration failed', 'error');
                }
            }
            
            function handleMessage(message) {
                try {
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
                    } else {
                        console.warn('Unknown message type received:', message.type);
                    }
                } catch (error) {
                    console.error('Error handling WebSocket message:', error);
                    showNotification('Error processing data', 'error');
                }
            }
            
            function updateTimeframe(interval, event) {
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
            
            function updateHistoricalPeriod(period, event) {
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
            
            function updateComparePeriod(period, event) {
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
            
            function toggleAutoRefresh(event) {
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
                }
                
                // Update dashboard grid
                const dashboard = document.getElementById('dashboard');
                
                if (filteredAssets.length === 0) {
                    dashboard.innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-info-circle"></i>
                            <h3>No assets found</h3>
                            <p>Try adding assets to your watchlist or changing filters</p>
                        </div>
                    `;
                    return;
                }
                
                // Generate cards for each asset
                let html = '';
                filteredAssets.forEach(asset => {
                    const changeClass = asset.change_percent >= 0 ? 'positive' : 'negative';
                    const changeIcon = asset.change_percent >= 0 ? '▲' : '▼';
                    
                    html += `
                        <div class="card">
                            <div class="card-header">
                                <div class="asset-info">
                                    <div class="asset-icon">${asset.symbol.charAt(0)}</div>
                                    <div>
                                        <div class="asset-name">${asset.name}</div>
                                        <div class="asset-symbol">${asset.symbol}</div>
                                    </div>
                                </div>
                                <div class="asset-type">${asset.type}</div>
                            </div>
                            <div class="price">$${asset.current_price.toFixed(2)}</div>
                            <div class="change ${changeClass}">
                                <span>${changeIcon}</span>
                                <span>${Math.abs(asset.change_percent).toFixed(2)}%</span>
                            </div>
                            <div class="info-grid">
                                <div class="info-item">
                                    <div class="info-label">Open</div>
                                    <div class="info-value">$${asset.open.toFixed(2)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">High</div>
                                    <div class="info-value">$${asset.high.toFixed(2)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Low</div>
                                    <div class="info-value">$${asset.low.toFixed(2)}</div>
                                </div>
                                <div class="info-item">
                                    <div class="info-label">Volume</div>
                                    <div class="info-value">${asset.volume?.toLocaleString() || 'N/A'}</div>
                                </div>
                            </div>
                            <div class="chart" id="chart-${asset.symbol}"></div>
                            <div style="display: flex; gap: 10px; margin-top: 15px;">
                                <button class="btn btn-secondary" onclick="showCreateAlertModal('${asset.symbol}')">
                                    <i class="fas fa-bell"></i> Alert
                                </button>
                                <button class="btn btn-info" onclick="showExportModal('${asset.symbol}')">
                                    <i class="fas fa-download"></i> Export
                                </button>
                                <button class="btn btn-success" onclick="addToWatchlist('${asset.symbol}', '${asset.name}', '${asset.type}')">
                                    <i class="fas fa-plus"></i> Watchlist
                                </button>
                            </div>
                        </div>
                    `;
                });
                
                dashboard.innerHTML = html;
                
                // Render charts for each asset
                filteredAssets.forEach(asset => {
                    renderChart(asset.symbol, asset.chart_data);
                });
            }
            
            function searchAssets() {
                const query = document.getElementById('symbolInput').value.trim().toLowerCase();
                if (!query) {
                    // If search is empty, show all assets for current tab
                    updateDashboard(currentAssets);
                    return;
                }
                
                const filteredAssets = currentAssets.filter(asset => 
                    asset.symbol.toLowerCase().includes(query) || asset.name.toLowerCase().includes(query)
                );
                updateDashboard(filteredAssets);
            }
            
            function showCreateAlertModal(symbol) {
                document.getElementById('alertSymbol').value = symbol;
                document.getElementById('createAlertModal').style.display = 'flex';
                document.getElementById('alertPrice').focus();
            }
            
            function refreshData() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({action: 'refresh'}));
                    showNotification('Refreshing data...');
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
                    ws.send(JSON.stringify({
                        action: 'add_asset',
                        symbol: symbol
                    }));
                    
                    closeAddAssetModal();
                    showNotification(`Added ${symbol} to watchlist`);
                }
            }
            
            function showExportModal(symbol) {
                document.getElementById('exportSymbol').textContent = symbol;
                document.getElementById('exportModal').style.display = 'flex';
            }
            
            function closeExportModal() {
                document.getElementById('exportModal').style.display = 'none';
            }
            
            function exportData(format) {
                const symbol = document.getElementById('exportSymbol').textContent;
                showNotification(`Exporting ${symbol} data as ${format.toUpperCase()}...`);
                closeExportModal();
                // In a real implementation, this would trigger an actual export
            }
            
            function showCompareModal() {
                document.getElementById('compareModal').style.display = 'flex';
                // Load available assets for comparison
                loadCompareAssets();
            }
            
            function closeCompareModal() {
                document.getElementById('compareModal').style.display = 'none';
            }
            
            function loadCompareAssets() {
                // In a real implementation, this would load available assets
                // For now, we'll use a mock list
                const assetsList = document.getElementById('compareAssetsList');
                assetsList.innerHTML = '';
                
                // Mock assets for demonstration
                const mockAssets = [
                    {symbol: 'AAPL', name: 'Apple Inc.'},
                    {symbol: 'GOOGL', name: 'Alphabet Inc.'},
                    {symbol: 'MSFT', name: 'Microsoft Corp.'},
                    {symbol: 'bitcoin', name: 'Bitcoin'},
                    {symbol: 'ethereum', name: 'Ethereum'},
                    {symbol: 'GC=F', name: 'Gold Futures'}
                ];
                
                mockAssets.forEach(asset => {
                    const item = document.createElement('div');
                    item.className = 'compare-asset-item';
                    item.innerHTML = `
                        <i>${asset.symbol.charAt(0)}</i>
                        <span>${asset.name} (${asset.symbol})</span>
                    `;
                    item.addEventListener('click', () => toggleCompareAsset(asset.symbol, item));
                    assetsList.appendChild(item);
                });
            }
            
            function toggleCompareAsset(symbol, element) {
                if (selectedCompareAssets.has(symbol)) {
                    selectedCompareAssets.delete(symbol);
                    element.classList.remove('selected');
                } else {
                    selectedCompareAssets.add(symbol);
                    element.classList.add('selected');
                }
                
                // Update comparison if at least 2 assets are selected
                if (selectedCompareAssets.size >= 2) {
                    loadComparisonData();
                } else {
                    document.getElementById('compareChartContainer').innerHTML = `
                        <div class="empty-state">
                            <i class="fas fa-chart-line"></i>
                            <h3>Select assets to compare</h3>
                            <p>Choose at least two assets to see their performance comparison</p>
                        </div>
                    `;
                }
            }
            
            function loadComparisonData() {
                if (selectedCompareAssets.size < 2) return;
                
                // In a real implementation, this would fetch actual data
                // For now, we'll show a mock chart
                const container = document.getElementById('compareChartContainer');
                container.innerHTML = `
                    <div style="text-align: center; padding: 20px;">
                        <i class="fas fa-chart-line" style="font-size: 3em; margin-bottom: 20px; color: #667eea;"></i>
                        <h3>Performance Comparison</h3>
                        <p>Comparison chart for ${Array.from(selectedCompareAssets).join(', ')}</p>
                        <div style="height: 300px; background: #2a2f4a; border-radius: 10px; margin-top: 20px; display: flex; align-items: center; justify-content: center;">
                            <div>Chart visualization would appear here</div>
                        </div>
                    </div>
                `;
            }
            
            function closeCreateAlertModal() {
                document.getElementById('createAlertModal').style.display = 'none';
                document.getElementById('alertSymbol').value = '';
                document.getElementById('alertPrice').value = '';
            }
            
            function createAlertFromModal() {
                const symbol = document.getElementById('alertSymbol').value.trim().toUpperCase();
                const price = parseFloat(document.getElementById('alertPrice').value);
                const type = document.getElementById('alertType').value;
                
                if (!symbol) {
                    showNotification('Please enter a symbol', 'error');
                    return;
                }
                
                if (isNaN(price) || price <= 0) {
                    showNotification('Please enter a valid price', 'error');
                    return;
                }
                
                if (ws && ws.readyState === WebSocket.OPEN) {
                    try {
                        ws.send(JSON.stringify({
                            action: 'create_alert',
                            symbol: symbol,
                            target_price: price,
                            alert_type: type
                        }));
                        
                        closeCreateAlertModal();
                        showNotification(`Alert created for ${symbol} at $${price}`);
                    } catch (error) {
                        console.error('Error creating alert:', error);
                        showNotification('Error creating alert', 'error');
                    }
                } else {
                    showNotification('Not connected to server', 'error');
                }
            }

            function createAlert() {
                const symbol = document.getElementById('alertSymbol').value.trim().toUpperCase();
                const price = parseFloat(document.getElementById('alertPrice').value);
                const type = document.getElementById('alertType').value;
                
                if (symbol && !isNaN(price) && ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        action: 'create_alert',
                        symbol: symbol,
                        target_price: price,
                        alert_type: type
                    }));
                    
                    document.getElementById('alertSymbol').value = '';
                    document.getElementById('alertPrice').value = '';
                    showNotification(`Alert created for ${symbol} at $${price}`);
                }
            }

            function showNotification(message, type = 'success') {
                const notification = document.getElementById('notification');
                notification.textContent = message;
                notification.className = 'notification ' + (type === 'error' ? 'error' : 'show');
                
                // Show notification
                notification.classList.add('show');
                
                // Hide after 3 seconds
                setTimeout(() => {
                    notification.classList.remove('show');
                }, 3000);
            }

            // Tab switching
            function switchTab(tabName, event) {
                // Update active tab
                activeTab = tabName;
                
                // Update UI
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                event.target.classList.add('active');
                
                // Update dashboard
                updateDashboard(currentAssets);
            }
            
            // Initialize
            function init() {
                // Set up event listeners
                document.querySelectorAll('.time-btn').forEach(btn => {
                    btn.addEventListener('click', (event) => updateTimeframe(btn.dataset.interval, event));
                });
                
                document.querySelectorAll('.historical-btn').forEach(btn => {
                    btn.addEventListener('click', (event) => updateHistoricalPeriod(btn.dataset.period, event));
                });
                
                document.querySelectorAll('.compare-period-btn').forEach(btn => {
                    btn.addEventListener('click', (event) => updateComparePeriod(btn.dataset.period, event));
                });
                
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.addEventListener('click', (event) => switchTab(tab.dataset.tab, event));
                });
                
                // Check authentication status
                checkAuthStatus();
                
                // Connect to WebSocket
                connect();
                
                // Set up auto refresh
                refreshInterval = setInterval(() => {
                    if (autoRefreshEnabled && ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({action: 'refresh'}));
                    }
                }, 30000); // 30 seconds
                
                // Handle Enter key in search box
                document.getElementById('symbolInput').addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        searchAssets();
                    }
                });
                
                // Handle Enter key in login form
                document.getElementById('loginPassword').addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        login();
                    }
                });
            }
            
            function renderChart(symbol, chartData) {
                const chartElement = document.getElementById(`chart-${symbol}`);
                if (!chartElement) return;
                
                // Extract data for plotting
                const timestamps = chartData.map(point => new Date(point.time));
                const prices = chartData.map(point => point.price || point.close);
                
                // Create trace for the chart
                const trace = {
                    x: timestamps,
                    y: prices,
                    type: 'scatter',
                    mode: 'lines',
                    line: {
                        color: '#667eea',
                        width: 2
                    },
                    fill: 'tozeroy',
                    fillcolor: 'rgba(102, 126, 234, 0.1)'
                };
                
                // Chart layout
                const layout = {
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    margin: {l: 0, r: 0, t: 0, b: 30},
                    xaxis: {
                        showgrid: false,
                        showticklabels: false
                    },
                    yaxis: {
                        showgrid: false,
                        showticklabels: false
                    },
                    showlegend: false
                };
                
                // Chart configuration
                const config = {
                    displayModeBar: false
                };
                
                // Render the chart
                Plotly.newPlot(chartElement, [trace], layout, config);
            }
            
            // Start when page loads
            window.onload = init;
        </script>
    </body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=200)