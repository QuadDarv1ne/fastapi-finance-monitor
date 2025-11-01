"""Connection manager for handling WebSocket connections"""

from typing import Dict, Set, Optional, Any, List
import logging
from datetime import datetime, timedelta
from fastapi import WebSocket
import asyncio
import json
import uuid

from app.services.metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)

# Connection limits
MAX_CLIENTS = 5000  # Increased from 1000 for better scalability
HEARTBEAT_INTERVAL = 10  # seconds  # Reduced from 30 for more responsive health checks
CLIENT_TIMEOUT = 30  # seconds  # Reduced from 120 for quicker cleanup

class ConnectionManager:
    """Управление WebSocket соединениями"""
    
    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize connection manager
        
        Args:
            metrics_collector: Metrics collector instance (optional)
        """
        # Active connections: websocket -> client info
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        if metrics_collector is None:
            from app.services.metrics_collector import MetricsCollector
            metrics_collector = MetricsCollector.get_instance()
        self.metrics = metrics_collector
        # Shutdown event for graceful shutdown
        self.shutdown_event = asyncio.Event()
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> Optional[str]:
        """
        Handle new WebSocket connection
        
        Args:
            websocket: WebSocket connection
            client_id: Optional client ID (if None, generate a new one)
            
        Returns:
            Client ID if connection successful, None otherwise
        """
        # Check connection limits
        if len(self.active_connections) >= MAX_CLIENTS:
            logger.warning("Maximum client connections reached")
            try:
                await websocket.close(code=1013, reason="Server busy")
            except Exception as e:
                logger.error(f"Error closing WebSocket for max clients: {e}")
            return None
        
        # Use provided client ID or generate a new one
        if client_id is None:
            client_id = str(uuid.uuid4())
        
        try:
            await websocket.accept()
            
            # Store client info
            self.active_connections[websocket] = {
                "id": client_id,
                "connected_at": datetime.now(),
                "last_heartbeat": datetime.now(),
                "timeframe": "5m"
            }
            
            self.metrics.increment_connections()
            logger.info(f"WebSocket client {client_id} connected. Total clients: {len(self.active_connections)}")
            
            return client_id
            
        except Exception as e:
            logger.error(f"WebSocket connection error for client {client_id}: {e}")
            return None
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Handle WebSocket disconnection
        
        Args:
            websocket: WebSocket connection to disconnect
        """
        client_id = "unknown"
        if websocket in self.active_connections:
            client_id = self.active_connections[websocket]["id"]
            
        # Remove from active connections
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        
        # Close the WebSocket
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")
        
        self.metrics.decrement_connections()
        logger.info(f"WebSocket client {client_id} disconnected. Total clients: {len(self.active_connections)}")
    
    async def send_message(self, websocket: WebSocket, message: Dict) -> bool:
        """
        Send message to a specific client
        
        Args:
            websocket: WebSocket connection
            message: Message to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            message_str = json.dumps(message)
            await asyncio.wait_for(websocket.send_text(message_str), timeout=5.0)
            self.metrics.record_message_sent()
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Client timeout during message send")
            return False
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            return False
    
    async def broadcast(self, message: Dict, websockets: Optional[List[WebSocket]] = None) -> None:
        """
        Broadcast message to multiple clients with performance optimizations
        
        Args:
            message: Message to broadcast
            websockets: List of websockets to send to (None for all active connections)
        """
        # If no specific websockets provided, send to all active connections
        if websockets is None:
            websockets = list(self.active_connections.keys())
        
        # Pre-serialize message to avoid repeated serialization
        message_str = json.dumps(message)
        
        # Process all clients concurrently for better performance with batching
        batch_size = 100
        for i in range(0, len(websockets), batch_size):
            batch = websockets[i:i + batch_size]
            broadcast_tasks = []
            for websocket in batch:
                task = self._send_to_client(websocket, message_str)
                broadcast_tasks.append(task)
            
            # Gather all results concurrently
            results = await asyncio.gather(*broadcast_tasks, return_exceptions=True)
            
            # Handle disconnected clients
            disconnected_clients = []
            for j, result in enumerate(results):
                if isinstance(result, Exception) or result is False:
                    disconnected_clients.append(batch[j])
            
            # Remove disconnected clients
            for websocket in disconnected_clients:
                await self.disconnect(websocket)
            
            # Small delay between batches to prevent overwhelming the system
            if i + batch_size < len(websockets):
                await asyncio.sleep(0.01)
    
    async def _send_to_client(self, websocket: WebSocket, message_str: str) -> bool:
        """
        Send message to a specific client
        
        Args:
            websocket: WebSocket connection
            message_str: Serialized message string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await asyncio.wait_for(websocket.send_text(message_str), timeout=1.0)  # Reduced timeout
            self.metrics.record_message_sent()
            return True
        except asyncio.TimeoutError:
            logger.warning(f"Client timeout during broadcast")
            return False
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            return False
    
    def get_client_id(self, websocket: WebSocket) -> Optional[str]:
        """
        Get client ID for a WebSocket connection
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Client ID or None if not found
        """
        if websocket in self.active_connections:
            return self.active_connections[websocket]["id"]
        return None
    
    def update_heartbeat(self, websocket: WebSocket) -> None:
        """
        Update last heartbeat time for a client
        
        Args:
            websocket: WebSocket connection
        """
        if websocket in self.active_connections:
            self.active_connections[websocket]["last_heartbeat"] = datetime.now()
    
    async def health_check_worker(self) -> None:
        """Периодическая проверка здоровья соединений"""
        while not self.shutdown_event.is_set():
            try:
                now = datetime.now()
                timeout_clients = []
                
                for websocket, info in list(self.active_connections.items()):
                    time_since_heartbeat = now - info["last_heartbeat"]
                    
                    if time_since_heartbeat > timedelta(seconds=CLIENT_TIMEOUT):
                        logger.warning(f"Client {info['id']} timeout")
                        timeout_clients.append(websocket)
                
                # Disconnect timeout clients
                for websocket in timeout_clients:
                    await self.disconnect(websocket)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in health check: {e}")
                await asyncio.sleep(60)  # Continue checking even if error occurs
    
    async def shutdown(self) -> None:
        """Graceful shutdown всех соединений"""
        logger.info("Инициирование shutdown...")
        self.shutdown_event.set()
        
        # Notify all clients of shutdown
        shutdown_message = {
            "type": "system",
            "message": "Server shutting down",
            "timestamp": datetime.now().isoformat()
        }
        
        disconnected = list(self.active_connections.keys())
        for websocket in disconnected:
            try:
                await self.send_message(websocket, shutdown_message)
                await asyncio.sleep(0.1)  # Small delay between messages
            except:
                pass
            finally:
                await self.disconnect(websocket)
        
        logger.info(f"Shutdown complete. {len(disconnected)} clients disconnected")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "active_connections": len(self.active_connections),
            "max_connections": MAX_CLIENTS
        }