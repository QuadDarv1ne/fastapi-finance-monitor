"""Alert service for price notifications and alerts"""

from typing import List, Optional, Dict
import asyncio
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from app.models import User, WatchlistItem
from app.services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class AlertService:
    """Service for handling price alerts and notifications"""
    
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.active_alerts = {}  # Store active alerts
        self.alert_checks = {}  # Store alert check tasks
        # Email configuration
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_username = os.getenv("EMAIL_USERNAME", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.sender_email = os.getenv("SENDER_EMAIL", self.email_username)
    
    async def create_price_alert(self, user_id: int, symbol: str, target_price: float, 
                                alert_type: str, watchlist_item_id: Optional[int] = None) -> Dict:
        """Create a price alert for a specific asset"""
        try:
            alert_id = f"{user_id}_{symbol}_{datetime.now().timestamp()}"
            
            alert = {
                "id": alert_id,
                "user_id": user_id,
                "symbol": symbol.upper(),
                "target_price": target_price,
                "alert_type": alert_type,  # 'above' or 'below'
                "watchlist_item_id": watchlist_item_id,
                "created_at": datetime.now(),
                "active": True
            }
            
            self.active_alerts[alert_id] = alert
            
            # Start monitoring this alert if not already running
            if symbol.upper() not in self.alert_checks:
                self.alert_checks[symbol.upper()] = asyncio.create_task(
                    self._monitor_asset_price(symbol.upper())
                )
            
            logger.info(f"Created price alert {alert_id} for {symbol} at {target_price}")
            return {"alert_id": alert_id, "message": "Alert created successfully"}
            
        except Exception as e:
            logger.error(f"Error creating price alert: {e}")
            return {"error": str(e)}
    
    async def remove_alert(self, alert_id: str) -> bool:
        """Remove an active alert"""
        try:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id]["active"] = False
                del self.active_alerts[alert_id]
                logger.info(f"Removed alert {alert_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing alert {alert_id}: {e}")
            return False
    
    async def get_user_alerts(self, user_id: int) -> List[Dict]:
        """Get all alerts for a specific user"""
        try:
            user_alerts = [
                alert for alert in self.active_alerts.values()
                if alert["user_id"] == user_id and alert["active"]
            ]
            return user_alerts
        except Exception as e:
            logger.error(f"Error getting user alerts: {e}")
            return []
    
    async def _monitor_asset_price(self, symbol: str):
        """Monitor asset price and trigger alerts"""
        try:
            from app.services.data_fetcher import DataFetcher
            data_fetcher = DataFetcher()
            
            while True:
                try:
                    # Check if there are any active alerts for this symbol
                    symbol_alerts = [
                        alert for alert in self.active_alerts.values()
                        if alert["symbol"] == symbol and alert["active"]
                    ]
                    
                    if not symbol_alerts:
                        # No active alerts for this symbol, remove the monitoring task
                        if symbol in self.alert_checks:
                            del self.alert_checks[symbol]
                        break
                    
                    # Fetch current price
                    # For now, we'll simulate price fetching
                    # In a real implementation, you would fetch actual prices
                    current_price = await self._get_current_price(symbol, data_fetcher)
                    
                    if current_price is not None:
                        # Check all alerts for this symbol
                        for alert in symbol_alerts:
                            await self._check_alert_condition(alert, current_price)
                    
                    # Wait before next check (in a real app, this might be configurable)
                    await asyncio.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Error monitoring {symbol}: {e}")
                    await asyncio.sleep(60)  # Wait before retrying
                    
        except Exception as e:
            logger.error(f"Error in monitoring task for {symbol}: {e}")
    
    async def _get_current_price(self, symbol: str, data_fetcher) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # Determine asset type based on symbol
            if symbol.lower() in ["bitcoin", "ethereum", "solana", "cardano", "polkadot"]:
                data = await data_fetcher.get_crypto_data(symbol.lower())
            else:
                data = await data_fetcher.get_stock_data(symbol)
            
            if data and "current_price" in data:
                return float(data["current_price"])
            
            return None
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    async def _check_alert_condition(self, alert: Dict, current_price: float):
        """Check if an alert condition is met"""
        try:
            target_price = alert["target_price"]
            alert_type = alert["alert_type"]
            alert_id = alert["id"]
            
            condition_met = False
            if alert_type == "above" and current_price >= target_price:
                condition_met = True
            elif alert_type == "below" and current_price <= target_price:
                condition_met = True
            
            if condition_met:
                # Trigger alert
                await self._trigger_alert(alert, current_price)
                
                # Remove the alert since it's been triggered
                await self.remove_alert(alert_id)
                
        except Exception as e:
            logger.error(f"Error checking alert condition: {e}")
    
    async def _trigger_alert(self, alert: Dict, current_price: float):
        """Trigger an alert notification"""
        try:
            user_id = alert["user_id"]
            symbol = alert["symbol"]
            target_price = alert["target_price"]
            alert_type = alert["alert_type"]
            
            # Get user information
            user = self.db_service.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found for alert")
                return
            
            message = f"Price Alert: {symbol} is now {alert_type} ${target_price} at ${current_price}"
            
            # Send email notification if user has email and email is configured
            user_email = getattr(user, 'email', None)
            if user_email and self.email_username and self.email_password:
                await self.send_email_notification(user, f"Price Alert for {symbol}", message)
            
            logger.info(f"ALERT TRIGGERED: {message}")
            
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
    
    async def send_email_notification(self, user: User, subject: str, message: str):
        """Send email notification to user"""
        try:
            # Check if email configuration is complete
            if not self.email_username or not self.email_password:
                logger.warning("Email configuration incomplete, skipping email notification")
                return
                
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.sender_email or self.email_username
            msg['To'] = str(getattr(user, 'email', ''))
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(message, 'plain'))
            
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable security
            server.login(self.email_username, self.email_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.sender_email or self.email_username, str(getattr(user, 'email', '')), text)
            server.quit()
            
            logger.info(f"Email notification sent to {getattr(user, 'email', '')}: {subject}")
            
        except Exception as e:
            logger.error(f"Error sending email notification to {getattr(user, 'email', '')}: {e}")
    
    async def send_websocket_notification(self, user_id: int, message: str):
        """Send WebSocket notification to user"""
        try:
            # In a real implementation, you would send to active WebSocket connections
            logger.info(f"WebSocket notification to user {user_id}: {message}")
            # Implementation would go here
            
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")


# Global alert service instance
alert_service = None


def get_alert_service(db_service: DatabaseService) -> AlertService:
    """Get or create alert service instance"""
    global alert_service
    if alert_service is None:
        alert_service = AlertService(db_service)
    return alert_service